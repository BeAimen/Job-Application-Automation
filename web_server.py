#!/usr/bin/env python3
"""
Standalone web server runner for Job Application Automation.
Run this file directly to start the web UI.
"""

import os
import sys
from pathlib import Path


def main():
    # ------------------------------------------------------------
    # 1. Ensure project root is added to sys.path properly
    # ------------------------------------------------------------
    # This file lives at: project_root/run_web.py
    # So project root = parent of this file
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))

    import uvicorn
    from dotenv import load_dotenv

    # Load .env from project root
    load_dotenv(dotenv_path=project_root / ".env")

    # Configuration
    host = os.getenv("WEB_HOST", "localhost")
    port = int(os.getenv("WEB_PORT", "8000"))
    debug = os.getenv("WEB_DEBUG", "true").lower() == "true"

    print(
        f"""
    ╔════════════════════════════════════════════════════════════╗
    ║   Job Application Automation System - Web Interface        ║
    ╚════════════════════════════════════════════════════════════╝

    🌐 Server starting...
    📍 URL: http://{host}:{port}
    🔧 Debug mode: {debug}

    Press Ctrl+C to stop the server
    """
    )

    try:
        uvicorn.run(
            app="src.ui_web:app",     # <- keep this form; uvicorn locates module correctly
            host=host,
            port=port,
            reload=debug,
            log_level="info" if debug else "warning",
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
