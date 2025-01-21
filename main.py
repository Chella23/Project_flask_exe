import webview
from app import create_app

if __name__ == "__main__":
    app = create_app()

    # Run the Flask app in the background
    from threading import Thread
    server_thread = Thread(target=app.run, kwargs={"port": 5000, "debug": False})
    server_thread.daemon = True
    server_thread.start()

    # Create PyWebView GUI
    webview.create_window("User Management App", "http://127.0.0.1:5000")
    webview.start()
