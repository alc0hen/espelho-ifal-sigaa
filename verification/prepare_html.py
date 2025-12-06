import re

def prepare_html():
    with open('app/templates/dashboard.html', 'r') as f:
        content = f.read()

    # Replace jinja tags
    content = re.sub(r'\{\{ url_for\(.*\) \}\}', '#', content)

    # Replace fetch URL to be absolute so we can intercept it easily from file:// origin?
    # Actually, browsers might block fetch to http from file.
    # It is better to just replace it with a dummy URL we can intercept, but verify if file protocol allows it.
    # Playwright interception usually works.
    # But to be safe, let's use a specific absolute URL.
    content = content.replace("fetch('/api/stream_grades')", "fetch('http://mock-backend/api/stream_grades')")

    with open('verification/test_dashboard.html', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    prepare_html()
