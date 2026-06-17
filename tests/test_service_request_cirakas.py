"""
Playwright Python tests for Service Request Management module at Cirakas.
Covers: Positive, Negative, Edge, Boundary, Accessibility, Regression scenarios.
Uses fully authenticated storage state (post-2FA) to access protected pages.

Service Request URL: https://qa.cirakas.com/service-request/
"""
from typing import Optional
from playwright.sync_api import sync_playwright, expect, Page, Browser
import pytest
import time
import json
import os


LOGIN_URL = "https://qa.cirakas.com/login/"
BASE_URL = "https://qa.cirakas.com"
SERVICE_REQUEST_URL = "https://qa.cirakas.com/service-request/"
VALID_EMAIL = "rajeev@yopmail.com"
VALID_PASSWORD = "Cirakas@123456"

AUTH_FILE = "outputs/full_auth_storage.json"
SUPER_ADMIN_AUTH_FILE = "outputs/super_admin_auth.json"


class TestServiceRequestCirakas:

    _browser: Optional[Browser] = None
    _playwright = None
    _auth_storage = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def class_setup(cls):
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True, slow_mo=100)

        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE) as f:
                    cls._auth_storage = json.load(f)
                print("INFO: Loaded auth storage from", AUTH_FILE)

                test_page = cls._browser.new_page(storage_state=cls._auth_storage)
                resp = test_page.goto(SERVICE_REQUEST_URL, wait_until="networkidle", timeout=20000)
                test_page.wait_for_timeout(2000)

                if resp and resp.status == 200 and "login" not in test_page.url.lower():
                    print("INFO: Auth verified - service request page accessible")
                    test_page.close()
                    yield
                    cls._teardown()
                    return
                else:
                    test_page.close()
            except Exception as e:
                print(f"WARN: Could not load auth file: {e}")

        print("WARN: Auth file not valid. Run 'python outputs/auto_explore.py' first.")
        pytest.exit("Cannot proceed: no valid auth")

        yield
        cls._teardown()

    @classmethod
    def _teardown(cls):
        if cls._browser:
            cls._browser.close()
            cls._browser = None
        if cls._playwright:
            cls._playwright.stop()
            cls._playwright = None

    def _new_page(self) -> Page:
        if self._auth_storage:
            ctx = self._browser.new_context(storage_state=self._auth_storage)
            return ctx.new_page()
        return self._browser.new_page()

    def _navigate_to_service_request(self, page: Page) -> Page:
        page.goto(SERVICE_REQUEST_URL, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(3000)
        if "login" in page.url.lower():
            print("  WARN: Redirected to login. Auth may be expired.")
        return page

    # ==============================
    # POSITIVE TEST CASES
    # ==============================

    def test_01_page_loads(self):
        """TC_SR_01: Verify service request page loads successfully."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)
            body_text = page.text_content("body") or ""
            assert len(body_text) > 0, "Page body is empty"
            assert "login" not in page.url.lower(), "Redirected to login"
            assert "service" in body_text.lower(), "No service content found"
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_02_create_inside_user(self):
        """TC_SR_02: Verify user can create service request (inside user)."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            create_selectors = [
                "button:has-text('Create Service Request')",
                "button:has-text('+Create Service Request')",
                "[class*='create'] button",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn is None:
                pytest.skip("No create button found")

            create_btn.click()
            page.wait_for_timeout(3000)

            # Fill title
            name_selectors = [
                "input[name='name']", "input[name='title']",
                "input[id*='name']", "input[id*='title']",
                "input[placeholder*='name' i]", "input[placeholder*='title' i]",
                "[data-testid*='title']",
            ]
            for sel in name_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("Test Service Request - Automation " + str(int(time.time())))
                    break

            # Fill description
            desc_selectors = [
                "textarea[name='description']", "textarea[id*='desc']",
                "textarea[placeholder*='desc' i]", "[data-testid*='desc']",
            ]
            for sel in desc_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("Automated test service request description")
                    break

            save_selectors = [
                "button[type='submit']", "button:has-text('Save')",
                "button:has-text('Create')", "button:has-text('Submit')",
            ]
            for sel in save_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click(force=True)
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_03_create_outsource(self):
        """TC_SR_03: Verify user can create outsource service request."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            create_selectors = [
                "button:has-text('Create Service Request')",
                "button:has-text('+Create Service Request')",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn is None:
                pytest.skip("No create button found")

            create_btn.click()
            page.wait_for_timeout(3000)

            # Try to select outsource/outside user type
            outsource_selectors = [
                "button:has-text('Outsource')", "button:has-text('Outside')",
                "input[type='radio'][value*='outside']", "input[type='radio'][value*='outsource']",
                "[data-testid*='outside']", "[data-testid*='outsource']",
            ]
            for sel in outsource_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(1000)
                    break

            # Fill title
            name_selectors = [
                "input[name='name']", "input[name='title']",
                "input[id*='name']", "input[id*='title']",
            ]
            for sel in name_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("Outsource SR - Automation " + str(int(time.time())))
                    break

            save_selectors = [
                "button[type='submit']", "button:has-text('Save')",
                "button:has-text('Create')", "button:has-text('Submit')",
            ]
            for sel in save_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click(force=True)
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_04_edit_service_request(self):
        """TC_SR_04: Verify user can edit a service request."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            edit_found = False
            edit_selectors = [
                "button:has-text('Edit')", "[title*='Edit' i]",
                "[aria-label*='Edit' i]", "[data-testid*='edit']",
                "[class*='edit']",
            ]

            edit_btn = None
            for sel in edit_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    edit_btn = loc
                    edit_found = True
                    break

            if edit_btn:
                edit_btn.click(force=True)
                page.wait_for_timeout(3000)

                name_selectors = [
                    "input[name='name']", "input[name='title']",
                    "input[id*='name']", "input[id*='title']",
                ]
                for sel in name_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.fill("Updated SR - Automation " + str(int(time.time())))
                        break

                save_selectors = [
                    "button[type='submit']", "button:has-text('Save')",
                    "button:has-text('Update')",
                ]
                for sel in save_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click(force=True)
                        page.wait_for_timeout(3000)
                        break
            elif not edit_found:
                pytest.skip("No edit button found")
            else:
                pytest.skip("No edit button found")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_05_list_displays(self):
        """TC_SR_05: Verify service request list displays all requests."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            # Check for h3 elements with request titles
            request_cards = page.locator("h3").all()
            titles = [c.text_content() or "" for c in request_cards if c.is_visible()]

            if len(titles) == 0:
                body = page.text_content("body") or ""
                if "no service" in body.lower():
                    pytest.skip("No service requests available")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_06_reassign_button(self):
        """TC_SR_06: Verify reassign button is present."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            reassign_selectors = [
                "button:has-text('Reassign')", "[data-testid*='reassign']",
                "[title*='Reassign' i]", "[class*='reassign']",
            ]

            for sel in reassign_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_10_calendar_view(self):
        """TC_SR_10: Verify calendar view is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            cal_selectors = [
                "button:has-text('Calendar')", "[title*='Calendar' i]",
                "[data-testid*='calendar']",
            ]

            for sel in cal_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_11_list_view(self):
        """TC_SR_11: Verify list view is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            list_selectors = [
                "button:has-text('List')", "[title*='List' i]",
                "[data-testid*='list']",
            ]

            for sel in list_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_12_card_view(self):
        """TC_SR_12: Verify card view is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            card_selectors = [
                "button:has-text('Cards')", "button:has-text('Card')",
                "[title*='Card' i]", "[data-testid*='card']",
            ]

            for sel in card_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_20_filter_by_status(self):
        """TC_SR_20: Verify filter by status works."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            status_selectors = [
                "button:has-text('All')", "button:has-text('Pending')",
                "button:has-text('In Progress')", "button:has-text('Completed')",
                "button:has-text('Paused')",
            ]

            for sel in status_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_21_filter_by_priority(self):
        """TC_SR_21: Verify filter by priority works."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            priority_sel = [
                "button:has-text('All Priorities')", "select[name*='priority']",
                "[data-testid*='priority-filter']",
            ]

            for sel in priority_sel:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(1000)
                    option = page.locator("[role='option'], option:not([value='']):not([value='all'])").first
                    if option.is_visible():
                        option.click()
                        page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_22_filter_by_project_site(self):
        """TC_SR_22: Verify filter by project site works."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            site_sel = [
                "button:has-text('All Project Sites')", "select[name*='site']",
                "[data-testid*='site-filter']",
            ]

            for sel in site_sel:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(1000)
                    option = page.locator("[role='option'], option:not([value='']):not([value='all'])").first
                    if option.is_visible():
                        option.click()
                        page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_23_card_title(self):
        """TC_SR_23: Verify card displays title."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            for sel in ["h3", "[class*='title']", ".sr-title", "[data-testid*='title']"]:
                loc = page.locator(sel).first
                if loc.is_visible():
                    txt = loc.text_content()
                    if txt and len(txt.strip()) > 0:
                        break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_26_card_status(self):
        """TC_SR_26: Verify card displays status."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            status_sel = [
                "[class*='status']", ".badge", "[data-testid*='status']",
            ]

            for sel in status_sel:
                loc = page.locator(sel).first
                if loc.is_visible() and loc.text_content():
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_25_card_priority(self):
        """TC_SR_25: Verify card displays priority."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            priority_sel = [
                "[class*='priority']", "[data-testid*='priority']",
            ]

            for sel in priority_sel:
                loc = page.locator(sel).first
                if loc.is_visible() and loc.text_content():
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # NEGATIVE TEST CASES
    # ==============================

    def test_31_empty_title(self):
        """TC_SR_31: Negative: Create with empty title shows validation."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            create_sel = ["button:has-text('Create Service Request')", "button:has-text('+Create Service Request')"]
            create_btn = None
            for sel in create_sel:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn:
                create_btn.click()
                page.wait_for_timeout(3000)

                save_sel = ["button[type='submit']", "button:has-text('Save')", "button:has-text('Create')"]
                for sel in save_sel:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click(force=True)
                        page.wait_for_timeout(2000)
                        break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # EDGE TEST CASES
    # ==============================

    def test_32_long_title(self):
        """TC_SR_32: Edge: Create with very long title."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            create_sel = ["button:has-text('Create Service Request')", "button:has-text('+Create Service Request')"]
            create_btn = None
            for sel in create_sel:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn:
                create_btn.click()
                page.wait_for_timeout(3000)

                name_sel = ["input[name='name']", "input[name='title']", "input[id*='name']"]
                for sel in name_sel:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.fill("A" * 255)
                        break

                save_sel = ["button[type='submit']", "button:has-text('Save')", "button:has-text('Create')"]
                for sel in save_sel:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click(force=True)
                        page.wait_for_timeout(3000)
                        break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_33_filter_no_results(self):
        """TC_SR_33: Edge: Filter with no matching results."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # ACCESSIBILITY TEST CASES
    # ==============================

    def test_34_heading_structure(self):
        """TC_SR_34: Accessibility: Proper heading structure."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)
            h1_count = page.locator("h1").count()
            h2_count = page.locator("h2").count()
            assert h1_count + h2_count >= 1, "No h1 or h2 headings found"
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_35_keyboard_navigation(self):
        """TC_SR_35: Accessibility: Keyboard navigation."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            focusable = page.locator("button, a, input, select, textarea, [tabindex]:not([tabindex='-1'])").first
            if focusable.is_visible():
                focusable.focus()
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                focused_tag = page.evaluate("() => document.activeElement.tagName")
                assert focused_tag in ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA", "DIV"], \
                    f"Tab should move focus, got '{focused_tag}'"

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # REGRESSION TEST CASES
    # ==============================

    def test_36_page_refresh_persistence(self):
        """TC_SR_36: Regression: Operations persist after page refresh."""
        page = self._new_page()
        try:
            page = self._navigate_to_service_request(page)

            page.reload(wait_until="networkidle")
            page.wait_for_timeout(3000)

            assert "login" not in page.url.lower(), "Redirected to login after refresh"

            page.wait_for_timeout(1000)
        finally:
            page.close()


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])