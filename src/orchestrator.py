"""
Orchestrator Module
===================
Main coordinator that ties together:
1. PDF parsing
2. Field mapping
3. Browser automation (auto-fill)

Provides a simple interface to run the entire workflow.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

# Load .env file if it exists
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

from .pdf_parser import PDFParser, ExtractedData
from .field_mapper import FieldMapper, FormSection
from .browser_automation import BLESS2AutoFill, BrowserConfig
from .ai_engine import AIEngine, AIConfig


class BLESS2Orchestrator:
    """
    Main orchestrator for the BLESS2 Auto-Fill system.
    
    Usage:
        orchestrator = BLESS2Orchestrator()
        orchestrator.run(
            pdf_directory="./documents",
            username="your_bless_id",
            password="your_password"
        )
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Optional path to YAML/JSON configuration file
        """
        self.config = self._load_config(config_path)
        self.parser: Optional[PDFParser] = None
        self.mapper: Optional[FieldMapper] = None
        self.automation: Optional[BLESS2AutoFill] = None
        self.ai_engine: Optional[AIEngine] = None
        self.extracted_data: Optional[ExtractedData] = None
        self.mapped_sections: List[FormSection] = []
        
        # Initialize AI Engine if API key is available
        ai_key = os.getenv("OPENROUTER_API_KEY", self.config.get("openrouter_api_key", ""))
        if ai_key:
            ai_config = AIConfig(
                api_key=ai_key,
                model=self.config.get("ai_model", "openai/gpt-4o-mini"),
                fallback_model=self.config.get("ai_fallback_model", "google/gemini-2.0-flash-001"),
            )
            self.ai_engine = AIEngine(config=ai_config)
            logger.info("AI Engine enabled (model: {})", ai_config.model)
        else:
            logger.info("AI Engine disabled (no OPENROUTER_API_KEY). Using regex-based extraction.")
        
        # Setup logging
        self._setup_logging()
        
        logger.info("BLESS2 Orchestrator initialized")

    def run(
        self,
        pdf_path: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headless: bool = False,
        auto_submit: bool = False,
        dry_run: bool = False,
        output_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete auto-fill workflow.
        
        Args:
            pdf_path: Path to PDF file or directory containing PDFs
            username: BLESS2 login username (or set BLESS2_USERNAME env var)
            password: BLESS2 login password (or set BLESS2_PASSWORD env var)
            headless: Run browser in headless mode
            auto_submit: Auto-submit form after filling
            dry_run: Only extract and map data, don't open browser
            output_json: Optional path to save extracted data as JSON
            
        Returns:
            Dictionary with workflow results
        """
        results = {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
            "steps": {},
        }
        
        try:
            # ================================
            # Step 1: Parse PDF Documents
            # ================================
            logger.info("=" * 60)
            logger.info("STEP 1: Parsing PDF Documents")
            logger.info("=" * 60)
            
            self.parser = PDFParser(ocr_enabled=self.config.get("ocr_enabled", False))
            
            if os.path.isdir(pdf_path):
                self.extracted_data = self.parser.parse_directory(pdf_path)
            elif os.path.isfile(pdf_path):
                self.extracted_data = self.parser.parse_file(pdf_path)
            else:
                raise FileNotFoundError(f"PDF path not found: {pdf_path}")
            
            parse_summary = self.parser.get_summary()
            
            # ================================
            # Step 1.5: AI-Enhanced Extraction (if available)
            # ================================
            ai_extracted = None
            if self.ai_engine and self.ai_engine.is_configured():
                logger.info("=" * 60)
                logger.info("STEP 1.5: AI-Enhanced Data Extraction")
                logger.info("=" * 60)
                
                raw_text = self.extracted_data.raw_text
                if raw_text.strip():
                    ai_extracted = self.ai_engine.extract_from_pdf_text(raw_text)
                    
                    if ai_extracted:
                        # Merge AI extraction with regex extraction (AI takes priority)
                        self._merge_ai_extraction(ai_extracted)
                        logger.info("AI extraction merged successfully")
                        results["steps"]["ai_extraction"] = {
                            "status": "success",
                            "fields_extracted": len(ai_extracted),
                        }
                    else:
                        logger.warning("AI extraction returned no results, using regex extraction")
                        results["steps"]["ai_extraction"] = {"status": "no_results"}
                else:
                    logger.warning("No raw text available for AI extraction")
                    results["steps"]["ai_extraction"] = {"status": "skipped", "reason": "no_text"}
            
            # Update summary after potential AI merge
            parse_summary = self.parser.get_summary()
            results["steps"]["pdf_parsing"] = {
                "status": "success",
                "summary": parse_summary,
                "ai_enhanced": bool(ai_extracted),
            }
            
            logger.info("PDF Parsing complete. Confidence: {}", parse_summary["confidence_score"])
            logger.info("Company: {}", parse_summary["company_name"])
            logger.info("Reg No: {}", parse_summary["registration_number"])
            logger.info("Directors found: {}", parse_summary["directors_count"])
            
            # ================================
            # Step 2: Map Fields
            # ================================
            logger.info("=" * 60)
            logger.info("STEP 2: Mapping Fields to BLESS2 Form")
            logger.info("=" * 60)
            
            self.mapper = FieldMapper()
            self.mapped_sections = self.mapper.map_data(self.extracted_data)
            
            mapping_summary = self.mapper.get_mapped_summary()
            results["steps"]["field_mapping"] = {
                "status": "success",
                "summary": mapping_summary,
            }
            
            # Print mapping summary
            for section_name, info in mapping_summary.items():
                logger.info("  {} - {}/{} fields mapped", 
                           section_name, info["filled_fields"], info["total_fields"])
            
            # Export mapped data
            if output_json:
                export_data = self.mapper.export_to_dict()
                export_data["_meta"] = {
                    "source_files": self.extracted_data.source_files,
                    "extraction_date": self.extracted_data.extraction_date,
                    "confidence_score": self.extracted_data.confidence_score,
                }
                
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                logger.info("Mapped data exported to: {}", output_json)
                results["steps"]["export"] = {"status": "success", "file": output_json}
            
            # ================================
            # Step 3: Browser Automation (if not dry run)
            # ================================
            if dry_run:
                logger.info("=" * 60)
                logger.info("DRY RUN - Skipping browser automation")
                logger.info("=" * 60)
                results["steps"]["browser_automation"] = {"status": "skipped", "reason": "dry_run"}
                results["status"] = "completed_dry_run"
            else:
                logger.info("=" * 60)
                logger.info("STEP 3: Browser Automation - Auto-Filling BLESS2")
                logger.info("=" * 60)
                
                # Get credentials
                username = username or os.getenv("BLESS2_USERNAME")
                password = password or os.getenv("BLESS2_PASSWORD")
                
                if not username or not password:
                    logger.error("Login credentials required. Set BLESS2_USERNAME and BLESS2_PASSWORD env vars or pass as arguments.")
                    results["steps"]["browser_automation"] = {
                        "status": "error",
                        "error": "Missing credentials"
                    }
                    results["status"] = "partial_completion"
                    return results
                
                # Configure browser
                browser_config = BrowserConfig(
                    headless=headless,
                    timeout=self.config.get("timeout", 30),
                    slow_mode=self.config.get("slow_mode", True),
                    slow_mode_delay=self.config.get("slow_mode_delay", 0.5),
                    screenshot_on_error=True,
                )
                
                self.automation = BLESS2AutoFill(config=browser_config)
                
                try:
                    # Start browser
                    self.automation.start_browser()
                    
                    # Login
                    login_success = self.automation.login(username, password)
                    if not login_success:
                        results["steps"]["browser_automation"] = {
                            "status": "error",
                            "error": "Login failed"
                        }
                        results["status"] = "login_failed"
                        return results
                    
                    # Navigate to application form
                    self.automation.navigate_to_application("new")
                    
                    # AI-powered dynamic field matching (if available)
                    if self.ai_engine and self.ai_engine.is_configured():
                        logger.info("Using AI to analyze page and match fields dynamically...")
                        page_html = self.automation.driver.page_source
                        page_url = self.automation.driver.current_url
                        
                        # Analyze page structure
                        page_analysis = self.ai_engine.analyze_page(page_html, page_url)
                        if page_analysis:
                            logger.info("AI page analysis: {}", page_analysis.get("page_title", "Unknown"))
                            results["steps"]["ai_page_analysis"] = {
                                "status": "success",
                                "page_title": page_analysis.get("page_title"),
                                "sections_found": len(page_analysis.get("form_sections", [])),
                            }
                        
                        # Get AI field mappings
                        export_data = self.mapper.export_to_dict()
                        ai_mappings = self.ai_engine.match_fields_to_form(export_data, page_html)
                        
                        if ai_mappings:
                            # Use AI mappings for filling
                            fill_results = self._fill_with_ai_mappings(ai_mappings)
                            results["steps"]["ai_field_matching"] = {
                                "status": "success",
                                "fields_matched": len(ai_mappings),
                            }
                        else:
                            # Fallback to static mapping
                            logger.info("AI matching returned no results, using static mappings...")
                            fill_results = self.automation.fill_form(
                                self.mapped_sections, auto_submit=auto_submit
                            )
                    else:
                        # No AI - use static field mapping
                        fill_results = self.automation.fill_form(
                            self.mapped_sections, 
                            auto_submit=auto_submit
                        )
                    
                    results["steps"]["browser_automation"] = {
                        "status": "success",
                        "fill_results": fill_results,
                    }
                    
                    # Save session for potential resume
                    self.automation.save_session("./bless2_session.json")
                    
                    results["status"] = "completed"
                    
                except Exception as e:
                    logger.error("Browser automation error: {}", str(e))
                    results["steps"]["browser_automation"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    results["status"] = "automation_error"
                    
                finally:
                    if not self.config.get("keep_browser_open", False):
                        self.automation.close()
            
        except Exception as e:
            logger.error("Orchestrator error: {}", str(e))
            results["status"] = "error"
            results["error"] = str(e)
        
        # Save results
        results_file = "./bless2_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info("Results saved to: {}", results_file)
        
        return results

    def extract_only(self, pdf_path: str, output_json: str = "./extracted_data.json") -> ExtractedData:
        """
        Only extract data from PDFs without browser automation.
        Useful for reviewing what will be filled.
        
        Args:
            pdf_path: Path to PDF file or directory
            output_json: Output JSON file path
            
        Returns:
            ExtractedData object
        """
        return self.run(
            pdf_path=pdf_path,
            dry_run=True,
            output_json=output_json,
        )

    def preview_mapping(self, pdf_path: str) -> None:
        """
        Preview the field mapping without filling any forms.
        Prints a formatted table of what would be filled.
        """
        self.parser = PDFParser(ocr_enabled=self.config.get("ocr_enabled", False))
        
        if os.path.isdir(pdf_path):
            self.extracted_data = self.parser.parse_directory(pdf_path)
        else:
            self.extracted_data = self.parser.parse_file(pdf_path)
        
        self.mapper = FieldMapper()
        self.mapped_sections = self.mapper.map_data(self.extracted_data)
        
        # Print preview
        print("\n" + "=" * 80)
        print("BLESS2 AUTO-FILL PREVIEW")
        print("=" * 80)
        print(f"\nSource: {pdf_path}")
        print(f"Confidence Score: {self.extracted_data.confidence_score:.0%}")
        print()
        
        for section in self.mapped_sections:
            print(f"\n{'─' * 60}")
            print(f"📋 {section.name}")
            print(f"{'─' * 60}")
            
            for field in section.fields:
                status = "✅" if field.value else "⚠️ EMPTY"
                required = " [REQUIRED]" if field.required else ""
                value_display = field.value[:50] + "..." if len(field.value) > 50 else field.value
                print(f"  {status} {field.field_name}{required}")
                if field.value:
                    print(f"     → {value_display}")
                print()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "base_url": "https://bless2.bless.gov.my/bless2/private",
            "ocr_enabled": False,
            "timeout": 30,
            "slow_mode": True,
            "slow_mode_delay": 0.5,
            "keep_browser_open": False,
            "log_level": "INFO",
            "log_file": "./bless2_autofill.log",
        }
        
        if config_path and os.path.exists(config_path):
            try:
                if config_path.endswith('.json'):
                    with open(config_path, 'r') as f:
                        user_config = json.load(f)
                elif config_path.endswith(('.yml', '.yaml')):
                    import yaml
                    with open(config_path, 'r') as f:
                        user_config = yaml.safe_load(f)
                else:
                    user_config = {}
                    
                default_config.update(user_config)
            except Exception as e:
                logger.warning("Could not load config from {}: {}", config_path, str(e))
        
        return default_config

    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config.get("log_level", "INFO")
        log_file = self.config.get("log_file", "./bless2_autofill.log")
        
        # Remove default handler
        logger.remove()
        
        # Console output
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
        )
        
        # File output
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
        )

    def _merge_ai_extraction(self, ai_data: Dict[str, Any]):
        """
        Merge AI-extracted data into the existing ExtractedData structure.
        AI data takes priority over regex-extracted data.
        """
        if not self.extracted_data:
            return
        
        company = self.extracted_data.company
        
        # Merge company info (AI overrides empty fields or all if AI has data)
        company_data = {}
        # Handle both nested and flat structures
        if "company_name" in ai_data:
            company_data = ai_data  # Flat structure
        elif "COMPANY INFO" in ai_data:
            company_data = ai_data.get("COMPANY INFO", {})
        elif "company" in ai_data:
            company_data = ai_data.get("company", {})
        
        field_mapping = {
            "company_name": "company_name",
            "registration_number": "registration_number",
            "old_registration_number": "old_registration_number",
            "company_type": "company_type",
            "incorporation_date": "incorporation_date",
            "business_nature": "business_nature",
            "msic_code": "msic_code",
            "msic_description": "msic_description",
            "status": "status",
            "paid_up_capital": "paid_up_capital",
            "authorized_capital": "authorized_capital",
            "phone": "phone",
            "fax": "fax",
            "email": "email",
            "website": "website",
        }
        
        for ai_key, attr_name in field_mapping.items():
            value = company_data.get(ai_key, "")
            if value and isinstance(value, str) and value.strip():
                setattr(company, attr_name, value.strip())
        
        # Address fields
        address_data = ai_data.get("ADDRESS", ai_data.get("address", company_data))
        if isinstance(address_data, dict):
            addr_fields = {
                "registered_address": "registered_address",
                "business_address": "business_address",
                "postcode": "postcode",
                "city": "city",
                "state": "state",
                "country": "country",
            }
            for ai_key, attr_name in addr_fields.items():
                value = address_data.get(ai_key, "")
                if value and isinstance(value, str) and value.strip():
                    setattr(company, attr_name, value.strip())
        
        # Financial
        financial_data = ai_data.get("FINANCIAL", ai_data.get("financial", {}))
        if isinstance(financial_data, dict):
            if financial_data.get("paid_up_capital"):
                company.paid_up_capital = str(financial_data["paid_up_capital"])
            if financial_data.get("authorized_capital"):
                company.authorized_capital = str(financial_data["authorized_capital"])
        
        # Contact
        contact_data = ai_data.get("CONTACT", ai_data.get("contact", {}))
        if isinstance(contact_data, dict):
            if contact_data.get("phone"):
                company.phone = contact_data["phone"]
            if contact_data.get("fax"):
                company.fax = contact_data["fax"]
            if contact_data.get("email"):
                company.email = contact_data["email"]
            if contact_data.get("website"):
                company.website = contact_data["website"]
        
        # Directors
        directors_data = ai_data.get("DIRECTORS", ai_data.get("directors", []))
        if isinstance(directors_data, list) and directors_data:
            from .pdf_parser import DirectorInfo
            
            # Replace existing directors with AI-extracted ones (more reliable)
            self.extracted_data.directors = []
            for d in directors_data:
                if isinstance(d, dict) and d.get("name"):
                    director = DirectorInfo(
                        name=d.get("name", ""),
                        ic_number=d.get("ic_number", ""),
                        nationality=d.get("nationality", "MALAYSIAN"),
                        designation=d.get("designation", "Director"),
                        address=d.get("address", ""),
                        date_of_birth=d.get("date_of_birth", ""),
                        gender=d.get("gender", ""),
                        appointment_date=d.get("appointment_date", ""),
                        shares_held=d.get("shares_held", ""),
                        share_percentage=d.get("share_percentage", ""),
                    )
                    self.extracted_data.directors.append(director)
        
        # Recalculate confidence
        self.parser._calculate_confidence()
        logger.info("Data merged. New confidence: {:.0%}", self.extracted_data.confidence_score)

    def _fill_with_ai_mappings(self, ai_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fill form using AI-generated field mappings.
        More flexible than static mapping as it adapts to actual page DOM.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import Select
        import time
        
        results = {
            "total_fields": len(ai_mappings),
            "filled_successfully": 0,
            "failed_fields": [],
            "skipped_fields": [],
        }
        
        for mapping in ai_mappings:
            selector = mapping.get("selector", "")
            value = mapping.get("value", "")
            field_type = mapping.get("field_type", "text")
            field_name = mapping.get("field_name", "Unknown")
            confidence = mapping.get("confidence", 0)
            
            # Skip low-confidence matches
            if confidence < 0.5:
                results["skipped_fields"].append({
                    "field": field_name,
                    "reason": f"Low confidence ({confidence})"
                })
                continue
            
            if not value or not selector:
                results["skipped_fields"].append({
                    "field": field_name,
                    "reason": "No value or selector"
                })
                continue
            
            try:
                # Find element
                element = None
                try:
                    if selector.startswith("//"):
                        element = self.automation.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.automation.driver.find_element(By.CSS_SELECTOR, selector)
                except Exception:
                    # Try alternative approaches
                    alt_selectors = [
                        f"[id='{mapping.get('field_id', '')}']",
                        f"[name='{mapping.get('field_name', '')}']",
                    ]
                    for alt in alt_selectors:
                        try:
                            element = self.automation.driver.find_element(By.CSS_SELECTOR, alt)
                            break
                        except Exception:
                            continue
                
                if not element:
                    results["failed_fields"].append({"field": field_name, "reason": "Element not found"})
                    continue
                
                # Scroll into view
                self.automation.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", element
                )
                time.sleep(0.3)
                
                # Fill based on type
                if field_type == "select":
                    try:
                        select = Select(element)
                        try:
                            select.select_by_value(value)
                        except Exception:
                            select.select_by_visible_text(value)
                    except Exception:
                        element.click()
                        time.sleep(0.3)
                        
                elif field_type == "radio":
                    if not element.is_selected():
                        element.click()
                        
                elif field_type == "checkbox":
                    should_check = value.lower() in ("true", "1", "yes", "checked")
                    if element.is_selected() != should_check:
                        element.click()
                        
                elif field_type == "date":
                    element.clear()
                    element.send_keys(Keys.CONTROL + "a")
                    element.send_keys(Keys.DELETE)
                    element.send_keys(value)
                    
                else:  # text, textarea
                    element.clear()
                    element.send_keys(Keys.CONTROL + "a")
                    element.send_keys(Keys.DELETE)
                    element.send_keys(value)
                
                results["filled_successfully"] += 1
                logger.debug("AI filled '{}' with '{}' (confidence: {})", 
                           field_name, value[:30], confidence)
                
                if self.automation.config.slow_mode:
                    time.sleep(self.automation.config.slow_mode_delay)
                    
            except Exception as e:
                logger.warning("Failed to fill '{}': {}", field_name, str(e))
                
                # Ask AI for fix suggestion
                if self.ai_engine:
                    fix = self.ai_engine.suggest_fix({
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "selector": selector,
                        "url": self.automation.driver.current_url,
                    })
                    
                    if fix.get("alternative_selector"):
                        try:
                            alt_element = self.automation.driver.find_element(
                                By.CSS_SELECTOR, fix["alternative_selector"]
                            )
                            alt_element.clear()
                            alt_element.send_keys(value)
                            results["filled_successfully"] += 1
                            logger.info("AI fix worked for '{}'", field_name)
                            continue
                        except Exception:
                            pass
                
                results["failed_fields"].append({
                    "field": field_name,
                    "reason": str(e)
                })
        
        logger.info("AI fill complete: {}/{} fields", 
                   results["filled_successfully"], results["total_fields"])
        return results
