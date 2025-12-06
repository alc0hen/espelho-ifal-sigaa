import json
from playwright.sync_api import sync_playwright, Page, expect
import os

def test_wrapped_hidden(page: Page, is_supporter: bool, screenshot_path: str):
    # Enable console logs
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))

    # Load the static HTML file
    cwd = os.getcwd()
    file_url = f"file://{cwd}/verification/test_dashboard.html"

    # Mock the API stream
    def handle_route(route):
        # Construct ndjson response
        user_info = json.dumps({
            "type": "user_info",
            "name": "Test User",
            "is_supporter": is_supporter
        })

        course_start = json.dumps({
            "type": "course_start",
            "id": 1,
            "name": "Math",
            "obs": "2025.1"
        })

        course_data = json.dumps({
            "type": "course_data",
            "id": 1,
            "data": {
                'b1Notes': [8.0], 'b2Notes': [9.0], 'b3Notes': [8.5], 'b4Notes': [9.5],
                'r1Note': None, 'r2Note': None
            }
        })

        course_freq = json.dumps({
            "type": "course_frequency",
            "id": 1,
            "data": {
                "total_faltas": 10,
                "max_faltas": 20,
                "percent": 12.5
            }
        })

        body = f"{user_info}\n{course_start}\n{course_data}\n{course_freq}\n"

        route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body=body,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    # Intercept the mocked absolute URL
    page.route("http://mock-backend/api/stream_grades", handle_route)

    page.goto(file_url)

    # Wait for data to load - check for a specific element that appears after loading
    # The 'New' tag or just wait a bit.
    page.wait_for_timeout(2000)

    # Click on the Achievements tab to show the Wrapped button
    page.click("button[onclick=\"switchTab('achievements')\"]")

    # Click on the Wrapped button
    page.click("button[onclick=\"generateWrapped()\"]")

    # Wait for modal animation
    page.wait_for_timeout(1000)

    # Check visibility of Faltas Totais
    freq_container = page.locator("#wr-freq-container")

    if is_supporter:
        expect(freq_container).to_be_visible()
        print("Supporter: Faltas Totais is visible (Correct)")
    else:
        expect(freq_container).to_be_hidden()
        print("Non-Supporter: Faltas Totais is hidden (Correct)")

    page.screenshot(path=screenshot_path)

if __name__ == "__main__":
    with sync_playwright() as p:
        # Important: Allow file access to fetch if needed, though we are mocking http
        browser = p.chromium.launch(headless=True, args=['--disable-web-security'])

        print("Testing Non-Supporter...")
        page1 = browser.new_page()
        try:
            test_wrapped_hidden(page1, is_supporter=False, screenshot_path="verification/non_supporter_wrapped.png")
        except Exception as e:
            print(f"FAILED Non-Supporter: {e}")
        finally:
            page1.close()

        print("\nTesting Supporter...")
        page2 = browser.new_page()
        try:
            test_wrapped_hidden(page2, is_supporter=True, screenshot_path="verification/supporter_wrapped.png")
        except Exception as e:
            print(f"FAILED Supporter: {e}")
        finally:
            page2.close()

        browser.close()
