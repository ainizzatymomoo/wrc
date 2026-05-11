#!/usr/bin/env python3
"""
BLESS2 Auto-Fill System
========================
Main entry point for the PDF-to-BLESS2 auto-fill system.

Usage:
    # Full auto-fill (parse PDF + fill website)
    python main.py --pdf ./documents/ --username YOUR_ID --password YOUR_PASS

    # Dry run (parse PDF only, output JSON)
    python main.py --pdf ./documents/ --dry-run --output ./output.json

    # Preview what will be filled
    python main.py --pdf ./documents/ --preview

    # With config file
    python main.py --pdf ./documents/ --config ./config/settings.yaml

Environment Variables:
    BLESS2_USERNAME - Login username for BLESS2
    BLESS2_PASSWORD - Login password for BLESS2
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import BLESS2Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="BLESS2 Auto-Fill System - Parse PDFs and auto-fill BLESS2 forms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf ./documents/ --dry-run --output ./data.json
  %(prog)s --pdf ./ssm_cert.pdf --preview
  %(prog)s --pdf ./documents/ --username MYID --password MYPASS
  %(prog)s --pdf ./documents/ --headless --auto-submit
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--pdf", "-p",
        required=True,
        help="Path to PDF file or directory containing PDF files"
    )
    
    # Optional arguments
    parser.add_argument(
        "--username", "-u",
        default=os.getenv("BLESS2_USERNAME"),
        help="BLESS2 login username (or set BLESS2_USERNAME env var)"
    )
    
    parser.add_argument(
        "--password", "-pw",
        default=os.getenv("BLESS2_PASSWORD"),
        help="BLESS2 login password (or set BLESS2_PASSWORD env var)"
    )
    
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to configuration file (YAML/JSON)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./extracted_data.json",
        help="Output JSON file for extracted data (default: ./extracted_data.json)"
    )
    
    # Mode flags
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Only parse PDFs and map fields, don't open browser"
    )
    
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the field mapping in a formatted table"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)"
    )
    
    parser.add_argument(
        "--auto-submit",
        action="store_true",
        help="Automatically submit the form after filling"
    )
    
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Enable OCR for scanned PDF documents"
    )
    
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Keep browser open after filling (for manual review)"
    )
    
    parser.add_argument(
        "--slow-mode",
        action="store_true",
        default=True,
        help="Add delays between actions for stability (default: True)"
    )
    
    args = parser.parse_args()
    
    # Validate PDF path
    if not os.path.exists(args.pdf):
        print(f"Error: PDF path not found: {args.pdf}")
        sys.exit(1)
    
    # Initialize orchestrator
    orchestrator = BLESS2Orchestrator(config_path=args.config)
    
    # Override config with CLI arguments
    if args.ocr:
        orchestrator.config["ocr_enabled"] = True
    if args.keep_open:
        orchestrator.config["keep_browser_open"] = True
    
    # Execute based on mode
    if args.preview:
        # Preview mode - just show what would be filled
        orchestrator.preview_mapping(args.pdf)
        
    elif args.dry_run:
        # Dry run - parse and map only
        results = orchestrator.run(
            pdf_path=args.pdf,
            dry_run=True,
            output_json=args.output,
        )
        print(f"\n✅ Dry run complete. Data exported to: {args.output}")
        print(f"   Confidence Score: {results['steps'].get('pdf_parsing', {}).get('summary', {}).get('confidence_score', 'N/A')}")
        
    else:
        # Full auto-fill mode
        if not args.username or not args.password:
            print("Error: Username and password required for auto-fill mode.")
            print("  Use --username and --password, or set BLESS2_USERNAME and BLESS2_PASSWORD env vars.")
            print("  Use --dry-run to only extract data without login.")
            sys.exit(1)
        
        results = orchestrator.run(
            pdf_path=args.pdf,
            username=args.username,
            password=args.password,
            headless=args.headless,
            auto_submit=args.auto_submit,
            dry_run=False,
            output_json=args.output,
        )
        
        # Print final status
        status = results.get("status", "unknown")
        if status == "completed":
            fill_results = results.get("steps", {}).get("browser_automation", {}).get("fill_results", {})
            print(f"\n✅ Auto-fill completed successfully!")
            print(f"   Fields filled: {fill_results.get('filled_successfully', 0)}/{fill_results.get('total_fields', 0)}")
        elif status == "completed_dry_run":
            print(f"\n✅ Dry run completed. See {args.output} for extracted data.")
        else:
            print(f"\n❌ Process ended with status: {status}")
            if "error" in results:
                print(f"   Error: {results['error']}")


if __name__ == "__main__":
    main()
