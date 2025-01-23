import ctypes
import os
import platform
import sys
import webview
from app import create_app

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

if __name__ == "__main__":
    app = create_app()
    ensure_admin_privileges()

    # Run the Flask app in the background
    from threading import Thread
    server_thread = Thread(target=app.run, kwargs={"port": 5000, "debug": False})
    server_thread.daemon = True
    server_thread.start()

    # Create PyWebView GUI
    webview.create_window("User Management App", "http://127.0.0.1:5000")
    webview.start()
