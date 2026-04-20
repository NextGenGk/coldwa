"""
WhatsApp Sender - Local Desktop Version
This module handles WhatsApp Web automation using Selenium.
IMPORTANT: This only works on local machines, NOT on cloud servers.
"""

import os
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from utils import format_phone_number, substitute_template

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")


_MSG_SELECTORS = [
    'div[contenteditable="true"][data-tab="10"]',
    'div[contenteditable="true"][role="textbox"]',
    'footer div[contenteditable="true"]',
    'div[title="Type a message"]',
    'div[data-testid="conversation-compose-box-input"]',
]

# Present only when fully logged in
_LOGGED_IN_SELECTOR = (
    '[data-testid="chat-list"], '
    '[data-testid="default-user"], '
    'div[aria-label="Chat list"], '
    '[data-testid="search"], '
    '[data-testid="intro-text"], '
    '[data-icon="chat"],'
    '#side'
)

_QR_SELECTOR = (
    'div[data-ref], '
    'canvas[aria-label="Scan me!"], '
    'div[data-testid="qrcode"], '
    'canvas'
)


def _clear_chrome_locks(profile_dir):
    """Remove stale Chrome lock files to prevent 'already in use' errors."""
    for subdir in [profile_dir, os.path.join(profile_dir, "Default")]:
        for lock in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            path = os.path.join(subdir, lock)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


def _build_driver() -> webdriver.Chrome:
    """
    Build and configure Chrome WebDriver for local WhatsApp Web automation.
    Uses a persistent profile to maintain WhatsApp login session.
    """
    options = Options()
    
    # Clear any stale locks from previous sessions
    _clear_chrome_locks(PROFILE_DIR)
    
    # Use persistent profile to keep WhatsApp logged in
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    
    # Stability options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Hide automation indicators
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Keep browser open and visible (required for WhatsApp Web)
    options.add_argument("--start-maximized")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
    except Exception as e:
        err = str(e)
        if "user data directory is already in use" in err.lower():
            raise RuntimeError(
                "WhatsApp Chrome window is already open. "
                "Close any Chrome windows opened by this app and try again."
            ) from e
        raise RuntimeError(f"Failed to start Chrome: {err}") from e

    return driver


def _wait_for_login(driver: webdriver.Chrome, timeout: int = 180, qr_callback=None, status_cb=None):
    """
    Wait until WhatsApp Web is fully logged in.
    The user should scan the QR code displayed in the Chrome window.
    """
    screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wa_qr.png")

    deadline = time.time() + timeout
    qr_shown = False

    while time.time() < deadline:
        try:
            # Check if already logged in
            if driver.find_elements(By.CSS_SELECTOR, _LOGGED_IN_SELECTOR):
                print("DEBUG: Successfully detected login!")
                return

            # Capture whatever is on the screen to ensure the user sees the QR code
            # even if our selectors fail to find the specific element.
            try:
                driver.save_screenshot(screenshot_path)
                if qr_callback:
                    qr_callback(screenshot_path)
                
                if not qr_shown:
                    print("DEBUG: Waiting for QR code scan. Check the Chrome window.")
                    if status_cb:
                        status_cb("📱 Scan the QR code in the Chrome window with your WhatsApp app")
                    qr_shown = True
            except Exception as e:
                print(f"DEBUG: Failed to capture fallback screenshot: {e}")

            # Check for common retry/error buttons
            for retry_sel in ['div[role="button"]', 'button']:
                try:
                    btns = driver.find_elements(By.CSS_SELECTOR, retry_sel)
                    for b in btns:
                        if "retry" in b.text.lower() or "click to reload" in b.text.lower():
                            print("DEBUG: Found a 'Retry' button. You might need to refresh the page.")
                except Exception:
                    pass

            time.sleep(5)

        except Exception as e:
            err_lower = str(e).lower()
            if any(k in err_lower for k in ("invalid session", "no such session", "session not created")):
                raise RuntimeError(
                    "Chrome session ended unexpectedly. "
                    "Please close any other Chrome windows and try again."
                ) from e
            # Other transient errors — keep waiting
            time.sleep(2)

    raise RuntimeError(
        f"WhatsApp login timed out after {timeout}s. "
        "Make sure you scanned the QR code in time."
    )


def _find_message_box(driver: webdriver.Chrome, timeout: int):
    wait = WebDriverWait(driver, timeout)
    for selector in _MSG_SELECTORS:
        try:
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        except Exception:
            continue
    raise RuntimeError("Message input box not found — WhatsApp Web may have changed its layout.")


class WhatsAppSender:
    def __init__(self, wait_time: int = 30, inter_message_delay: int = 5,
                 default_cc: str = "91", qr_timeout: int = 180):
        self.wait_time           = wait_time
        self.inter_message_delay = inter_message_delay
        self.default_cc          = default_cc
        self.qr_timeout          = qr_timeout
        self.driver              = None

    def _open_driver(self, status_cb=None, qr_callback=None):
        if self.driver is None:
            if status_cb:
                status_cb("🌐 Opening WhatsApp Web…")
            self.driver = _build_driver()
            self.driver.get("https://web.whatsapp.com")
            time.sleep(5)  # Let the page initialise

            # Quick check if already logged in
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, _LOGGED_IN_SELECTOR))
                )
                if status_cb:
                    status_cb("✅ Already logged in — starting to send…")
            except Exception:
                if status_cb:
                    status_cb("📷 Loading QR code — please wait…")
                _wait_for_login(
                    self.driver,
                    timeout=self.qr_timeout,
                    qr_callback=qr_callback,
                    status_cb=status_cb,
                )
                if status_cb:
                    status_cb("✅ QR scanned! Starting to send messages…")

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
