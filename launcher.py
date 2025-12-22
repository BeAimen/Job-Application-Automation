#!/usr/bin/env python3
"""
JobFlow Application Launcher
Professional launcher that starts the web server and opens the browser automatically.
Works on Windows, macOS, and Linux.
"""

import os
import sys
import time
import webbrowser
import threading
import socket
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).resolve().parent


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def wait_for_server(host, port, timeout=30):
    """Wait for the server to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex((host, port)) == 0:
                    return True
        except:
            pass
        time.sleep(0.5)
    return False


def open_browser(url, delay=2):
    """Open browser after a delay to ensure server is ready."""
    time.sleep(delay)
    print(f"🌐 Opening browser: {url}")
    webbrowser.open(url)


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner(host, port):
    """Print startup banner."""
    url = f"http://{host}:{port}"

    banner = f"""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║               🚀 JobFlow Application Manager 🚀                ║
║                                                                ║
║          Automate Your Job Applications with Ease             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

📍 Server Address:  {url}
🔧 Status:          Starting...
💡 Tip:             Press Ctrl+C to stop the server

────────────────────────────────────────────────────────────────
"""
    print(banner)


def main():
    """Main launcher function."""
    # Setup paths
    project_root = get_project_root()
    sys.path.insert(0, str(project_root))

    # Clear screen for clean startup
    clear_screen()

    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=project_root / ".env")

        # Get configuration
        host = os.getenv("WEB_HOST", "localhost")
        port = int(os.getenv("WEB_PORT", "8000"))
        debug = os.getenv("WEB_DEBUG", "true").lower() == "true"

        # Print banner
        print_banner(host, port)

        # Check if port is already in use
        if is_port_in_use(port):
            print(f"⚠️  Port {port} is already in use!")
            print(f"   Either:")
            print(f"   1. Another instance is running - opening browser to existing server...")
            print(f"   2. Another application is using port {port} - please change WEB_PORT in .env")
            print()

            url = f"http://{host}:{port}"
            webbrowser.open(url)

            response = input("Press Enter to exit or 'k' to try killing the existing process: ").lower()
            if response == 'k':
                print("⚠️  Please manually stop the other process and try again.")
            return

        # Start server in background thread
        print("🔄 Starting server...")

        import uvicorn

        # Create server config
        config = uvicorn.Config(
            app="src.ui_web:app",
            host=host,
            port=port,
            reload=debug,
            log_level="warning",  # Less verbose
            access_log=False  # Cleaner console
        )

        server = uvicorn.Server(config)

        # Schedule browser opening
        url = f"http://{host}:{port}"
        browser_thread = threading.Thread(
            target=open_browser,
            args=(url,),
            daemon=True
        )
        browser_thread.start()

        print(f"✅ Server started successfully!")
        print(f"🌐 Opening browser to {url}")
        print(f"\n{'─' * 64}")
        print("Server is running. Press Ctrl+C to stop.")
        print(f"{'─' * 64}\n")

        # Run server (blocking)
        server.run()

    except KeyboardInterrupt:
        print("\n\n" + "─" * 64)
        print("🛑 Shutting down gracefully...")
        print("👋 Server stopped. Thank you for using JobFlow!")
        print("─" * 64 + "\n")

    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\n💡 Solution: Install required packages")
        print("   Run: pip install -r requirements.txt\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("\n💡 Tips:")
        print("   - Ensure all dependencies are installed")
        print("   - Check your .env configuration")
        print("   - Verify Google credentials are set up")
        print(f"   - Try changing the port in .env (current: {port})\n")
        sys.exit(1)


if __name__ == "__main__":
    main()