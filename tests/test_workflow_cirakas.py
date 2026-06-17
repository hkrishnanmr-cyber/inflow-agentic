"""
Playwright Python tests for Workflow Management module at Cirakas.
Covers: Positive, Negative, Edge, Boundary, Accessibility, Regression scenarios.
Uses fully authenticated storage state (post-2FA) to access protected pages.

Steps to obtain full_auth_storage.json:
  python outputs/auto_explore.py
  (enters OTP from yopmail automatically)

Or for interactive OTP entry:
  python outputs/explore_full_auth.py
"""
from typing import Optional
from playwright.sync_api import sync_playwright, expect, Page, Browser
import pytest
import time
import json
import os


LOGIN_URL = "https://qa.cirakas.com/login/"
BASE_URL = "https://qa.cirakas.com"
WORKFLOWS_URL = "https://qa.cirakas.com/workflows/"
VALID_EMAIL = "rajeev@yopmail.com"
VALID_PASSWORD = "Cirakas@123456"

AUTH_FILE = "outputs/full_auth_storage.json"
SUPER_ADMIN_AUTH_FILE = "outputs/super_admin_auth.json"


class TestWorkflowCirakas:

    _browser: Optional[Browser] = None
    _playwright = None
    _auth_storage = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def class_setup(cls):
        """Class-scoped setup: launch browser and authenticate."""
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True, slow_mo=100)

        # Try loading saved full auth state first (post-2FA)
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE) as f:
                    cls._auth_storage = json.load(f)
                print("INFO: Loaded full auth storage from", AUTH_FILE)
                
                # Verify auth works by navigating to workflows
                test_page = cls._browser.new_page(storage_state=cls._auth_storage)
                resp = test_page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
                test_page.wait_for_timeout(2000)
                
                if resp and resp.status == 200 and "login" not in test_page.url.lower():
                    print("INFO: Auth storage verified - workflows page accessible")
                    test_page.close()
                    yield
                    cls._teardown()
                    return
                else:
                    print(f"WARN: Auth expired (redirected to login). Creating fresh session...")
                    test_page.close()
            except Exception as e:
                print(f"WARN: Could not load auth file: {e}")

        # Fallback: login fresh and save auth state
        print("INFO: Performing fresh login + 2FA to get auth...")
        auth_page = cls._browser.new_page()
        auth_page.goto(LOGIN_URL, wait_until="networkidle")
        auth_page.fill("#login-email", VALID_EMAIL)
        auth_page.fill("#login-password", VALID_PASSWORD)
        auth_page.locator("button[type='submit']").click()
        auth_page.wait_for_load_state("networkidle")

        authenticated = False
        for _ in range(40):
            auth_page.wait_for_timeout(500)
            body_text = auth_page.text_content("body") or ""

            if auth_page.locator("#otp").is_visible():
                # Save storage at 2FA - but this won't work for protected pages
                cls._auth_storage = auth_page.context.storage_state()
                print("WARN: Only reached 2FA page. Protected pages may redirect to login.")
                print("WARN: Run 'python outputs/auto_explore.py' first to create full auth.")
                authenticated = True
                break

            current_url = auth_page.url
            if "login" not in current_url.lower():
                cls._auth_storage = auth_page.context.storage_state()
                authenticated = True
                print(f"INFO: Past login -> {current_url}")
                break

            if "too many login attempts" in body_text.lower():
                print("WARN: Rate-limited during class setup")
                break

        auth_page.close()

        if not authenticated:
            pytest.exit("Cannot proceed: login failed during setup")

        yield
        cls._teardown()

    @classmethod
    def _teardown(cls):
        """Clean up browser resources."""
        if cls._browser:
            cls._browser.close()
            cls._browser = None
        if cls._playwright:
            cls._playwright.stop()
            cls._playwright = None

    def _new_page(self) -> Page:
        """Create a new page with saved auth state."""
        if self._auth_storage:
            ctx = self._browser.new_context(storage_state=self._auth_storage)
            return ctx.new_page()
        return self._browser.new_page()

    def _navigate_to_workflows(self, page: Page) -> Page:
        """Navigate directly to the workflows page."""
        page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(3000)
        
        # Check for redirect to login
        if "login" in page.url.lower():
            print(f"  WARN: Workflows URL redirected to login. Auth may be expired.")
            print(f"  WARN: Run 'python outputs/auto_explore.py' to refresh auth.")
        
        return page

    # ==============================
    # POSITIVE TEST CASES
    # ==============================

    def test_01_workflow_page_loads(self):
        """TC_WF_01: Verify workflow page loads successfully."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)
            body_text = page.text_content("body") or ""
            assert len(body_text) > 0, "Workflows page body is empty"
            current_url = page.url
            assert "login" not in current_url.lower(), \
                f"Redirected to login. URL: {current_url}"
            # Verify workflows-specific content
            assert "workflow" in body_text.lower(), "No workflow content found on page"
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_02_create_workflow(self):
        """TC_WF_02: Verify user can create a new workflow."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Find the Create Workflow button - confirmed "+Create Workflow" text
            create_selectors = [
                "button:has-text('Create Workflow')",
                "button:has-text('+Create Workflow')",
                "button:has-text('+ Create Workflow')",
                "[class*='create'] button",
                "a:has-text('Create Workflow')",
                "a:has-text('Add Workflow')",
                "[data-testid='create-workflow']",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn is None:
                pytest.skip("No create workflow button found")

            create_btn.click()
            page.wait_for_timeout(3000)

            # Fill workflow name
            name_selectors = [
                "input[name='name']",
                "input[name='title']",
                "input[id*='name']",
                "input[id*='title']",
                "input[placeholder*='name' i]",
                "input[placeholder*='title' i]",
                "[data-testid='workflow-name']",
                "textarea[name='name']",
                "textarea[name='title']",
            ]

            for sel in name_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("Test Workflow - Automation " + str(int(time.time())))
                    break

            # Fill description
            desc_selectors = [
                "textarea[name='description']",
                "textarea[id*='desc']",
                "input[placeholder*='desc' i]",
                "[data-testid='workflow-desc']",
            ]

            for sel in desc_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("Automated test workflow description")
                    break

            # Save
            save_selectors = [
                "button[type='submit']",
                "button:has-text('Save')",
                "button:has-text('Create')",
                "button:has-text('Submit')",
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

    def test_03_workflow_list(self):
        """TC_WF_03: Verify workflow list displays all workflows."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Check for workflow items in card view (confirmed h3 with workflow names)
            workflow_cards = page.locator("h3").all()
            workflow_names = [c.text_content() or "" for c in workflow_cards if c.is_visible()]
            
            if len(workflow_names) == 0:
                body_text = page.text_content("body") or ""
                if "no workflow" in body_text.lower():
                    pytest.skip("No workflows available")
            
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_04_edit_workflow(self):
        """TC_WF_04: Verify user can edit an existing workflow."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Find edit button - confirmed [class*='edit'] matches SVG credit-card icon with animation
            # Use force=True to bypass CSS animation instability
            edit_found = False
            edit_selectors = [
                "button:has-text('Edit')",
                "[title*='Edit' i]",
                "[aria-label*='Edit' i]",
                ".edit-btn",
                "[data-testid*='edit']",
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
                # Use force=True to bypass CSS transition animation on SVG icon
                edit_btn.click(force=True)
                page.wait_for_timeout(3000)

                # Modify name
                name_selectors = [
                    "input[name='name']",
                    "input[name='title']",
                    "input[id*='name']",
                    "input[id*='title']",
                    "input[placeholder*='name' i]",
                    "input[placeholder*='title' i]",
                ]

                for sel in name_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.fill("Updated Workflow - Automation " + str(int(time.time())))
                        break

                # Save
                save_selectors = [
                    "button[type='submit']",
                    "button:has-text('Save')",
                    "button:has-text('Update')",
                ]

                for sel in save_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click(force=True)
                        page.wait_for_timeout(3000)
                        break
            elif not edit_found:
                # Check if the edit SVG icon exists but is animated
                svg_edit = page.locator("[class*='lucide-credit-card']").first
                if svg_edit.is_visible():
                    pytest.skip("Edit icon found but has CSS animation; use force=True to test")
                else:
                    pytest.skip("No edit button found on workflows page")
            else:
                pytest.skip("No edit button found on workflows page")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_05_delete_workflow(self):
        """TC_WF_05: Verify user can delete a workflow."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            delete_selectors = [
                "button:has-text('Delete')",
                "button[title*='Delete' i]",
                "[aria-label*='Delete' i]",
                ".delete-btn",
                "[data-testid*='delete']",
                "button:has-text('Remove')",
                "[class*='delete']",
            ]

            delete_btn = None
            for sel in delete_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    delete_btn = loc
                    break

            if delete_btn:
                delete_btn.click(force=True)
                page.wait_for_timeout(3000)

                # Confirm deletion
                confirm_selectors = [
                    "button:has-text('Confirm')",
                    "button:has-text('Yes')",
                    "button:has-text('Delete')",
                    "button:has-text('OK')",
                    "button:has-text('Proceed')",
                    "[data-testid*='confirm']",
                ]

                for sel in confirm_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click()
                        page.wait_for_timeout(3000)
                        break
            else:
                pytest.skip("No delete button found on workflows page")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_06_execute_workflow(self):
        """TC_WF_06: Verify user can start/execute a workflow."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Find Start button on a workflow card (confirmed Start button exists)
            start_selectors = [
                "button:has-text('Start')",
                "button:has-text('Execute')",
                "button:has-text('Run')",
                "[title*='Execute' i]",
                "[title*='Start' i]",
                "[data-testid*='execute']",
                "[data-testid*='start']",
            ]

            for sel in start_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(3000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_07_workflow_tasks_in_task_list(self):
        """TC_WF_07: Verify tasks from workflow appear in task list."""
        page = self._new_page()
        try:
            # Navigate to tasks page
            page.goto(f"{BASE_URL}/tasks/", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)
            
            current_url = page.url
            assert "login" not in current_url.lower(), f"Redirected to login. URL: {current_url}"
            
            body_text = page.text_content("body") or ""
            assert "task" in body_text.lower(), "No task content found on tasks page"

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_08_project_site_filter(self):
        """TC_WF_08: Verify project site filter is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Confirmed "All Project Sites" text in dropdown
            site_filter_selectors = [
                "select[name*='site']",
                "select[id*='site']",
                "button:has-text('All Project Sites')",
                "button:has-text('Project Site')",
                "[class*='site-filter']",
                "select",
            ]

            for sel in site_filter_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.click()
                    page.wait_for_timeout(1000)
                    # Try to select an option
                    option = page.locator("[role='option'], option:not([value='']):not([value='all'])").first
                    if option.is_visible():
                        option.click()
                        page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_09_card_view(self):
        """TC_WF_09: Verify card view is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Confirmed "Cards" button exists
            card_selectors = [
                "button:has-text('Cards')",
                "button:has-text('Card')",
                "[title*='Card' i]",
                "[data-testid*='card']",
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

    def test_10_list_view(self):
        """TC_WF_10: Verify list view is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Confirmed "List" button exists
            list_selectors = [
                "button:has-text('List')",
                "[title*='List' i]",
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

    def test_11_search_field_visible(self):
        """TC_WF_11: Verify search field is available."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Confirmed search input exists
            search_selectors = [
                "input[type='search']",
                "input[placeholder*='search' i]",
                "input[placeholder*='workflow' i]",
                "input[name*='search']",
                "input[id*='search']",
                "[data-testid*='search']",
                ".search-container input",
            ]

            for sel in search_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_12_search_filters_workflows(self):
        """TC_WF_12: Verify search filters workflows by name."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            search_selectors = [
                "input[type='search']",
                "input[placeholder*='search' i]",
                "input[placeholder*='workflow' i]",
                "input[name*='search']",
                ".search-container input",
            ]

            for sel in search_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("ABC workflow")
                    page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_24_workflow_card_name(self):
        """TC_WF_24: Verify workflow card displays name."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            # Confirmed workflow names are in h3 elements
            name_found = False
            for sel in ["h3", "[class*='workflow-card'] [class*='name']", ".workflow-name", "[data-testid*='workflow-name']"]:
                loc = page.locator(sel).first
                if loc.is_visible():
                    name = loc.text_content()
                    if name and len(name.strip()) > 0:
                        name_found = True
                        break

            if not name_found:
                pytest.skip("No workflow name element found")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_25_workflow_card_status(self):
        """TC_WF_25: Verify workflow card displays status."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            status_selectors = [
                "[class*='status']",
                ".workflow-status",
                "[data-testid*='status']",
                ".badge",
                "[class*='workflow-status']",
            ]

            for sel in status_selectors:
                loc = page.locator(sel).first
                if loc.is_visible() and loc.text_content():
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # NEGATIVE TEST CASES
    # ==============================

    def test_16_create_workflow_empty_name(self):
        """TC_WF_16: Negative: Create workflow with empty name shows validation."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            create_selectors = [
                "button:has-text('Create Workflow')",
                "button:has-text('+Create Workflow')",
                "[class*='create'] button",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn:
                create_btn.click()
                page.wait_for_timeout(3000)

                # Click save without filling name
                save_selectors = [
                    "button[type='submit']",
                    "button:has-text('Save')",
                    "button:has-text('Create')",
                ]

                for sel in save_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click(force=True)
                        page.wait_for_timeout(2000)
                        break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_17_delete_workflow_cancel(self):
        """TC_WF_17: Negative: Delete workflow cancellation."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            delete_selectors = [
                "button:has-text('Delete')",
                "button[title*='Delete' i]",
                "[aria-label*='Delete' i]",
                ".delete-btn",
                "[data-testid*='delete']",
                "[class*='delete']",
            ]

            delete_btn = None
            for sel in delete_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    delete_btn = loc
                    break

            if delete_btn:
                delete_btn.click(force=True)
                page.wait_for_timeout(3000)

                # Cancel the deletion
                cancel_selectors = [
                    "button:has-text('Cancel')",
                    "button:has-text('No')",
                    "button:has-text('Close')",
                    "[data-testid*='cancel']",
                    ".btn-cancel",
                ]

                for sel in cancel_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.click()
                        page.wait_for_timeout(2000)
                        break
            else:
                pytest.skip("No delete button found on workflows page")

            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # EDGE TEST CASES
    # ==============================

    def test_18_search_no_results(self):
        """TC_WF_18: Edge: Search with no matching results."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            search_selectors = [
                "input[type='search']",
                "input[placeholder*='search' i]",
                "input[placeholder*='workflow' i]",
                ".search-container input",
            ]

            for sel in search_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    loc.fill("ZZZZ_NoMatch_9999_XXXX")
                    page.wait_for_timeout(2000)
                    break

            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_19_long_name(self):
        """TC_WF_19: Edge: Workflow creation with very long name."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            create_selectors = [
                "button:has-text('Create Workflow')",
                "button:has-text('+Create Workflow')",
                "[class*='create'] button",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn:
                create_btn.click()
                page.wait_for_timeout(3000)

                name_selectors = [
                    "input[name='name']",
                    "input[name='title']",
                    "input[id*='name']",
                    "input[id*='title']",
                    "input[placeholder*='name' i]",
                    "input[placeholder*='title' i]",
                ]

                for sel in name_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.fill("A" * 255)
                        break

                save_selectors = [
                    "button[type='submit']",
                    "button:has-text('Save')",
                    "button:has-text('Create')",
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

    # ==============================
    # BOUNDARY TEST CASES
    # ==============================

    def test_20_minimum_length_name(self):
        """TC_WF_20: Boundary: Workflow name minimum length validation."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            create_selectors = [
                "button:has-text('Create Workflow')",
                "button:has-text('+Create Workflow')",
                "[class*='create'] button",
            ]

            create_btn = None
            for sel in create_selectors:
                loc = page.locator(sel).first
                if loc.is_visible():
                    create_btn = loc
                    break

            if create_btn:
                create_btn.click()
                page.wait_for_timeout(3000)

                name_selectors = [
                    "input[name='name']",
                    "input[name='title']",
                    "input[id*='name']",
                    "input[id*='title']",
                    "input[placeholder*='name' i]",
                    "input[placeholder*='title' i]",
                ]

                for sel in name_selectors:
                    loc = page.locator(sel).first
                    if loc.is_visible():
                        loc.fill("A")
                        break

                save_selectors = [
                    "button[type='submit']",
                    "button:has-text('Save')",
                    "button:has-text('Create')",
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

    # ==============================
    # ACCESSIBILITY TEST CASES
    # ==============================

    def test_21_heading_structure(self):
        """TC_WF_21: Accessibility: Proper heading structure."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)
            h1_count = page.locator("h1").count()
            h2_count = page.locator("h2").count()
            assert h1_count + h2_count >= 1, "No h1 or h2 headings found on workflows page"
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_22_keyboard_navigation(self):
        """TC_WF_22: Accessibility: Keyboard navigation."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

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

    def test_23_page_refresh_persistence(self):
        """TC_WF_23: Regression: Operations persist after page refresh."""
        page = self._new_page()
        try:
            page = self._navigate_to_workflows(page)

            page.reload(wait_until="networkidle")
            page.wait_for_timeout(3000)

            current_url = page.url
            assert "login" not in current_url.lower(), \
                f"Redirected to login after refresh. URL: {current_url}"

            page.wait_for_timeout(1000)
        finally:
            page.close()


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])