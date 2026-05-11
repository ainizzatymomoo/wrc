"""
BLESS2 Auto-Fill System
========================
Automatically parses PDF documents (SSM, business registration, etc.)
and fills in related fields on the BLESS2 government website.

Modules:
- pdf_parser: Extract structured data from various PDF document types
- field_mapper: Map extracted data to BLESS2 form fields
- browser_automation: Selenium/Playwright-based form filler
- orchestrator: Main coordinator that ties everything together
"""

__version__ = "1.0.0"
__author__ = "WRC Team"
