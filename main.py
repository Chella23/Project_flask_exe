# main.py
import ctypes
import json
import os
import platform
import sys
import shutil
from threading import Thread
from flask import Flask
import webview
from webview.platforms.edgechromium import EdgeChrome
from app import create_app
from app.seeds import init_default_categories, check_and_initialize

# Custom EdgeChrome class with logging and error handling
class CustomEdgeChrome(EdgeChrome):
    def on_script_notify(self, func_param):
        if func_param is None:
            print("⚠️ Ignoring NoneType in on_script_notify")
            return
        try:
            super().on_script_notify(func_param)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    def load_url(self, url):
        print(f"Loading URL: {url}")
        super().load_url(url)

    def initialize(self):
        print(f"Initializing WebView2 with user data folder: {self.user_data_folder}")
        try:
            super().initialize()
        except Exception as e:
            print(f"WebView2 initialization failed: {e}")
            raise

def ensure_admin_privileges():
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

# Detect if running as an EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
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

    with app.app_context():
        init_default_categories()
        check_and_initialize()
    
    # Run Flask in the background
    server_thread = Thread(target=app.run, kwargs={"port": 5000, "debug": False})
    server_thread.daemon = True
    server_thread.start()

    # Replace EdgeChrome with custom class
    webview.platforms.edgechromium.EdgeChrome = CustomEdgeChrome


    # Create WebView window
    window = webview.create_window(
        "User Management App",
        "http://127.0.0.1:5000",
        js_api={},
        confirm_close=False,
    )


    webview.start()
   