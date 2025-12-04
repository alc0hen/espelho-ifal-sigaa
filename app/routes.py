from flask import Blueprint, render_template, request, redirect, url_for, session, Response, stream_with_context
from .sigaa_api.sigaa import Sigaa, InstitutionType
import asyncio
import json

bp = Blueprint('main', __name__)

SIGAA_URL = "https://sigaa.ifal.edu.br"

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        sigaa = Sigaa(SIGAA_URL, InstitutionType.IFAL)
        try:
            account = await sigaa.login(username, password)

            client_session = await sigaa.session._get_session()
            cookies = {}
            for cookie in client_session.cookie_jar:
                cookies[cookie.key] = cookie.value

            session['sigaa_cookies'] = cookies
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            return render_template('login.html', error=str(e))
        finally:
            await sigaa.close()

    return render_template('login.html')

@bp.route('/apoio')
def support():
    return render_template('support.html')

def process_grades(raw_grades):

    data = {
        'b1Notes': [], 'b2Notes': [], 'b3Notes': [], 'b4Notes': [],
        'r1Note': None, 'r2Note': None
    }

    repos = []

    for item in raw_grades:
        name = item.get('name', '').strip()
        val = None

        if item.get('type') == 'single':
            val = item.get('value')
        elif item.get('type') == 'group':

            last_val = None
            for sub in item.get('grades', []):
                 if sub.get('value') is not None:
                     last_val = sub.get('value')

            if last_val is not None:
                val = last_val

        if val is None:
            continue

        try:
            val = float(val)
        except (ValueError, TypeError):
            continue

        if name == '1':
            data['b1Notes'] = [val]
        elif name == '2':
            data['b2Notes'] = [val]
        elif name == '3':
            data['b3Notes'] = [val]
        elif name == '4':
            data['b4Notes'] = [val]
        elif 'Reposição' in name or 'Recuperação' in name:
            repos.append(val)

    if len(repos) > 0:
        data['r1Note'] = repos[0]
    if len(repos) > 1:
        data['r2Note'] = repos[1]

    return data

@bp.route('/dashboard')
async def dashboard():
    """
    Renders the dashboard shell. The actual data will be loaded via the /api/stream_grades endpoint.
    """
    cookies = session.get('sigaa_cookies')
    if not cookies:
        return redirect(url_for('main.login'))

    return render_template('dashboard.html')

@bp.route('/api/stream_grades')
def stream_grades():
    """
    Sync route wrapper that yields from an async generator using a local event loop.
    This bypasses WSGI limitations with async generators.
    """
    cookies = session.get('sigaa_cookies')
    if not cookies:
        return Response("Unauthorized", status=401)

    async def async_generate():
        sigaa = Sigaa(SIGAA_URL, InstitutionType.IFAL, cookies=cookies)
        try:
            response = await sigaa.session.get("/sigaa/portais/discente/discente.jsf")
            if "login" in response.url.path:
                 yield json.dumps({"error": "Session expired"}) + "\n"
                 return

            from .sigaa_api.account import Account
            account = Account(sigaa.session, response)

            name = await account.get_name()
            yield json.dumps({"type": "user_info", "name": name}) + "\n"

            if account.active_bonds:
                for bond in account.active_bonds:
                    courses = await bond.get_courses()
                    if courses:
                        for i, course in enumerate(courses):
                            course_id = i + 1
                            yield json.dumps({
                                "type": "course_start",
                                "id": course_id,
                                "name": course.title,
                                "obs": bond.program
                            }) + "\n"

                            grades_data = {
                                'b1Notes': [], 'b2Notes': [], 'b3Notes': [], 'b4Notes': [],
                                'r1Note': None, 'r2Note': None
                            }
                            try:
                                raw_grades = await course.get_grades()
                                if raw_grades:
                                    grades_data = process_grades(raw_grades)
                            except Exception as e:
                                print(f"Error fetching grades for {course.title}: {e}")

                            yield json.dumps({
                                "type": "course_data",
                                "id": course_id,
                                "data": grades_data
                            }) + "\n"

                            # Fetch Frequency
                            freq_data = None
                            try:
                                freq_data = await course.get_frequency()
                            except Exception as e:
                                print(f"Error fetching frequency for {course.title}: {e}")

                            if freq_data:
                                yield json.dumps({
                                    "type": "course_frequency",
                                    "id": course_id,
                                    "data": freq_data
                                }) + "\n"

        except Exception as e:
            print(f"Stream error: {e}")
            yield json.dumps({"error": str(e)}) + "\n"
        finally:
            await sigaa.close()

    def sync_generate():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        gen = async_generate()

        try:
            while True:
                data = loop.run_until_complete(gen.__anext__())
                yield data
        except StopAsyncIteration:
            pass
        except Exception as e:
            print(f"Sync wrapper error: {e}")
            yield json.dumps({"error": "Internal Server Error"}) + "\n"
        finally:
            loop.close()

    return Response(stream_with_context(sync_generate()), mimetype='application/x-ndjson')

@bp.route('/logout')
def logout():
    session.pop('sigaa_cookies', None)
    return redirect(url_for('main.login'))