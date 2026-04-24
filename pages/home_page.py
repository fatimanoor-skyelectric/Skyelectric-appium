import time
import subprocess


def adb_dump_screen():
    subprocess.run(['adb', 'shell', 'uiautomator', 'dump', '/sdcard/ui.xml'],
                   capture_output=True)
    result = subprocess.run(['adb', 'shell', 'cat', '/sdcard/ui.xml'],
                            capture_output=True, text=True)
    return result.stdout


class HomePage:
    def __init__(self, driver):
        self.driver = driver

    def is_dashboard_loaded(self, timeout=30):
        """Check if main screen loaded by looking for known dashboard text."""
        print("⏳ Waiting for main screen...")
        dashboard_keywords = [
            "Dashboard", "Home", "Solar", "Battery",
            "Energy", "kWh", "Welcome", "Overview"
        ]
        for _ in range(timeout // 2):
            xml = adb_dump_screen()
            for keyword in dashboard_keywords:
                if keyword in xml:
                    print(f"✅ Dashboard loaded — found '{keyword}'")
                    return True
            time.sleep(2)
        print("Main console screen not found")
        return False
