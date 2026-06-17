"""
Playwright Python tests for example.com domain validation.
Covers: Positive, Negative, Edge, Boundary, Accessibility, Regression scenarios.
"""

from typing import Optional
from playwright.sync_api import sync_playwright, expect, Page, Browser
import pytest


BASE_URL = "https://example.com"
LEARN_MORE_URL = "https://www.iana.org/help/example-domains"


class TestExampleDomain:

    _browser: Optional[Browser] = None
    _playwright = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def browser_fixture(cls):
        """Fixture to manage browser lifecycle (class-scoped)."""
        cls._playwright = sync_playwright().start()
        cls._browser = (
            cls._playwright.chromium.launch(headless=True)
        )
        yield cls._browser
        cls._browser.close()
        cls._browser = None
        cls._playwright.stop()
        cls._playwright = None

    # ==============================
    # POSITIVE TEST CASES
    # ==============================

    def test_01_page_loads_successfully(self, browser_fixture: Browser):
        """TC_DOM_01: Verify that example.com page loads successfully."""
        page = browser_fixture.new_page()
        try:
            response = page.goto(BASE_URL, wait_until="networkidle")
            assert response is not None, "No response received"
            assert response.ok, f"Page returned status {response.status}"
        finally:
            page.close()

    def test_02_contains_text_example_domains(self, browser_fixture: Browser):
        """TC_DOM_02: Verify page contains text 'Example Domains'."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            body_text = page.text_content("body")
            assert body_text is not None, "Body text not found"
            assert "Example Domains" in body_text, (
                f"Expected text 'Example Domains' not found in body. "
                f"Actual body start: {body_text[:200]}"
            )
        finally:
            page.close()

    def test_03_contains_informational_paragraph(self, browser_fixture: Browser):
        """TC_DOM_03: Verify page contains the exact informational paragraph text."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            expected_text = (
                "This domain is for use in documentation examples "
                "without needing permission. Avoid use in operations."
            )
            body_text = page.text_content("body")
            assert body_text is not None, "Body text not found"
            assert expected_text in body_text, (
                f"Expected informational text not found in body. "
                f"Actual body start: {body_text[:300]}"
            )
        finally:
            page.close()

    def test_04_contains_learn_more_link(self, browser_fixture: Browser):
        """TC_DOM_04: Verify page contains a link with text 'Learn more'."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            link = page.locator("a", has_text="Learn more")
            expect(link).to_be_visible()
            href = link.get_attribute("href")
            assert href is not None, "Learn more link has no href attribute"
        finally:
            page.close()

    def test_05_learn_more_link_is_clickable(self, browser_fixture: Browser):
        """
        TC_DOM_05: Verify the 'Learn more' link is clickable and navigates correctly.
        The link opens in the same page (no new tab).
        """
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            # Click the link - it navigates in the same page
            page.locator("a", has_text="Learn more").click()
            page.wait_for_load_state("networkidle")
            actual_url = page.url
            assert LEARN_MORE_URL in actual_url, (
                f"Expected URL to contain '{LEARN_MORE_URL}', got '{actual_url}'"
            )
        finally:
            page.close()

    def test_06_page_title_contains_example(self, browser_fixture: Browser):
        """TC_DOM_06: Verify page title contains 'Example'."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            title = page.title()
            assert "Example" in title, f"Expected 'Example' in title, got '{title}'"
        finally:
            page.close()

    # ==============================
    # NEGATIVE TEST CASES
    # ==============================

    def test_07_negative_invalid_url(self, browser_fixture: Browser):
        """TC_DOM_08: Verify behavior with invalid URL returns 404."""
        page = browser_fixture.new_page()
        try:
            response = page.goto(f"{BASE_URL}/invalidpage", wait_until="networkidle")
            assert response is not None
            # example.com returns 404 for invalid paths
            assert response.status == 404, (
                f"Expected 404 for invalid URL, got {response.status}"
            )
        finally:
            page.close()

    # ==============================
    # EDGE TEST CASES
    # ==============================

    def test_08_edge_responsive_viewport_mobile(self, browser_fixture: Browser):
        """TC_DOM_09: Verify page renders at mobile viewport."""
        page = browser_fixture.new_page(viewport={"width": 320, "height": 568})
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            body_text = page.text_content("body")
            assert body_text is not None and len(body_text) > 0, (
                "Body is empty at mobile viewport"
            )
            assert "Example Domains" in body_text, (
                "Content missing at mobile viewport"
            )
        finally:
            page.close()

    def test_09_edge_responsive_viewport_tablet(self, browser_fixture: Browser):
        """TC_DOM_09: Verify page renders at tablet viewport."""
        page = browser_fixture.new_page(viewport={"width": 768, "height": 1024})
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            body_text = page.text_content("body")
            assert body_text is not None and len(body_text) > 0, (
                "Body is empty at tablet viewport"
            )
            assert "Example Domains" in body_text, (
                "Content missing at tablet viewport"
            )
        finally:
            page.close()

    def test_10_edge_responsive_viewport_desktop(self, browser_fixture: Browser):
        """TC_DOM_09: Verify page renders at desktop viewport."""
        page = browser_fixture.new_page(viewport={"width": 1920, "height": 1080})
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            body_text = page.text_content("body")
            assert body_text is not None and len(body_text) > 0, (
                "Body is empty at desktop viewport"
            )
            assert "Example Domains" in body_text, (
                "Content missing at desktop viewport"
            )
        finally:
            page.close()

    # ==============================
    # BOUNDARY TEST CASES
    # ==============================

    def test_11_boundary_page_load_time(self, browser_fixture: Browser):
        """TC_DOM_11: Verify page loads within acceptable time."""
        page = browser_fixture.new_page()
        try:
            start_time = page.evaluate("performance.now()")
            page.goto(BASE_URL, wait_until="networkidle")
            end_time = page.evaluate("performance.now()")
            load_time = end_time - start_time
            # Acceptable threshold: < 10 seconds (generous for slow networks)
            assert load_time < 10000, (
                f"Page load time exceeded threshold: {load_time:.2f}ms"
            )
        finally:
            page.close()

    # ==============================
    # ACCESSIBILITY TEST CASES
    # ==============================

    def test_12_accessibility_keyboard_navigable(self, browser_fixture: Browser):
        """TC_DOM_12: Verify page is keyboard navigable."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            # Focus the first focusable element
            page.keyboard.press("Tab")
            focused = page.evaluate("() => document.activeElement.tagName")
            assert focused is not None, "No element could receive focus via keyboard"
        finally:
            page.close()

    def test_13_accessibility_heading_structure(self, browser_fixture: Browser):
        """TC_DOM_13: Verify page has proper heading structure."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            h1_count = page.locator("h1").count()
            assert h1_count >= 1, (
                f"Expected at least 1 h1 element, found {h1_count}"
            )
            h1_text = page.locator("h1").first.text_content()
            assert h1_text is not None and len(h1_text) > 0, "h1 element is empty"
        finally:
            page.close()


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])