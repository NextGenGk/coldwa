import os
import time
import urllib.parse
import platform

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from utils import format_phone_number, substitute_template

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

# Detect if running on Streamlit Cloud
def _is_streamlit_cloud():
    return os.path.exists('/mount/src') or platform.system() == 'Linux' and 'STREAMLIT' in os.environ.get('HOME', '')

_MSG_SELECTORS = [
    'div[contenteditable="true"][data-tab="10"]',
    'div[contenteditable="true"][role="textbox"]',
    'footer div[contenteditable="true"]',
    'div[title="Type a message"]',
    'div[data-testid="conversation-compose-box-input"]',
    'div[data-testid="conversation-text-input"]',
]

# Present only when fully logged in
_LOGGED_IN_SELECTOR = (
    '[data-testid="chat-list"], '
    '[data-testid="default-user"], '
    'div[aria-label="Chat list"], '
    '[data-testid="search"], '
    '[data-testid="intro-text"], '
    '[data-icon="chat"]'
)

def _clear_chrome_locks(profile_dir):
    """Try to remove Chrome lock files if they exist."""
    for lock in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
        lock_path = os.path.join(profile_dir, lock)
        if os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except Exception:
                pass
    # Also check Default/ subdirectory
    default_dir = os.path.join(profile_dir, "Default")
    if os.path.exists(default_dir):
        for lock in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_path = os.path.join(default_dir, lock)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except Exception:
                    pass


def _build_driver() -> webdriver.Chrome:
    options = Options()
    
    # Detect environment
    is_cloud = _is_streamlit_cloud()
    
    if is_cloud:
        # Streamlit Cloud configuration
        import shutil
        # Try to find chromium binary automatically
        chrome_path = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
        if chrome_path:
            options.binary_location = chrome_path
        
        options.add_argument('--headless') # Try standard headless if 'new' fails
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Use temp directory for profile on cloud
        temp_profile = "/tmp/chrome_profile"
        os.makedirs(temp_profile, exist_ok=True)
        # options.add_argument(f"--user-data-dir={temp_profile}") # Temporarily disable to test
    else:
        # Local configuration
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if not is_cloud:
        _clear_chrome_locks(PROFILE_DIR)

    if is_cloud:
        try:
            # Try finding chromedriver in PATH via shutil.which
            chromedriver_path = shutil.which('chromedriver')
            if chromedriver_path:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Fallback to absolute path or just default
                driver = webdriver.Chrome(options=options)
        except Exception as e:
            raise RuntimeError(f"Failed to start Chrome on Cloud: {e}. Binary: {options.binary_location}, Driver: {shutil.which('chromedriver') or 'Not in PATH'}")
    else:
        # Use ChromeDriverManager locally
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options,
            )
        except Exception as e:
            if "user data directory is already in use" in str(e).lower():
                raise RuntimeError(
                    "WhatsApp Chrome window is already open. Please close any other "
                    "Chrome windows opened by this app and try again."
                ) from e
            raise e
    
    if not is_cloud:
        driver.maximize_window()
    
    return driver


def _wait_for_login(driver: webdriver.Chrome, timeout: int = 90, qr_callback=None):
    """Block until WhatsApp Web shows the chat list (QR scanned)."""
    # Try to capture QR code for display
    if qr_callback:
        try:
            # Short wait to see if we're already logged in or need to show QR
            for _ in range(10):  # 5 seconds polling
                if driver.find_elements(By.CSS_SELECTOR, _LOGGED_IN_SELECTOR):
                    return
                # Check for QR code
                qr_elements = driver.find_elements(By.CSS_SELECTOR, 'canvas[aria-label="Scan me!"], div[data-ref]')
                if qr_elements:
                    # Take screenshot and pass to callback
                    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_qr.png")
                    if _is_streamlit_cloud():
                        screenshot_path = "/tmp/whatsapp_qr.png"
                    
                    driver.save_screenshot(screenshot_path)
                    qr_callback(screenshot_path)
                    break
                time.sleep(0.5)
        except Exception as e:
            print(f"DEBUG: QR capture info: {e}")
    
    # Wait for the logged-in state
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _LOGGED_IN_SELECTOR))
        )
    except Exception as e:
        # One last check for any logged-in element before failing
        if not driver.find_elements(By.CSS_SELECTOR, _LOGGED_IN_SELECTOR):
            raise e


def _find_message_box(driver: webdriver.Chrome, timeout: int):
    wait = WebDriverWait(driver, timeout)
    for selector in _MSG_SELECTORS:
        try:
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        except Exception:
            continue
    raise RuntimeError("Message input box not found.")


class WhatsAppSender:
    def __init__(self, wait_time: int = 30, inter_message_delay: int = 5,
                 default_cc: str = "91", qr_timeout: int = 90):
        self.wait_time           = wait_time
        self.inter_message_delay = inter_message_delay
        self.default_cc          = default_cc
        self.qr_timeout          = qr_timeout
        self.driver              = None

    def _open_driver(self, status_cb=None, qr_callback=None):
        if self.driver is None:
            if status_cb:
                status_cb("Opening WhatsApp Web…")
            self.driver = _build_driver()
            self.driver.get("https://web.whatsapp.com")

            # Check if already logged in
            try:
                WebDriverWait(self.driver, 6).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, _LOGGED_IN_SELECTOR))
                )
                if status_cb:
                    status_cb("Already logged in — starting to send…")
            except Exception:
                if status_cb:
                    status_cb("Scan the QR code to continue…")
                _wait_for_login(self.driver, self.qr_timeout, qr_callback=qr_callback)
                if status_cb:
                    status_cb("QR scanned! Starting to send messages…")

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def send_single(self, phone: str, message: str, contact_name: str = "") -> dict:
        try:
            formatted   = format_phone_number(phone, self.default_cc)
            encoded_msg = urllib.parse.quote(message)
            url = f"https://web.whatsapp.com/send?phone={formatted}&text={encoded_msg}"

            self.driver.get(url)
            msg_box = _find_message_box(self.driver, self.wait_time)
            msg_box.click()
            time.sleep(0.5)
            msg_box.send_keys(Keys.ENTER)
            time.sleep(2)

            return {"contact": contact_name, "number": formatted, "status": "sent", "error": ""}
        except ValueError as exc:
            return {"contact": contact_name, "number": str(phone), "status": "failed",
                    "error": f"Invalid number — {exc}"}
        except Exception as exc:
            return {"contact": contact_name, "number": str(phone), "status": "failed", "error": str(exc)}

    def send_batch(self, df, template: str, progress_callback=None, status_cb=None, qr_callback=None) -> list:
        self._open_driver(status_cb=status_cb, qr_callback=qr_callback)
        results = []
        total   = len(df)
        try:
            for i, (_, row) in enumerate(df.iterrows()):
                message = substitute_template(template, row.to_dict())
                result  = self.send_single(
                    phone=row["mobile"],
                    message=message,
                    contact_name=str(row.get("name", "")),
                )
                results.append(result)
                if progress_callback:
                    progress_callback(i + 1, total, result)
                if i < total - 1:
                    time.sleep(self.inter_message_delay)
        finally:
            self.close()
        return results
