import ctypes
import json
import os
import platform
import sys
from flask import Flask
import webview
from webview.platforms.edgechromium import EdgeChrome  # Use EdgeChrome instead of EdgeChromium
from app import create_app
from app.seeds import init_default_categories
from threading import Thread

# Custom EdgeChrome class to handle on_script_notify safely
class CustomEdgeChrome(EdgeChrome):
    def on_script_notify(self, func_param):
        if func_param is None:
            print("⚠️ Ignoring NoneType in on_script_notify")
            return
        try:
            super().on_script_notify(func_param)  # Call the original handler with valid data
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


def ensure_admin_privileges():
    """
    Ensure the script is running with administrative privileges.
    If not, restart the script with elevated permissions.
    """
    if platform.system() == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("Restarting with admin privileges...")
                script = sys.argv[0]
                params = " ".join(sys.argv[1:])
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
                sys.exit(0)
        except Exception as e:
            print(f"Failed to check or elevate privileges: {e}")
            sys.exit(1)
    else:
        if os.geteuid() != 0:
            print("This script requires admin privileges. Please run it with 'sudo'.")
            sys.exit(1)

# Detect if running as an EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # PyInstaller sets this for temp files
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

if __name__ == "__main__":
    app = create_app()
    ensure_admin_privileges()

    # Ensure the app context is pushed before calling init_default_categories
    with app.app_context():
        init_default_categories()

    # Run Flask in the background
    server_thread = Thread(target=app.run, kwargs={"port": 5000, "debug": False})
    server_thread.daemon = True
    server_thread.start()

    # Replace the default EdgeChrome class with the custom one
    webview.platforms.edgechromium.EdgeChrome = CustomEdgeChrome

    webview.create_window(
        "User Management App",
        "http://127.0.0.1:5000",
        js_api={},  # Remove on_script_notify from here
    )

    webview.start()
