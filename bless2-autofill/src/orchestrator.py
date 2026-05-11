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

from loguru import logger

from .pdf_parser import PDFParser, ExtractedData
from .field_mapper import FieldMapper, FormSection
from .browser_automation import BLESS2AutoFill, BrowserConfig


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
        self.extracted_data: Optional[ExtractedData] = None
        self.mapped_sections: List[FormSection] = []
        
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
            results["steps"]["pdf_parsing"] = {
                "status": "success",
                "summary": parse_summary,
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
                    
                    # Fill the form
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
