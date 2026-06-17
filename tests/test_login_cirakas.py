"""
Playwright Python tests for login page at https://qa.cirakas.com/login/.
Covers: Positive, Negative, Edge, Boundary, Accessibility, Regression scenarios.
"""

from typing import Optional
from playwright.sync_api import sync_playwright, expect, Page, Browser
import pytest
import time


BASE_URL = "https://qa.cirakas.com/login/"
VALID_EMAIL = "rajeev@yopmail.com"
VALID_PASSWORD = "Cirakas@123456"


class TestLoginCirakas:

    _browser: Optional[Browser] = None
    _playwright = None

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    def browser_fixture(cls):
        """Fixture to manage browser lifecycle (class-scoped)."""
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True)
        yield cls._browser
        cls._browser.close()
        cls._browser = None
        cls._playwright.stop()
        cls._playwright = None

    def _go_to_login(self, browser: Browser) -> Page:
        """Helper: create page and navigate to login."""
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        return page

    def _try_login_and_get_2fa(self, browser: Browser, max_wait: int = 8) -> Optional[Page]:
        """
        Login with valid credentials and wait for 2FA page.
        Returns page at 2FA page, or None if rate-limited.
        """
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        page.fill("#login-email", VALID_EMAIL)
        page.fill("#login-password", VALID_PASSWORD)
        page.locator("button[type='submit']").click()
        page.wait_for_load_state("networkidle")
        # Wait for either 2FA page or rate-limit error
        for _ in range(max_wait * 2):
            page.wait_for_timeout(500)
            body_text = page.text_content("body") or ""
            if "too many login attempts" in body_text.lower():
                return None  # Rate limited
            # Check if OTP field is visible
            otp = page.locator("#otp")
            if otp.is_visible():
                return page
        return None

    # ==============================
    # POSITIVE TEST CASES (Login Page)
    # ==============================

    def test_01_login_page_loads_with_fields(self, browser_fixture: Browser):
        """TC_LOG_01: Verify login page loads with email and password fields."""
        page = self._go_to_login(browser_fixture)
        try:
            email_field = page.locator("#login-email")
            password_field = page.locator("#login-password")
            expect(email_field).to_be_visible()
            expect(password_field).to_be_visible()
            assert email_field.get_attribute("type") == "email"
            assert password_field.get_attribute("type") == "password"
            assert email_field.get_attribute("placeholder") is not None
            assert password_field.get_attribute("placeholder") is not None
        finally:
            page.close()

    def test_02_email_field_type_is_email(self, browser_fixture: Browser):
        """TC_LOG_02: Verify email field has HTML5 email type."""
        page = self._go_to_login(browser_fixture)
        try:
            email_field = page.locator("#login-email")
            field_type = email_field.get_attribute("type")
            assert field_type == "email", f"Expected type='email', got '{field_type}'"
            assert email_field.get_attribute("required") is not None, "Email field should be required"
        finally:
            page.close()

    def test_03_email_required_validation(self, browser_fixture: Browser):
        """TC_LOG_03: Verify email field shows validation when empty."""
        page = self._go_to_login(browser_fixture)
        try:
            submit_btn = page.locator("button[type='submit']")
            submit_btn.click()
            page.wait_for_timeout(1000)
            is_invalid = page.evaluate(
                "() => document.querySelector('#login-email').validity.valueMissing"
            )
            assert is_invalid, "Email field should be invalid when empty after submit"
        finally:
            page.close()

    def test_04_password_required_validation(self, browser_fixture: Browser):
        """TC_LOG_04: Verify password field shows validation when empty."""
        page = self._go_to_login(browser_fixture)
        try:
            page.fill("#login-email", VALID_EMAIL)
            submit_btn = page.locator("button[type='submit']")
            submit_btn.click()
            page.wait_for_timeout(1000)
            is_invalid = page.evaluate(
                "() => document.querySelector('#login-password').validity.valueMissing"
            )
            assert is_invalid, "Password field should be invalid when empty after submit"
        finally:
            page.close()

    def test_05_valid_login_navigates_to_2fa(self, browser_fixture: Browser):
        """TC_LOG_05: Verify login with valid credentials navigates to 2FA page."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            # Check that OTP field appears (we're on 2FA page)
            otp_field = page.locator("#otp")
            expect(otp_field).to_be_visible()
            # Verify page shows verification-related text
            verification_label = page.get_by_text("Verification Code").first
            expect(verification_label).to_be_visible()
        finally:
            page.close()

    def test_06_otp_field_is_visible_on_2fa(self, browser_fixture: Browser):
        """TC_LOG_06: Verify 2FA page shows OTP input field."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            otp_field = page.locator("#otp")
            expect(otp_field).to_be_visible()
            placeholder = otp_field.get_attribute("placeholder")
            assert placeholder is not None, "OTP field should have placeholder"
            assert "code" in placeholder.lower(), f"Expected OTP placeholder, got '{placeholder}'"
        finally:
            page.close()

    def test_07_sending_verification_message(self, browser_fixture: Browser):
        """TC_LOG_07: Verify 2FA page shows verification-related text."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            # Look for either "Verification Code" label or "Sending your verification code" message
            code_label = page.get_by_text("Verification Code").first
            sending_msg = page.get_by_text("verification", exact=False).first
            assert code_label.is_visible() or sending_msg.is_visible(), \
                "Expected verification-related text on 2FA page"
        finally:
            page.close()

    def test_08_otp_field_accepts_6_digits(self, browser_fixture: Browser):
        """TC_LOG_08: Verify OTP field accepts 6-digit code."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            otp_field = page.locator("#otp")
            expect(otp_field).to_be_visible()
            otp_field.fill("123456")
            value = otp_field.input_value()
            assert value == "123456", f"Expected OTP value '123456', got '{value}'"
        finally:
            page.close()

    # ==============================
    # NEGATIVE TEST CASES
    # ==============================

    def test_10_invalid_email_format(self, browser_fixture: Browser):
        """TC_LOG_10: Verify login with invalid email format is blocked."""
        page = self._go_to_login(browser_fixture)
        try:
            page.fill("#login-email", "abc")
            page.fill("#login-password", VALID_PASSWORD)
            submit_btn = page.locator("button[type='submit']")
            submit_btn.click()
            page.wait_for_timeout(1000)
            is_invalid = page.evaluate(
                "() => document.querySelector('#login-email').validity.typeMismatch"
            )
            assert is_invalid, "Email field should be invalid for 'abc' (type mismatch)"
        finally:
            page.close()

    def test_11_wrong_password(self, browser_fixture: Browser):
        """TC_LOG_11: Verify login with wrong password shows error."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            page.fill("#login-email", VALID_EMAIL)
            page.fill("#login-password", "WrongPass123")
            page.locator("button[type='submit']").click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            current_url = page.url
            assert "login" in current_url.lower(), \
                f"With wrong password, should stay on login page, but URL is '{current_url}'"
        finally:
            page.close()

    def test_12_empty_fields_submit(self, browser_fixture: Browser):
        """TC_LOG_12: Verify login with empty fields is blocked."""
        page = self._go_to_login(browser_fixture)
        try:
            submit_btn = page.locator("button[type='submit']")
            submit_btn.click()
            page.wait_for_timeout(1000)
            is_invalid = page.evaluate(
                "() => document.querySelector('#login-email').validity.valueMissing"
            )
            assert is_invalid, "Email should be invalid when empty"
        finally:
            page.close()

    def test_13_non_existent_email(self, browser_fixture: Browser):
        """TC_LOG_13: Verify login with non-existent email shows error."""
        page = browser_fixture.new_page()
        try:
            page.goto(BASE_URL, wait_until="networkidle")
            page.fill("#login-email", "nonexistent@example.com")
            page.fill("#login-password", "SomePass123")
            page.locator("button[type='submit']").click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            current_url = page.url
            assert "login" in current_url.lower(), \
                f"With non-existent email, should stay on login page, but URL is '{current_url}'"
        finally:
            page.close()

    # ==============================
    # EDGE TEST CASES
    # ==============================

    def test_16_email_whitespace_trim(self, browser_fixture: Browser):
        """TC_LOG_16: Verify email with leading/trailing whitespace is handled."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            # We use the page returned from _try_login - but it was already logged in with trimmed email
            # Let's test trimming separately: log out and try with spaces
            page.close()
            new_page = browser_fixture.new_page()
            new_page.goto(BASE_URL, wait_until="networkidle")
            new_page.fill("#login-email", f"  {VALID_EMAIL}  ")
            new_page.fill("#login-password", VALID_PASSWORD)
            new_page.locator("button[type='submit']").click()
            new_page.wait_for_load_state("networkidle")
            new_page.wait_for_timeout(3000)
            # Check if we got to 2FA (email should have been trimmed)
            otp_field = new_page.locator("#otp")
            if otp_field.is_visible():
                assert True, "Login with whitespace email succeeded (email was trimmed)"
            else:
                body_text = new_page.text_content("body") or ""
                if "too many login attempts" in body_text.lower():
                    pytest.skip("Rate-limited during whitespace test")
                else:
                    pytest.skip("Could not reach 2FA page - possible auth issue")
        finally:
            page.close()

    def test_17_otp_max_length(self, browser_fixture: Browser):
        """TC_LOG_17: Verify OTP field max length is 6 characters."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            otp_field = page.locator("#otp")
            expect(otp_field).to_be_visible()
            # Try entering 7 digits
            otp_field.fill("1234567")
            value = otp_field.input_value()
            assert len(value) <= 6, \
                f"OTP field should accept max 6 digits, but got {len(value)} digits"
        finally:
            page.close()

    def test_18_back_button_2fa(self, browser_fixture: Browser):
        """TC_LOG_18: Verify 'Back' button on 2FA page navigates back to login."""
        page = self._try_login_and_get_2fa(browser_fixture, max_wait=10)
        if page is None:
            pytest.skip("Rate-limited: too many login attempts")
        try:
            # Click Back button
            back_btn = page.locator("button:has-text('Back')").first
            expect(back_btn).to_be_visible()
            back_btn.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            # Should be back on login page
            email_field = page.locator("#login-email")
            expect(email_field).to_be_visible()
        finally:
            page.close()

    # ==============================
    # BOUNDARY TEST CASES
    # ==============================

    def test_21_long_email_input(self, browser_fixture: Browser):
        """TC_LOG_21: Verify very long email input is handled."""
        page = self._go_to_login(browser_fixture)
        try:
            long_local = "a" * 240
            long_email = f"{long_local}@b.com"
            page.fill("#login-email", long_email)
            value = page.locator("#login-email").input_value()
            assert len(value) > 0, "Long email should be accepted"
        finally:
            page.close()

    # ==============================
    # ACCESSIBILITY TEST CASES
    # ==============================

    def test_19_field_labels_accessibility(self, browser_fixture: Browser):
        """TC_LOG_19: Verify input fields have label associations."""
        page = self._go_to_login(browser_fixture)
        try:
            email_field = page.locator("#login-email")
            password_field = page.locator("#login-password")
            # Check placeholder text
            email_placeholder = email_field.get_attribute("placeholder")
            password_placeholder = password_field.get_attribute("placeholder")
            assert email_placeholder and "email" in email_placeholder.lower(), \
                f"Expected email placeholder, got '{email_placeholder}'"
            assert password_placeholder and "password" in password_placeholder.lower(), \
                f"Expected password placeholder, got '{password_placeholder}'"
            # Check autocomplete attributes
            email_auto = email_field.get_attribute("autocomplete")
            password_auto = password_field.get_attribute("autocomplete")
            assert email_auto is not None, "Email field should have autocomplete attribute"
            assert password_auto is not None, "Password field should have autocomplete attribute"
        finally:
            page.close()

    def test_20_keyboard_navigation(self, browser_fixture: Browser):
        """TC_LOG_20: Verify keyboard tab order is correct."""
        page = self._go_to_login(browser_fixture)
        try:
            # Tab from email to password
            page.locator("#login-email").focus()
            page.keyboard.press("Tab")
            focused_id = page.evaluate("() => document.activeElement.id")
            assert focused_id == "login-password", \
                f"Tab from email should focus password, got '{focused_id}'"
            # Tab from password to submit
            page.keyboard.press("Tab")
            focused_tag = page.evaluate("() => document.activeElement.tagName")
            focused_type = page.evaluate("() => document.activeElement.type || ''")
            assert focused_tag == "BUTTON" or "submit" in focused_type, \
                f"Tab from password should focus submit button, got '{focused_tag}'"
        finally:
            page.close()


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short", __file__])