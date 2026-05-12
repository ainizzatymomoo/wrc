"""
Browser Automation Module
=========================
Uses Selenium WebDriver to automate form filling on the BLESS2 website.
Handles login, navigation, and intelligent field filling with retry logic.
"""

import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from loguru import logger

from .field_mapper import FormField, FormSection


@dataclass
class BrowserConfig:
    """Browser automation configuration."""
    base_url: str = "https://bless2.bless.gov.my/bless2/private"
    headless: bool = False
    timeout: int = 30
    implicit_wait: int = 10
    page_load_timeout: int = 60
    screenshot_on_error: bool = True
    screenshot_dir: str = "./screenshots"
    retry_attempts: int = 3
    retry_delay: float = 1.0
    slow_mode: bool = False  # Add delay between actions for stability
    slow_mode_delay: float = 0.5


class BLESS2AutoFill:
    """
    Automated form filler for the BLESS2 website.
    
    Handles:
    - Login authentication
    - Multi-page form navigation
    - Intelligent element detection (multiple selector strategies)
    - Dropdown/select field handling
    - Date picker handling
    - File upload handling
    - Error recovery and retry logic
    - Screenshot capture for debugging
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize the browser automation.
        
        Args:
            config: Browser configuration settings
        """
        self.config = config or BrowserConfig()
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self._filled_fields: List[Dict] = []
        self._errors: List[Dict] = []
        
        # Ensure screenshot directory exists
        os.makedirs(self.config.screenshot_dir, exist_ok=True)
        
        logger.info("BLESS2 AutoFill initialized with base URL: {}", self.config.base_url)

    def start_browser(self):
        """Start the Chrome WebDriver."""
        try:
            chrome_options = Options()
            
            if self.config.headless:
                chrome_options.add_argument("--headless=new")
                
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-popup-blocking")
            
            # Prevent detection as automation
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Detect Chrome/Chromium binary - use Playwright's if system not available
            import shutil
            system_chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
            if system_chrome:
                chrome_options.binary_location = system_chrome
            else:
                # Fallback to Playwright's Chromium
                pw_cache = Path.home() / ".cache/ms-playwright"
                if pw_cache.exists():
                    chrome_bins = sorted(pw_cache.glob("chromium-*/chrome-linux*/chrome"), reverse=True)
                    if chrome_bins:
                        chrome_options.binary_location = str(chrome_bins[0])
                        logger.info("Using Playwright Chromium: {}", chrome_options.binary_location)
            
            # Try using webdriver-manager for automatic driver management
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                # Fallback to system chromedriver
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.implicitly_wait(self.config.implicit_wait)
            self.driver.set_page_load_timeout(self.config.page_load_timeout)
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            
            # Remove webdriver flag
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error("Failed to start browser: {}", str(e))
            raise

    def login(self, username: str, password: str) -> bool:
        """
        Login to the BLESS2 system using requests (bypass Selenium navigation issues).
        POST credentials, get cookies, set them in Selenium, then navigate to private area.
        
        Args:
            username: BLESS2 username/ID
            password: BLESS2 password
            
        Returns:
            True if login successful
        """
        try:
            login_url = self.config.base_url.replace("/private", "/login")
            private_url = self.config.base_url  # /private
            
            # Step 1: Use requests to POST login credentials
            import requests as req
            
            # Get CSRF token and cookies first by visiting login page
            session = req.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            
            resp = session.get(login_url, timeout=30)
            logger.info("GET login page: {} {}", resp.status_code, len(resp.text))
            
            # Extract CSRF token if present
            import re
            csrf_match = re.search(r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)', resp.text)
            csrf_token = csrf_match.group(1) if csrf_match else ""
            if csrf_token:
                logger.info("CSRF token found: {}..", csrf_token[:10])
            
            # POST login credentials
            login_data = {
                "username": username,
                "password": password,
            }
            if csrf_token:
                login_data["_csrf"] = csrf_token
                login_data["_token"] = csrf_token
            
            # Try different common form field names
            post_resp = session.post(login_url, data=login_data, 
                                    allow_redirects=True, timeout=30)
            
            logger.info("POST login: {} -> {}", post_resp.status_code, post_resp.url)
            
            # Check if login was successful (redirected to private/dashboard area)
            if "/private" in post_resp.url or "dashboard" in post_resp.url.lower():
                logger.info("Login successful via REST API! ({} cookies)", len(session.cookies))
                
                # Log cookies for debugging
                for c in session.cookies:
                    logger.debug("Cookie: {}={} domain={} path={}", c.name, c.value[:20], c.domain, c.path)
                
                # Step 2: Navigate Selenium to BLESS2 domain (needed before setting cookies)
                self.driver.get("https://bless2.bless.gov.my/bless2/")
                time.sleep(2)
                
                # Step 3: Check if already logged in by cookie inheritance
                current_url = self.driver.execute_script("return window.location.href;")
                if "/private" in current_url:
                    logger.info("Already logged in via domain navigation!")
                    return True
                
                # Step 4: Set cookies via CDP if available, otherwise via add_cookie
                cookies_set = 0
                for cookie in session.cookies:
                    domain = cookie.domain or "bless2.bless.gov.my"
                    # Ensure domain starts with a dot or is the exact domain
                    if not domain.startswith('.'):
                        domain = domain
                    
                    cookie_dict = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': domain,
                        'path': cookie.path or '/',
                        'secure': cookie.secure if hasattr(cookie, 'secure') else True,
                        'httpOnly': cookie.has_nonstandard_attr('httponly'),
                    }
                    
                    try:
                        # Try CDP method first (doesn't require exact domain match)
                        self.driver.execute_cdp_cmd('Network.setCookie', cookie_dict)
                        cookies_set += 1
                    except Exception:
                        try:
                            # Fallback to standard add_cookie
                            self.driver.add_cookie(cookie_dict)
                            cookies_set += 1
                        except Exception as e2:
                            logger.debug("Could not set cookie {}: {}", cookie.name, str(e2)[:30])
                
                logger.info("Cookies set via CDP/addCookie: {}/{}", cookies_set, len(session.cookies))
                
                # Step 5: Navigate to private area - restore page load timeout
                self.driver.set_page_load_timeout(self.config.page_load_timeout)
                self.driver.get(private_url)
                time.sleep(3)
                
                # Verify
                current_url = self.driver.execute_script("return window.location.href;")
                if "/private" in current_url or "dashboard" in current_url.lower():
                    logger.info("Login verified! URL: {}", current_url)
                    return True
                else:
                    logger.warning("Cookie login redirected to: {}", current_url)
                    self.driver.set_page_load_timeout(self.config.page_load_timeout)
                    self.driver.get(private_url)
                    time.sleep(3)
                    current_url = self.driver.execute_script("return window.location.href;")
                    if "/private" in current_url:
                        return True
            
            # Step 5: Fallback - try navigate + inject cookies
            logger.info("REST login redirected, trying Selenium cookie fallback...")
            
            # Load private URL (might redirect to login page)
            self.driver.get(private_url)
            time.sleep(3)
            
            # Inject cookies and retry
            for cookie in session.cookies:
                try:
                    self.driver.add_cookie({
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain or 'bless2.bless.gov.my',
                        'path': cookie.path or '/',
                    })
                except Exception:
                    pass
            
            self.driver.get(private_url)
            time.sleep(3)
            
            current_url = self.driver.execute_script("return window.location.href;")
            logger.info("Fallback URL: {}", current_url)
            
            if "/private" in current_url or "dashboard" in current_url.lower():
                logger.info("Login verified via fallback!")
                return True
                
            logger.warning("All login methods failed")
            self._take_screenshot("login_failed")
            return False
                
        except Exception as e:
            logger.error("Login failed: {}", str(e))
            self._take_screenshot("login_exception")
            return False

    def fill_form(self, sections: List[FormSection], auto_submit: bool = False) -> Dict[str, Any]:
        """
        Fill the BLESS2 form with mapped data.
        
        Args:
            sections: List of FormSection with field values
            auto_submit: Whether to automatically submit after filling
            
        Returns:
            Dictionary with results summary
        """
        results = {
            "total_fields": 0,
            "filled_successfully": 0,
            "failed_fields": [],
            "skipped_fields": [],
            "sections_completed": [],
        }
        
        for section in sections:
            logger.info("Processing section: {}", section.name)
            
            # Navigate to section URL if specified
            if section.url_path:
                try:
                    full_url = self.config.base_url + section.url_path
                    self.driver.get(full_url)
                    time.sleep(2)
                except Exception as e:
                    logger.warning("Could not navigate to section URL: {}", str(e))
            
            section_success = True
            
            for field in section.fields:
                results["total_fields"] += 1
                
                if not field.value:
                    results["skipped_fields"].append({
                        "field": field.field_name,
                        "reason": "No value to fill"
                    })
                    continue
                
                success = self._fill_field(field)
                
                if success:
                    results["filled_successfully"] += 1
                    self._filled_fields.append({
                        "field_id": field.field_id,
                        "field_name": field.field_name,
                        "value": field.value,
                    })
                else:
                    section_success = False
                    results["failed_fields"].append({
                        "field": field.field_name,
                        "field_id": field.field_id,
                        "value": field.value,
                        "selector": field.selector,
                    })
                    
                if self.config.slow_mode:
                    time.sleep(self.config.slow_mode_delay)
            
            if section_success:
                results["sections_completed"].append(section.name)
        
        # Auto-submit if requested
        if auto_submit:
            self._submit_form()
            
        logger.info(
            "Form filling complete. {}/{} fields filled successfully",
            results["filled_successfully"],
            results["total_fields"]
        )
        
        return results

    def _fill_field(self, field: FormField) -> bool:
        """
        Fill a single form field with intelligent handling based on field type.
        
        Args:
            field: FormField to fill
            
        Returns:
            True if field was filled successfully
        """
        for attempt in range(self.config.retry_attempts):
            try:
                if field.field_type == "text" or field.field_type == "textarea":
                    return self._fill_text_field(field)
                elif field.field_type == "select":
                    return self._fill_select_field(field)
                elif field.field_type == "radio":
                    return self._fill_radio_field(field)
                elif field.field_type == "checkbox":
                    return self._fill_checkbox_field(field)
                elif field.field_type == "date":
                    return self._fill_date_field(field)
                else:
                    return self._fill_text_field(field)
                    
            except StaleElementReferenceException:
                logger.warning("Stale element for {}, retrying ({}/{})", 
                             field.field_name, attempt + 1, self.config.retry_attempts)
                time.sleep(self.config.retry_delay)
            except Exception as e:
                logger.warning("Error filling {} (attempt {}/{}): {}", 
                             field.field_name, attempt + 1, self.config.retry_attempts, str(e))
                time.sleep(self.config.retry_delay)
        
        logger.error("Failed to fill field after {} attempts: {}", 
                    self.config.retry_attempts, field.field_name)
        return False

    def _fill_text_field(self, field: FormField) -> bool:
        """Fill a text input or textarea field."""
        element = self._find_element_by_selectors(field.selector.split(", "))
        
        if not element:
            logger.warning("Text field not found: {}", field.field_name)
            return False
        
        # Scroll element into view
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        
        # Clear existing value
        element.clear()
        
        # For some fields, clear() doesn't work properly
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.DELETE)
        
        # Type the value
        element.send_keys(field.value)
        
        logger.debug("Filled text field '{}' with '{}'", field.field_name, field.value[:30])
        return True

    def _fill_select_field(self, field: FormField) -> bool:
        """Fill a dropdown/select field."""
        element = self._find_element_by_selectors(field.selector.split(", "))
        
        if not element:
            logger.warning("Select field not found: {}", field.field_name)
            return False
        
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        
        try:
            select = Select(element)
            
            # Try selecting by value first
            try:
                select.select_by_value(field.value)
                logger.debug("Selected by value '{}' in '{}'", field.value, field.field_name)
                return True
            except NoSuchElementException:
                pass
            
            # Try selecting by visible text
            try:
                select.select_by_visible_text(field.value)
                logger.debug("Selected by text '{}' in '{}'", field.value, field.field_name)
                return True
            except NoSuchElementException:
                pass
            
            # Try partial text match
            for option in select.options:
                if field.value.upper() in option.text.upper():
                    select.select_by_visible_text(option.text)
                    logger.debug("Selected by partial match '{}' in '{}'", option.text, field.field_name)
                    return True
                    
            logger.warning("No matching option found for '{}' in '{}'", field.value, field.field_name)
            return False
            
        except Exception as e:
            # Some dropdowns are custom (not standard <select>)
            # Try clicking and selecting from custom dropdown
            return self._handle_custom_dropdown(element, field)

    def _fill_radio_field(self, field: FormField) -> bool:
        """Fill a radio button field."""
        # Try to find the specific radio button by value
        selectors = [
            f"input[name='{field.field_id}'][value='{field.value}']",
            f"input[name='{field.field_id}'][value='{field.value.lower()}']",
            f"input[type='radio'][value='{field.value}']",
            f"label:contains('{field.value}') input[type='radio']",
        ]
        
        element = self._find_element_by_selectors(selectors)
        
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
            element.click()
            logger.debug("Selected radio '{}' for '{}'", field.value, field.field_name)
            return True
        
        # Try finding by label text
        try:
            labels = self.driver.find_elements(By.XPATH, 
                f"//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{field.value.lower()}')]")
            for label in labels:
                label.click()
                logger.debug("Clicked label for radio '{}'", field.field_name)
                return True
        except Exception:
            pass
            
        logger.warning("Radio field not found: {}", field.field_name)
        return False

    def _fill_checkbox_field(self, field: FormField) -> bool:
        """Fill a checkbox field."""
        element = self._find_element_by_selectors(field.selector.split(", "))
        
        if not element:
            return False
            
        is_checked = element.is_selected()
        should_check = field.value.lower() in ("true", "1", "yes", "checked")
        
        if is_checked != should_check:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.click()
            
        return True

    def _fill_date_field(self, field: FormField) -> bool:
        """Fill a date field (handles both native date inputs and date pickers)."""
        element = self._find_element_by_selectors(field.selector.split(", "))
        
        if not element:
            logger.warning("Date field not found: {}", field.field_name)
            return False
        
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        
        # Check if it's a native date input
        input_type = element.get_attribute("type")
        
        if input_type == "date":
            # Native date input expects YYYY-MM-DD format
            date_value = self._convert_to_iso_date(field.value)
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; "
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                element, date_value
            )
        else:
            # Regular text input - just type the date
            element.clear()
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            element.send_keys(field.value)
        
        logger.debug("Filled date field '{}' with '{}'", field.field_name, field.value)
        return True

    def _handle_custom_dropdown(self, element, field: FormField) -> bool:
        """Handle custom (non-standard) dropdown components."""
        try:
            # Click to open dropdown
            element.click()
            time.sleep(0.5)
            
            # Look for dropdown options
            option_selectors = [
                f"li[data-value='{field.value}']",
                f"div[data-value='{field.value}']",
                f"//li[contains(text(), '{field.value}')]",
                f"//div[contains(@class, 'option')][contains(text(), '{field.value}')]",
                f"//span[contains(text(), '{field.value}')]",
            ]
            
            for selector in option_selectors:
                try:
                    if selector.startswith("//"):
                        option = self.driver.find_element(By.XPATH, selector)
                    else:
                        option = self.driver.find_element(By.CSS_SELECTOR, selector)
                    option.click()
                    return True
                except NoSuchElementException:
                    continue
                    
            return False
        except Exception as e:
            logger.warning("Custom dropdown handling failed: {}", str(e))
            return False

    def _find_element_by_selectors(self, selectors: List[str]):
        """
        Try multiple CSS selectors to find an element.
        Returns the first matching element or None.
        """
        for selector in selectors:
            selector = selector.strip()
            if not selector:
                continue
            try:
                if selector.startswith("//"):
                    element = self.driver.find_element(By.XPATH, selector)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    return element
            except (NoSuchElementException, Exception):
                continue
        return None

    def _convert_to_iso_date(self, date_str: str) -> str:
        """Convert date string to ISO format (YYYY-MM-DD)."""
        import re
        
        # Already ISO format
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
            
        # DD/MM/YYYY format
        match = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if match:
            return f"{match.group(3)}-{match.group(2).zfill(2)}-{match.group(1).zfill(2)}"
            
        return date_str

    def _submit_form(self):
        """Submit the current form."""
        try:
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[id*='submit']",
                "button[id*='save']",
                "button:contains('Submit')",
                "button:contains('Hantar')",
            ]
            
            submit_btn = self._find_element_by_selectors(submit_selectors)
            if submit_btn:
                submit_btn.click()
                time.sleep(3)
                logger.info("Form submitted")
            else:
                logger.warning("Submit button not found")
                
        except Exception as e:
            logger.error("Form submission failed: {}", str(e))

    def _take_screenshot(self, name: str):
        """Take a screenshot for debugging."""
        if self.config.screenshot_on_error and self.driver:
            try:
                filepath = os.path.join(self.config.screenshot_dir, f"{name}_{int(time.time())}.png")
                self.driver.save_screenshot(filepath)
                logger.info("Screenshot saved: {}", filepath)
            except Exception as e:
                logger.warning("Could not take screenshot: {}", str(e))

    def navigate_to_application(self, application_type: str = "new"):
        """Navigate to form: use known direct URL for new application if possible."""
        try:
            logger.info("Navigating BLESS2 flow to application form...")
            
            # Try direct URL to the BLESS2 application form
            direct_form_url = "https://bless2.bless.gov.my/bless2/private/application/new"
            try:
                self.driver.get(direct_form_url)
                time.sleep(3)
                current_url = self.driver.execute_script("return window.location.href;")
                if "application" in current_url.lower() or "form" in current_url.lower():
                    logger.info("Navigated directly to application form: {}", current_url)
                    return
            except Exception:
                pass
            
            # Fallback: My Tray flow
            self._navigate_to_my_tray()
            
            form_opened = self._open_form_from_tray()
            if not form_opened:
                logger.info("No pending application in tray. Starting new application flow...")
                self._add_new_license(application_type)
            
            logger.info("Successfully navigated to application form")
            
        except Exception as e:
            logger.error("Navigation failed: {}", str(e))
            self._take_screenshot("navigation_error")

    def _navigate_to_my_tray(self):
        """
        Navigate to My License → My Tray.
        This is where pending/incomplete applications are listed.
        """
        try:
            # Try direct URL first
            tray_url = self.config.base_url.rstrip('/') + "/myLicense/myTray"
            self.driver.get(tray_url)
            time.sleep(2)
            
            # Verify we're on My Tray page
            if "myTray" in self.driver.current_url or "my-tray" in self.driver.current_url:
                logger.info("Navigated to My Tray via direct URL")
                return
            
            # Fallback: Navigate via menu clicks
            logger.info("Trying menu navigation to My Tray...")
            
            # Click "My License" menu
            my_license_selectors = [
                "//a[contains(text(), 'My License')]",
                "//span[contains(text(), 'My License')]",
                "//li[contains(@class, 'menu')]//a[contains(text(), 'License')]",
                "a[href*='myLicense']",
            ]
            
            menu_clicked = False
            for selector in my_license_selectors:
                try:
                    if selector.startswith("//"):
                        el = self.driver.find_element(By.XPATH, selector)
                    else:
                        el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    el.click()
                    time.sleep(1)
                    menu_clicked = True
                    break
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            if menu_clicked:
                # Click "My Tray" submenu
                tray_selectors = [
                    "//a[contains(text(), 'My Tray')]",
                    "//span[contains(text(), 'My Tray')]",
                    "a[href*='myTray']",
                    "a[href*='my-tray']",
                ]
                
                for selector in tray_selectors:
                    try:
                        if selector.startswith("//"):
                            el = self.driver.find_element(By.XPATH, selector)
                        else:
                            el = self.driver.find_element(By.CSS_SELECTOR, selector)
                        el.click()
                        time.sleep(2)
                        logger.info("Navigated to My Tray via menu")
                        return
                    except (NoSuchElementException, ElementNotInteractableException):
                        continue
            
            logger.warning("Could not navigate to My Tray via menu")
            
        except Exception as e:
            logger.error("Error navigating to My Tray: {}", str(e))

    def _open_form_from_tray(self) -> bool:
        """
        Open an existing application form from My Tray.
        Looks for the edit icon (pencil icon) to open the form.
        
        Returns:
            True if a form was successfully opened
        """
        try:
            time.sleep(1)
            
            # Look for edit icon in the tray list
            edit_selectors = [
                "i.fa-edit",
                "i.fa-pencil",
                "a[title='Edit']",
                "a[title='Kemaskini']",
                ".edit-icon",
                "i.glyphicon-edit",
                "//a[contains(@title, 'Edit')]",
                "//i[contains(@class, 'edit')]",
                "//i[contains(@class, 'pencil')]",
                "//td//a[contains(@href, 'edit')]",
            ]
            
            for selector in edit_selectors:
                try:
                    if selector.startswith("//"):
                        el = self.driver.find_element(By.XPATH, selector)
                    else:
                        el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if el and el.is_displayed():
                        el.click()
                        time.sleep(3)
                        logger.info("Opened form from My Tray (edit icon)")
                        return True
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            # Check if form status shows INCOMPLETE (clickable row)
            try:
                incomplete_rows = self.driver.find_elements(
                    By.XPATH, "//tr[contains(., 'INCOMPLETE')]//a | //tr[contains(., 'INCOMPLETE')]//i"
                )
                if incomplete_rows:
                    incomplete_rows[0].click()
                    time.sleep(3)
                    logger.info("Opened INCOMPLETE form from tray")
                    return True
            except Exception:
                pass
            
            logger.info("No existing application found in My Tray")
            return False
            
        except Exception as e:
            logger.warning("Error opening form from tray: {}", str(e))
            return False

    def _add_new_license(self, license_type: str = "new"):
        """
        Add a new license to My Tray via the Active License(s) flow.
        Flow: Active License(s) → Add New License → Search → Select → Add to Tray
        
        Args:
            license_type: 'new' or 'renewal'
        """
        try:
            # Navigate to Active Licenses
            active_url = self.config.base_url.rstrip('/') + "/myLicense/activeLicense"
            self.driver.get(active_url)
            time.sleep(2)
            
            # Click "Add New License" button
            add_new_selectors = [
                "//button[contains(text(), 'Add New')]",
                "//a[contains(text(), 'Add New')]",
                "//button[contains(text(), 'Tambah')]",
                "button[id*='addNew']",
                "a[id*='addNew']",
                ".btn-add-license",
            ]
            
            for selector in add_new_selectors:
                try:
                    if selector.startswith("//"):
                        el = self.driver.find_element(By.XPATH, selector)
                    else:
                        el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    el.click()
                    time.sleep(2)
                    logger.info("Clicked 'Add New License'")
                    break
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            # The rest of the flow (select company, search keyword, select license)
            # will be handled by AI or manual user interaction
            logger.info("Add new license flow initiated. Waiting for user/AI to complete selection...")
            self._take_screenshot("add_new_license_screen")
            
        except Exception as e:
            logger.error("Error adding new license: {}", str(e))

    def navigate_to_section(self, section_id: str):
        """
        Navigate to a specific form section (Bahagian).
        BLESS2 forms are divided into sections that may be tabs or sequential pages.
        
        Args:
            section_id: Section identifier like 'bahagian_a', 'bahagian_b', etc.
        """
        try:
            section_labels = {
                "bahagian_a": ["BAHAGIAN A", "Section A", "Maklumat Permohonan", "Butir-Butir Pemohon"],
                "bahagian_b": ["BAHAGIAN B", "Section B", "Maklumat Barang", "Butir-Butir Permit"],
                "bahagian_c": ["BAHAGIAN C", "Section C", "Maklumat Syarikat Pembekal"],
                "bahagian_d": ["BAHAGIAN D", "Section D", "Butir-Butir Lesen"],
                "bahagian_e": ["BAHAGIAN E", "Section E", "Senarai Semak", "Document Checklist"],
                "bahagian_f": ["BAHAGIAN F", "Section F", "Dokumen Sokongan"],
                "perakuan": ["PERAKUAN", "Declaration"],
            }
            
            labels = section_labels.get(section_id, [])
            
            for label in labels:
                # Try clicking tab/link with that label
                try:
                    el = self.driver.find_element(
                        By.XPATH, f"//a[contains(text(), '{label}')] | //li[contains(text(), '{label}')] | //div[contains(@class, 'tab')][contains(text(), '{label}')]"
                    )
                    if el and el.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        el.click()
                        time.sleep(1)
                        logger.info("Navigated to section: {}", section_id)
                        return True
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            # Sections might be all on one page (scroll to section)
            for label in labels:
                try:
                    heading = self.driver.find_element(
                        By.XPATH, f"//*[contains(text(), '{label}')]"
                    )
                    if heading:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", heading)
                        time.sleep(0.5)
                        logger.info("Scrolled to section: {}", section_id)
                        return True
                except NoSuchElementException:
                    continue
            
            logger.warning("Could not navigate to section: {}", section_id)
            return False
            
        except Exception as e:
            logger.warning("Error navigating to section {}: {}", section_id, str(e))
            return False

    def fill_bahagian_a(self, data: Dict[str, Any]):
        """
        Fill BAHAGIAN A - Applicant/Company Details.
        These are the core company fields that come from PDF extraction.
        
        Args:
            data: Dictionary with field values from extracted PDF data
        """
        logger.info("Filling BAHAGIAN A - Butir-Butir Pemohon/Syarikat...")
        
        self.navigate_to_section("bahagian_a")
        
        # Negeri (State) - dropdown
        if data.get("state"):
            self._fill_select_by_selectors(
                ["select[id*='negeri']", "select[name*='negeri']", "select[id*='state']"],
                data["state"]
            )
        
        # Cawangan Agensi Pemprosesan - dropdown (user-specific, may skip)
        if data.get("cawangan"):
            self._fill_select_by_selectors(
                ["select[id*='cawangan']", "select[name*='cawangan']", "select[id*='branch']"],
                data["cawangan"]
            )
        
        # Bentuk Perniagaan (Business Type) - dropdown
        if data.get("company_type"):
            self._fill_select_by_selectors(
                ["select[id*='bentuk']", "select[name*='bentuk']", "select[id*='businessType']"],
                data["company_type"]
            )
        
        # Aktiviti Perniagaan (Business Activity)
        if data.get("business_nature"):
            self._fill_text_by_selectors(
                ["input[id*='aktiviti']", "input[name*='aktiviti']", "textarea[id*='aktiviti']", "input[id*='activity']"],
                data["business_nature"]
            )
        
        # No. Telefon Pejabat (Office Phone)
        if data.get("phone"):
            self._fill_text_by_selectors(
                ["input[id*='noTel']", "input[name*='noTel']", "input[id*='phone']", "input[id*='telefon']"],
                data["phone"]
            )
        
        # No. Telefon Bimbit (Mobile)
        if data.get("mobile") or data.get("phone"):
            self._fill_text_by_selectors(
                ["input[id*='bimbit']", "input[name*='bimbit']", "input[id*='mobile']", "input[id*='hp']"],
                data.get("mobile", data.get("phone", ""))
            )
        
        # No. Faks
        if data.get("fax"):
            self._fill_text_by_selectors(
                ["input[id*='faks']", "input[name*='faks']", "input[id*='fax']"],
                data["fax"]
            )
        
        # Email
        if data.get("email"):
            self._fill_text_by_selectors(
                ["input[id*='email']", "input[name*='email']", "input[type='email']"],
                data["email"]
            )
        
        logger.info("BAHAGIAN A completed")

    def submit_application(self):
        """
        Submit the application after all sections are filled.
        Flow: Tick PERAKUAN checkbox → Click Submit button.
        """
        try:
            logger.info("Submitting application...")
            
            # Navigate to PERAKUAN section
            self.navigate_to_section("perakuan")
            time.sleep(1)
            
            # Tick the declaration checkbox
            perakuan_selectors = [
                "input[type='checkbox'][id*='perakuan']",
                "input[type='checkbox'][id*='declare']",
                "input[type='checkbox'][name*='perakuan']",
                "input[type='checkbox'][name*='declare']",
                "input[type='checkbox'][name*='agree']",
            ]
            
            for selector in perakuan_selectors:
                try:
                    checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                        checkbox.click()
                        logger.info("PERAKUAN checkbox ticked")
                        break
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            time.sleep(1)
            
            # Click Submit button
            self._submit_form()
            
            logger.info("Application submitted successfully!")
            self._take_screenshot("submission_success")
            
        except Exception as e:
            logger.error("Submission failed: {}", str(e))
            self._take_screenshot("submission_error")

    def save_draft(self):
        """Save the current form as draft without submitting."""
        try:
            save_selectors = [
                "button:contains('Simpan')",
                "button:contains('Save')",
                "button[id*='save']",
                "//button[contains(text(), 'Simpan')]",
                "//button[contains(text(), 'Save')]",
            ]
            
            for selector in save_selectors:
                try:
                    if selector.startswith("//"):
                        el = self.driver.find_element(By.XPATH, selector)
                    else:
                        el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    el.click()
                    time.sleep(2)
                    logger.info("Form saved as draft")
                    return True
                except (NoSuchElementException, ElementNotInteractableException):
                    continue
            
            logger.warning("Save button not found")
            return False
            
        except Exception as e:
            logger.error("Error saving draft: {}", str(e))
            return False

    def _fill_text_by_selectors(self, selectors: List[str], value: str) -> bool:
        """Helper: Fill text field trying multiple selectors."""
        element = self._find_element_by_selectors(selectors)
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
            element.clear()
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            element.send_keys(value)
            return True
        return False

    def _fill_select_by_selectors(self, selectors: List[str], value: str) -> bool:
        """Helper: Fill select/dropdown trying multiple selectors."""
        element = self._find_element_by_selectors(selectors)
        if element:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
            try:
                select = Select(element)
                # Try by value
                try:
                    select.select_by_value(value)
                    return True
                except NoSuchElementException:
                    pass
                # Try by visible text
                try:
                    select.select_by_visible_text(value)
                    return True
                except NoSuchElementException:
                    pass
                # Try partial match
                for option in select.options:
                    if value.upper() in option.text.upper():
                        select.select_by_visible_text(option.text)
                        return True
            except Exception:
                pass
        return False

    def get_current_page_fields(self) -> List[Dict[str, str]]:
        """
        Scan the current page and identify all form fields.
        Useful for dynamic field discovery.
        """
        fields = []
        
        try:
            # Find all input fields
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
            
            for inp in inputs:
                field_info = {
                    "tag": inp.tag_name,
                    "type": inp.get_attribute("type") or "",
                    "name": inp.get_attribute("name") or "",
                    "id": inp.get_attribute("id") or "",
                    "placeholder": inp.get_attribute("placeholder") or "",
                    "value": inp.get_attribute("value") or "",
                    "required": inp.get_attribute("required") is not None,
                }
                fields.append(field_info)
                
            logger.info("Found {} form fields on current page", len(fields))
            
        except Exception as e:
            logger.error("Error scanning page fields: {}", str(e))
            
        return fields

    def save_session(self, filepath: str = "session_data.json"):
        """Save current session data (cookies, filled fields) for resuming later."""
        session_data = {
            "cookies": self.driver.get_cookies() if self.driver else [],
            "current_url": self.driver.current_url if self.driver else "",
            "filled_fields": self._filled_fields,
            "errors": self._errors,
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        logger.info("Session saved to {}", filepath)

    def load_session(self, filepath: str = "session_data.json"):
        """Load a previously saved session."""
        try:
            with open(filepath, 'r') as f:
                session_data = json.load(f)
            
            if self.driver and session_data.get("cookies"):
                self.driver.get(self.config.base_url)
                for cookie in session_data["cookies"]:
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception:
                        pass
                self.driver.refresh()
                
            logger.info("Session loaded from {}", filepath)
            
        except FileNotFoundError:
            logger.warning("No session file found at {}", filepath)
        except Exception as e:
            logger.error("Error loading session: {}", str(e))

    def _dismiss_post_login_modals(self):
        """Dismiss any modal dialogs that appear after login."""
        try:
            modal_close_selectors = [
                ".modal .close",
                ".modal button.close",
                ".modal-footer .btn",
                "button[data-dismiss='modal']",
                ".ui-dialog .ui-dialog-titlebar-close",
                ".modal-header button",
                ".modal-header .close",
                "//div[contains(@class, 'modal')]//button[contains(@class, 'close')]",
                "//div[contains(@class, 'modal')]//button[contains(@class, 'btn')]",
                "//div[contains(@class, 'modal')]//a[contains(@class, 'btn')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'Tutup')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'Close')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'OK')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'Ya')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'Setuju')]",
                "//div[contains(@class, 'modal')]//button[contains(text(), 'Teruskan')]",
                "//div[contains(@class, 'modal')]//a[contains(text(), 'Tutup')]",
                "//div[contains(@class, 'modal')]//a[contains(text(), 'OK')]",
                "//div[contains(@class, 'modal')]//span[contains(text(), '×')]",
            ]
            
            for attempt in range(5):
                modal_found = False
                for selector in modal_close_selectors:
                    try:
                        if selector.startswith("//"):
                            el = self.driver.find_element(By.XPATH, selector)
                        else:
                            el = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if el and el.is_displayed():
                            el.click()
                            logger.info("Post-login modal dismissed via '{}'", selector)
                            time.sleep(0.5)
                            modal_found = True
                            break
                    except (NoSuchElementException, ElementNotInteractableException):
                        continue
                if modal_found:
                    time.sleep(1)
                else:
                    # Also check for hidden modals via JS
                    try:
                        hidden_modals = self.driver.find_elements(By.CSS_SELECTOR, 
                            ".modal.fade.in, .modal.show, div[style*='display: block'][class*='modal']")
                        for m in hidden_modals:
                            if m.is_displayed():
                                self.driver.execute_script("arguments[0].style.display='none';", m)
                                logger.info("Post-login modal hidden via JS")
                                time.sleep(0.5)
                    except Exception:
                        pass
                    break
        except Exception as e:
            logger.warning("Error dismissing post-login modals: {}", str(e))

    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception:
                pass
            self.driver = None

    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
