#!/usr/bin/env python3
"""
Run the BLESS2 Auto-Fill Web GUI
=================================
Start the web server at http://localhost:8000

Usage:
    python run_gui.py
    python run_gui.py --port 8080
    python run_gui.py --host 0.0.0.0 --port 8000
"""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="BLESS2 Auto-Fill Web GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║          BLESS2 Auto-Fill Web GUI                        ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║   🌐  URL:  http://{args.host}:{args.port}              ║
║                                                          ║
║   📄  Upload PDF → Preview Data → Auto-Fill BLESS2      ║
║                                                          ║
║   Press Ctrl+C to stop the server                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
