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
        Login to the BLESS2 system.
        
        Args:
            username: BLESS2 username/ID
            password: BLESS2 password
            
        Returns:
            True if login successful
        """
        try:
            login_url = self.config.base_url.replace("/private", "/public/login")
            self.driver.get(login_url)
            
            logger.info("Navigating to login page: {}", login_url)
            time.sleep(2)  # Wait for page to fully load
            
            # Try multiple selectors for username field
            username_selectors = [
                "input[name='username']",
                "input[name='userId']",
                "input[id='username']",
                "input[id='userId']",
                "input[id='blessId']",
                "input[name='blessId']",
                "input[type='text']:first-of-type",
            ]
            
            username_field = self._find_element_by_selectors(username_selectors)
            if username_field:
                username_field.clear()
                username_field.send_keys(username)
                logger.info("Username entered")
            else:
                logger.error("Could not find username field")
                self._take_screenshot("login_error_username")
                return False
            
            # Try multiple selectors for password field
            password_selectors = [
                "input[name='password']",
                "input[id='password']",
                "input[type='password']",
            ]
            
            password_field = self._find_element_by_selectors(password_selectors)
            if password_field:
                password_field.clear()
                password_field.send_keys(password)
                logger.info("Password entered")
            else:
                logger.error("Could not find password field")
                self._take_screenshot("login_error_password")
                return False
            
            # Submit login form
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button[id*='login']",
                "button[id*='submit']",
                "a[id*='login']",
            ]
            
            submit_btn = self._find_element_by_selectors(submit_selectors)
            if submit_btn:
                submit_btn.click()
            else:
                # Try pressing Enter
                password_field.send_keys(Keys.RETURN)
            
            time.sleep(3)  # Wait for login to process
            
            # Check if login was successful (should redirect to private area)
            if "/private" in self.driver.current_url or "dashboard" in self.driver.current_url.lower():
                logger.info("Login successful! Current URL: {}", self.driver.current_url)
                return True
            else:
                logger.warning("Login may have failed. Current URL: {}", self.driver.current_url)
                self._take_screenshot("login_result")
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
        """
        Navigate to the application form.
        
        Args:
            application_type: 'new' for new application, 'renewal' for renewal
        """
        try:
            if application_type == "new":
                url = f"{self.config.base_url}/application/new"
            else:
                url = f"{self.config.base_url}/application/renewal"
                
            self.driver.get(url)
            time.sleep(2)
            logger.info("Navigated to {} application", application_type)
        except Exception as e:
            logger.error("Navigation failed: {}", str(e))

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
