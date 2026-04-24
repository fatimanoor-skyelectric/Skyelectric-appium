import time
import subprocess
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Maps digit character → Android keycode event number
DIGIT_KEYCODE = {
    '0': 7, '1': 8, '2': 9, '3': 10,
    '4': 11, '5': 12, '6': 13, '7': 14,
    '8': 15, '9': 16,
}


def adb_tap(x, y):
    """Tap screen using adb — avoids UiAutomator2 crash."""
    subprocess.run(['adb', 'shell', 'input', 'tap', str(x), str(y)])
    time.sleep(0.8)


def adb_type(text):
    """Type text using adb input (email only — not for OTP boxes)."""
    safe = text.replace('@', '\\@').replace('.', '\\.')
    subprocess.run(['adb', 'shell', 'input', 'text', safe])
    time.sleep(1)


def adb_key(keycode_int):
    """Send a single keyevent by numeric code."""
    subprocess.run(['adb', 'shell', 'input', 'keyevent', str(keycode_int)])
    time.sleep(0.35)  # give each OTP box time to register & shift focus


class LoginPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait   = WebDriverWait(driver, 25)

    # ── Locators ──────────────────────────────────────────────────
    EMAIL_FIELD      = (AppiumBy.CLASS_NAME, 'android.widget.EditText')
    LOGIN_BTN        = (AppiumBy.XPATH, '//android.widget.Button[@content-desc="Login"]')
    OTP_SCREEN_TITLE = (AppiumBy.XPATH, '//*[@content-desc="Enter OTP"]')
    OTP_EDIT_TEXT    = (AppiumBy.XPATH, '//android.widget.EditText')
    VERIFY_BTN       = (AppiumBy.XPATH, '//android.widget.Button[@content-desc="Verify"]')
    RESEND_OTP_BTN   = (AppiumBy.XPATH,
                        '//*[contains(@content-desc,"Resend") or contains(@content-desc,"resend")]')
    ERROR_MESSAGE    = (AppiumBy.XPATH,
                        '//*[contains(@content-desc,"Invalid") or contains(@content-desc,"invalid")'
                        ' or contains(@content-desc,"Wrong") or contains(@content-desc,"wrong")'
                        ' or contains(@content-desc,"Error") or contains(@content-desc,"expired")]')

    # ── Login Screen ──────────────────────────────────────────────
    def wait_for_login_screen(self):
        self.wait.until(EC.presence_of_element_located(self.EMAIL_FIELD))
        time.sleep(2)
        print("✅ Login screen loaded")

    def enter_email(self, email):
        # Email EditText bounds from XML: [46,1348][1034,1538] → center (540, 1443)
        adb_tap(540, 1443)
        time.sleep(1)
        subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_CTRL_A'])
        subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_DEL'])
        time.sleep(0.5)
        adb_type(email)
        print(f"📧 Email entered: {email}")

    def tap_login(self):
        """
        Dismiss keyboard, then click Login.
        Login button bounds from XML: [46,1584][1034,1745] → center (540, 1664)
        Falls back to Appium element click if coordinate tap misses.
        """
        # 1. Dismiss keyboard
        subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_BACK'])
        time.sleep(1)

        # 2. Try Appium element click first (most reliable)
        try:
            btn = self.wait.until(EC.element_to_be_clickable(self.LOGIN_BTN))
            btn.click()
            print("🖱️  Login button clicked via Appium element")
        except Exception:
            # 3. Fallback: coordinate tap
            print("⚠️  Appium click failed — falling back to adb tap (540, 1664)")
            adb_tap(540, 1664)

        time.sleep(4)
        print("📨 OTP request sent — waiting for OTP screen…")

    # ── OTP Screen ────────────────────────────────────────────────
    def wait_for_otp_screen(self):
        self.wait.until(EC.presence_of_element_located(self.OTP_SCREEN_TITLE))
        time.sleep(1.5)
        print("✅ OTP screen loaded")

    def enter_otp(self, otp):
        """
        The 6 visual OTP boxes share a single EditText:
          bounds="[42,709][1038,835]" → center (540, 772)

        Strategy:
          1. Tap to focus the field
          2. Clear with CTRL_A + DEL
          3. Re-tap so focus is restored after clear
          4. Send each digit as an individual KEYCODE (0–9)
             — this reliably triggers each box's focus-advance logic,
               unlike `input text` which can dump all chars at once
        """
        otp_str = str(otp).strip()
        print(f"🔢 Entering OTP digit-by-digit: {otp_str}")

        # Step 1: Focus
        adb_tap(540, 772)
        time.sleep(0.8)

        # Step 2: Clear
        subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_CTRL_A'])
        time.sleep(0.3)
        subprocess.run(['adb', 'shell', 'input', 'keyevent', 'KEYCODE_DEL'])
        time.sleep(0.5)

        # Step 3: Re-focus (clear often drops focus)
        adb_tap(540, 772)
        time.sleep(0.8)

        # Step 4: Send each digit as its own keyevent
        for i, digit in enumerate(otp_str):
            keycode = DIGIT_KEYCODE.get(digit)
            if keycode is None:
                print(f" Unexpected character '{digit}' in OTP — skipping")
                continue
            adb_key(keycode)
            print(f"   Box {i+1}: '{digit}' ✓")

        time.sleep(1)
        print(f"All {len(otp_str)} OTP digits entered")

    def tap_verify(self):
        """
        Verify button bounds: [42,1124][1038,1276] → center (540, 1200)
        Tries Appium element first, then falls back to coordinate tap.
        """
        try:
            btn = self.wait.until(EC.element_to_be_clickable(self.VERIFY_BTN))
            btn.click()
            print(" Verify clicked via Appium element")
        except Exception:
            print(" Appium click failed — adb tap (540, 1200)")
            adb_tap(540, 1200)
        time.sleep(3)

    def tap_resend_otp(self):
        btn = self.wait.until(EC.element_to_be_clickable(self.RESEND_OTP_BTN))
        btn.click()
        time.sleep(2)

    def is_error_displayed(self):
        try:
            time.sleep(2)
            el = self.driver.find_element(*self.ERROR_MESSAGE)
            return el.is_displayed()
        except Exception:
            return False

    def get_error_text(self):
        try:
            el = self.driver.find_element(*self.ERROR_MESSAGE)
            return el.get_attribute("content-desc")
        except Exception:
            return ""

    # ── Full Login Flow ───────────────────────────────────────────
    def login_with_otp(self, email, otp_fetcher_func):
        self.wait_for_login_screen()
        self.enter_email(email)

        # Record time BEFORE triggering OTP so gmail fetcher ignores older emails
        otp_requested_at = time.time()

        self.tap_login()
        self.wait_for_otp_screen()

        # Pass the timestamp so fetcher only picks up the NEW email
        otp = otp_fetcher_func(since_timestamp=otp_requested_at)

        assert otp, "Could not retrieve OTP from Gmail"
        print(f" OTP to enter: {otp}")

        self.enter_otp(otp)
        self.tap_verify()
        print("Login flow completed")