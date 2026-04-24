import pytest
import time
from pages.login_page import LoginPage
from pages.home_page  import HomePage
from utils.gmail_helper import get_otp_from_gmail

TEST_EMAIL = "fatimanoor@skyelectric.com"

APP_PACKAGE  = "com.skyelectric.smartapp"
APP_ACTIVITY = "com.skyelectric.smartapp.skyelectricpvt.MainActivity"

def restart_app(driver):
    driver.terminate_app(APP_PACKAGE)
    time.sleep(3)
    driver.activate_app(APP_PACKAGE)
    time.sleep(4)


class TestLogin:

    def test_login_screen_loads(self, driver):
        login = LoginPage(driver)
        login.wait_for_login_screen()
        assert driver.find_element(*LoginPage.EMAIL_FIELD).is_displayed()

    def test_successful_login_with_otp(self, driver):
        restart_app(driver)
        login = LoginPage(driver)
        home  = HomePage(driver)
        login.login_with_otp(
            email=TEST_EMAIL,
            # ✅ CHANGED: lambda now accepts and forwards since_timestamp
            otp_fetcher_func=lambda since_timestamp=None: get_otp_from_gmail(
                sender_filter='skyelectric',
                subject_filter='OTP',
                wait_seconds=90,
                since_timestamp=since_timestamp   # <-- passes the pre-login timestamp
            )
        )
        assert home.is_dashboard_loaded(), "Dashboard did not load after OTP login"

    def test_invalid_email_format(self, driver):
        restart_app(driver)
        login = LoginPage(driver)
        login.wait_for_login_screen()
        login.enter_email("notanemail")
        login.tap_send_otp()
        assert login.is_error_displayed(), "No error for invalid email format"

    def test_empty_email_field(self, driver):
        restart_app(driver)
        login = LoginPage(driver)
        login.wait_for_login_screen()
        login.tap_send_otp()
        assert login.is_error_displayed(), "No error for empty email"

    def test_wrong_otp(self, driver):
        restart_app(driver)
        login = LoginPage(driver)
        login.wait_for_login_screen()
        login.enter_email(TEST_EMAIL)
        login.tap_send_otp()
        login.wait_for_otp_screen()
        login.enter_otp("000000")
        login.tap_verify()
        assert login.is_error_displayed(), "No error for wrong OTP"

    def test_resend_otp(self, driver):
        restart_app(driver)
        login = LoginPage(driver)
        login.wait_for_login_screen()
        login.enter_email(TEST_EMAIL)
        login.tap_send_otp()
        login.wait_for_otp_screen()
        login.tap_resend_otp()
        login.wait_for_otp_screen()
        assert True