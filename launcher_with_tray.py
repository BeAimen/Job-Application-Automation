#!/usr/bin/env python3
"""
JobFlow System Tray Application
Runs JobFlow with a system tray icon for easy control.

Requirements: pip install pystray pillow
"""

import os
import sys
import time
import webbrowser
import threading
import socket
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠️  System tray not available. Install with: pip install pystray pillow")
    print("   Falling back to standard launcher...\n")


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).resolve().parent


def create_icon_image():
    """Create a simple icon for the system tray."""
    # Create a 64x64 image with a gradient blue background
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), (37, 99, 235))

    # Draw a simple "J" for JobFlow
    draw = ImageDraw.Draw(image)

    # Draw letter J
    draw.rectangle([20, 15, 25, 45], fill=(255, 255, 255))
    draw.rectangle([20, 45, 35, 50], fill=(255, 255, 255))
    draw.rectangle([35, 40, 40, 50], fill=(255, 255, 255))

    return image


class JobFlowTray:
    """System tray application for JobFlow."""

    def __init__(self):
        self.project_root = get_project_root()
        sys.path.insert(0, str(self.project_root))

        from dotenv import load_dotenv
        load_dotenv(dotenv_path=self.project_root / ".env")

        self.host = os.getenv("WEB_HOST", "localhost")
        self.port = int(os.getenv("WEB_PORT", "8000"))
        self.url = f"http://{self.host}:{self.port}"
        self.server = None
        self.server_thread = None
        self.icon = None

    def start_server(self):
        """Start the uvicorn server in background."""
        import uvicorn

        config = uvicorn.Config(
            app="src.ui_web:app",
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False
        )

        self.server = uvicorn.Server(config)

        # Run server in thread
        self.server_thread = threading.Thread(
            target=self.server.run,
            daemon=True
        )
        self.server_thread.start()

        # Wait for server to be ready
        time.sleep(2)

        # Open browser
        webbrowser.open(self.url)

    def open_browser(self, icon, item):
        """Open browser to JobFlow."""
        webbrowser.open(self.url)

    def stop_server(self, icon, item):
        """Stop the server and exit."""
        print("\n🛑 Stopping JobFlow...")
        if self.server:
            self.server.should_exit = True
        icon.stop()

    def show_status(self, icon, item):
        """Show status notification."""
        if self.server:
            print(f"✅ JobFlow is running at {self.url}")
        else:
            print("❌ JobFlow is not running")

    def create_menu(self):
        """Create system tray menu."""
        return pystray.Menu(
            pystray.MenuItem(
                "Open JobFlow",
                self.open_browser,
                default=True
            ),
            pystray.MenuItem(
                "Show Status",
                self.show_status
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Quit JobFlow",
                self.stop_server
            )
        )

    def run(self):
        """Run the system tray application."""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║               🚀 JobFlow Application Manager 🚀                ║
║                                                                ║
║                   System Tray Mode Active                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

📍 Server Address:  {url}
🔧 Status:          Starting in background...
💡 Tip:             Check system tray for controls

────────────────────────────────────────────────────────────────
""".format(url=self.url))

        # Start server
        self.start_server()

        print("✅ Server started successfully!")
        print("🎯 System tray icon active - check your taskbar")
        print("🌐 Browser opened automatically")
        print("\nRight-click tray icon for options:")
        print("  • Open JobFlow")
        print("  • Show Status")
        print("  • Quit JobFlow\n")

        # Create and run tray icon
        icon_image = create_icon_image()
        self.icon = pystray.Icon(
            "JobFlow",
            icon_image,
            "JobFlow - Running",
            menu=self.create_menu()
        )

        # Run (blocking)
        self.icon.run()

        print("\n👋 JobFlow stopped. Goodbye!")


def run_with_tray():
    """Run with system tray support."""
    try:
        app = JobFlowTray()
        app.run()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down gracefully...")
        print("👋 Server stopped. Thank you for using JobFlow!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def run_without_tray():
    """Fallback to standard launcher without tray."""
    from launcher import main
    main()


def main():
    """Main entry point."""
    if TRAY_AVAILABLE:
        run_with_tray()
    else:
        run_without_tray()


if __name__ == "__main__":
    main()