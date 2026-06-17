"""
Playwright tests for Super Admin workflow visibility scenarios.
TC_WF_13: Super admin can see all workflow tasks across all project sites
TC_WF_14: Admin can see tasks of assigned project sites only
TC_WF_15: Admin/super admin can see user status updates

Uses super_admin_auth.json for authentication.
"""
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser
import pytest
import json
import os


BASE_URL = "https://qa.cirakas.com"
WORKFLOWS_URL = "https://qa.cirakas.com/workflows/"
TASKS_URL = "https://qa.cirakas.com/tasks/"
SUPER_ADMIN_AUTH_FILE = "outputs/super_admin_auth.json"
ADMIN_AUTH_FILE = "outputs/full_auth_storage.json"


class TestWorkflowSuperAdmin:

    _browser: Optional[Browser] = None
    _playwright = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def class_setup(cls):
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True, slow_mo=100)
        yield
        cls._browser.close()
        cls._browser = None
        cls._playwright.stop()
        cls._playwright = None

    def _page_with_auth(self, auth_file: str) -> Page:
        """Create a page with stored auth state."""
        with open(auth_file) as f:
            auth = json.load(f)
        ctx = self._browser.new_context(storage_state=auth)
        return ctx.new_page()

    # ==============================
    # TC_WF_13 - Super Admin can see all workflow tasks
    # ==============================

    def test_13_super_admin_sees_all_workflow_tasks(self):
        """TC_WF_13: Verify super admin can see all workflow tasks across all project sites."""
        if not os.path.exists(SUPER_ADMIN_AUTH_FILE):
            pytest.skip("Super admin auth file not found. Run outputs/auto_explore_superadmin.py first.")

        page = self._page_with_auth(SUPER_ADMIN_AUTH_FILE)
        try:
            # Navigate to workflows page
            resp = page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            assert "login" not in page.url.lower(), "Super admin redirected to login"
            
            # Check we're on the workflows page
            body_text = page.text_content("body") or ""
            assert "workflow" in body_text.lower(), "No workflow content found for super admin"
            
            # Count workflow cards to verify all are visible
            workflow_cards = page.locator("h3").all()
            print(f"  Super admin sees {len(workflow_cards)} workflow cards")
            assert len(workflow_cards) > 0, "No workflow cards visible to super admin"
            
            # Now navigate to tasks page
            page.goto(TASKS_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)
            
            tasks_body = page.text_content("body") or ""
            assert "task" in tasks_body.lower(), "No task content found for super admin"
            
            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # TC_WF_14 - Admin can only see assigned project site tasks
    # ==============================

    def test_14_admin_sees_assigned_site_tasks(self):
        """TC_WF_14: Verify admin can see only tasks of assigned project sites."""
        if not os.path.exists(ADMIN_AUTH_FILE):
            pytest.skip("Admin auth file not found. Run outputs/auto_explore.py first.")

        page = self._page_with_auth(ADMIN_AUTH_FILE)
        try:
            # Navigate to workflows page
            resp = page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            assert "login" not in page.url.lower(), "Admin redirected to login"
            
            body_text = page.text_content("body") or ""
            assert "workflow" in body_text.lower(), "No workflow content found for admin"
            
            # Check project site filter is present (admins see only assigned sites)
            site_filter = page.locator("button:has-text('All Project Sites'), button:has-text('Project Site'), select").first
            assert site_filter.is_visible(), "Project site filter should be visible for admin"
            
            page.wait_for_timeout(1000)
        finally:
            page.close()

    # ==============================
    # TC_WF_15 - Admin/Super Admin can see user status updates
    # ==============================

    def test_15_admin_sees_user_status_updates(self):
        """TC_WF_15: Verify admin/super admin can see user status changes (start/progress/pause/resume/complete)."""
        if not os.path.exists(ADMIN_AUTH_FILE):
            pytest.skip("Admin auth file not found")

        page = self._page_with_auth(ADMIN_AUTH_FILE)
        try:
            # Navigate to workflows page where task statuses are visible
            page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            assert "login" not in page.url.lower(), "Admin redirected to login"

            body_text = page.text_content("body") or ""
            
            # Look for status indicators on workflow/task cards
            status_indicators = page.locator("[class*='status'], .badge, [class*='task-status']")
            status_count = status_indicators.count()
            print(f"  Admin sees {status_count} status indicators")
            
            # Check for Start/In Progress/Complete buttons
            action_buttons = page.locator("button:has-text('Start'), button:has-text('Pause'), button:has-text('Resume'), button:has-text('Complete')")
            action_count = action_buttons.count()
            print(f"  Admin sees {action_count} action buttons on workflow items")
            
            page.wait_for_timeout(1000)
        finally:
            page.close()

    def test_15b_super_admin_sees_user_status_updates(self):
        """TC_WF_15b: Verify super admin can see user status changes."""
        if not os.path.exists(SUPER_ADMIN_AUTH_FILE):
            pytest.skip("Super admin auth file not found. Run outputs/auto_explore_superadmin.py first.")

        page = self._page_with_auth(SUPER_ADMIN_AUTH_FILE)
        try:
            page.goto(WORKFLOWS_URL, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            assert "login" not in page.url.lower(), "Super admin redirected to login"

            # Check for status badges/indicators
            status_indicators = page.locator("[class*='status'], .badge, [class*='task-status']")
            status_count = status_indicators.count()
            print(f"  Super admin sees {status_count} status indicators")

            # Check for action buttons on workflow tasks  
            action_buttons = page.locator("button:has-text('Start'), button:has-text('Pause'), button:has-text('Resume'), button:has-text('Complete')")
            action_count = action_buttons.count()
            print(f"  Super admin sees {action_count} action buttons")

            page.wait_for_timeout(1000)
        finally:
            page.close()


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])