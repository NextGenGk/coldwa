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
]

# Present only when fully logged in
_LOGGED_IN_SELECTOR = '[data-testid="chat-list"], [data-testid="default-user"], div[aria-label="Chat list"]'


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=Options() if False else options,
    )
    driver.maximize_window()
    return driver


def _wait_for_login(driver: webdriver.Chrome, timeout: int = 90):
    """Block until WhatsApp Web shows the chat list (QR scanned)."""
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, _LOGGED_IN_SELECTOR))
    )


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

    def _open_driver(self, status_cb=None):
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
                    status_cb("Scan the QR code in the Chrome window to continue…")
                _wait_for_login(self.driver, self.qr_timeout)
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

    def send_batch(self, df, template: str, progress_callback=None, status_cb=None) -> list:
        self._open_driver(status_cb=status_cb)
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
