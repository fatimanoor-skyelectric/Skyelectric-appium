import pytest
from pages.login_page import LoginPage
from pages.home_page  import HomePage
import os

VALID_EMAIL    = "testuser@skyelectric.com"
VALID_PASSWORD = "YourPassword123"

class TestNavigation:

    def test_dashboard_loads(self, driver):
        home = HomePage(driver)
        assert home.is_dashboard_loaded(), "Dashboard did not load"

    def test_energy_reading_displayed(self, driver):
        home = HomePage(driver)
        reading = home.get_energy_reading()
        assert reading, "Energy reading is empty"

    def test_take_screenshot(self, driver):
        path = "/tmp/skyelectric_dashboard.png"
        driver.save_screenshot(path)
        assert os.path.exists(path), "Screenshot was not saved"
