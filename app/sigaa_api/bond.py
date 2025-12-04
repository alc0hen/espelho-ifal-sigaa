from urllib.parse import urljoin
from .exceptions import SigaaConnectionError
from .course import Course

class StudentBond:
    def __init__(self, session, registration, program, switch_url=None):
        self.session = session
        self.registration = registration
        self.program = program
        self.switch_url = switch_url
        self.courses = []

    async def get_courses(self):

        page = None
        if self.switch_url:
             page = await self.session.get(self.switch_url)
        else:

             page = await self.session.get('/sigaa/portais/discente/discente.jsf')

        self.courses = self._parse_courses(page)
        return self.courses

    def _parse_courses(self, page):
        courses = []

        tables = page.soup.find_all('table')

        for table in tables:

            headers = table.find_all('th')
            header_texts = [h.get_text(strip=True) for h in headers]

            is_course_table = any('Componente' in h or 'Disciplina' in h for h in header_texts)

            title_idx = -1
            for i, h in enumerate(header_texts):
                if 'Componente' in h or 'Disciplina' in h:
                    title_idx = i
                    break

            if not is_course_table:
                first_row = table.find('tr')
                if first_row:
                    row_text = first_row.get_text(strip=True)
                    if 'Componente' in row_text or 'Disciplina' in row_text:
                         is_course_table = True

            if not is_course_table:
                continue

            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                rows = table.find_all('tr') #

            for row in rows:
                if 'periodo' in row.get('class', []):
                    continue

                row_text_clean = row.get_text(strip=True)
                if 'Componente Curricular' in row_text_clean or 'Disciplina' in row_text_clean:
                    continue

                cells = row.find_all('td')
                if not cells:
                    continue

                name_cell = None

                if title_idx != -1 and title_idx < len(cells):
                    name_cell = cells[title_idx]

                if not name_cell:
                    for cell in cells:
                        if cell.find('span', class_='tituloDisciplina'): # IFAL specific?
                            name_cell = cell
                            break

                if not name_cell and len(cells) > 1:

                     if title_idx == -1:

                         text1 = cells[1].get_text(strip=True)
                         if "Campus" in text1 or "Sala" in text1:
                             name_cell = cells[0]
                         else:
                             name_cell = cells[1] # Standard fallback

                if not name_cell:
                    continue

                if name_cell.find('span', class_='tituloDisciplina'):
                    title = name_cell.find('span', class_='tituloDisciplina').get_text(strip=True)
                else:
                    title = name_cell.get_text(strip=True)

                # Find the form/button to access class
                access_link = row.find('a', onclick=True)
                if not access_link:
                    # Maybe it's in a specific cell
                    for cell in cells:
                         link = cell.find('a', onclick=True)
                         if link and ('discente' in str(link.get('title', '')).lower() or 'acessar' in link.get_text(strip=True).lower()):
                             access_link = link
                             break

                if access_link:
                    js_code = access_link['onclick']
                    try:
                        form_data = page.parse_jsfcljs(js_code)
                        course = Course(self.session, title, form_data)
                        courses.append(course)
                    except Exception:
                        pass # Failed to parse form, skip

        return courses


    def __repr__(self):
        return f"<StudentBond registration='{self.registration}' program='{self.program}'>"

class TeacherBond:
    def __repr__(self):
        return "<TeacherBond>"
