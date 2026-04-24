import pytest
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
import os

APK_PATH = os.path.join(os.path.dirname(__file__), "app-skyelectric-production.apk")

APP_PACKAGE  = "com.skyelectric.smartapp"
APP_ACTIVITY = "com.skyelectric.smartapp.skyelectricpvt.MainActivity"

@pytest.fixture(scope="session")
def driver():
    options = UiAutomator2Options()
    options.platform_name          = "Android"
    options.device_name            = "emulator-5554"
    options.app                    = APK_PATH
    options.app_package            = APP_PACKAGE
    options.app_activity           = APP_ACTIVITY
    options.no_reset               = False
    options.auto_grant_permissions = True
    options.new_command_timeout    = 300

    driver = webdriver.Remote(
        command_executor="http://127.0.0.1:4723",
        options=options
    )
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


def restart_app(driver):
    """Restart app using start_activity — works for Flutter apps."""
    driver.start_activity(APP_PACKAGE, APP_ACTIVITY)
    time.sleep(4)