import os
import platform
import subprocess
import shutil
import time
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json


def terminate_chrome_processes():
    """
    Terminate all Chrome processes to unlock cache files.
    """
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and "chrome" in proc.info['name'].lower():
                proc.kill()  # Use .kill() for a forceful stop
        print("✅ All Chrome processes terminated successfully.")
    except Exception as e:
        print(f"❌ Error terminating Chrome processes: {e}")


def clear_dns_cache():
    """
    Clears the system DNS cache.
    """
    try:
        if platform.system() == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], check=True)
        elif platform.system() == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=True)
        print("✅ DNS cache cleared successfully.")
    except Exception as e:
        print(f"❌ Error clearing DNS cache: {e}")


def clear_chrome_dns_cache():
    """
    Clears Chrome's DNS cache using Selenium.
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Locate ChromeDriver automatically
        chrome_driver_path = shutil.which("chromedriver")
        if not chrome_driver_path:
            raise FileNotFoundError("⚠️ ChromeDriver not found! Install it or specify its path.")

        service = Service(chrome_driver_path)

        # Initialize WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("chrome://net-internals/#dns")
        time.sleep(2)

        # Click the "Clear host cache" button
        clear_button = driver.find_element(By.XPATH, '//*[@id="dns-view"]/div[2]/button')
        clear_button.click()
        print("✅ Chrome DNS cache cleared successfully.")
        driver.quit()
    except Exception as e:
        print(f"❌ Error clearing Chrome DNS cache: {e}")


def clear_browser_cache():
    """
    Clears Chrome and Firefox cache.
    """
    try:
        user_home = os.path.expanduser("~")
        
        # Define paths for Chrome and Firefox cache
        if platform.system() == "Windows":
            chrome_cache_base = os.path.join(user_home, "AppData", "Local", "Google", "Chrome", "User Data")
            firefox_cache_base = os.path.join(user_home, "AppData", "Local", "Mozilla", "Firefox", "Profiles")
        elif platform.system() == "Darwin":  # macOS
            chrome_cache_base = os.path.join(user_home, "Library", "Caches", "Google", "Chrome")
            firefox_cache_base = os.path.join(user_home, "Library", "Caches", "Firefox", "Profiles")
        else:  # Linux
            chrome_cache_base = os.path.join(user_home, ".cache", "google-chrome")
            firefox_cache_base = os.path.join(user_home, ".cache", "mozilla", "firefox")

        # Possible Chrome cache directories
        chrome_cache_paths = [
            "Default/Cache",
            "Default/Cache2",
            "Default/Network/Cache",
            "Profile 1/Cache",
            "Profile 2/Cache",
            "Profile 3/Cache",
        ]

        # Clear Chrome cache
        for path in chrome_cache_paths:
            full_path = os.path.join(chrome_cache_base, path)
            if os.path.exists(full_path):
                try:
                    shutil.rmtree(full_path)
                    print(f"✅ Chrome cache cleared: {full_path}")
                except PermissionError:
                    print(f"⚠️ Cannot delete some files in: {full_path}. Close Chrome and retry.")

        # Clear Firefox cache
        if os.path.exists(firefox_cache_base):
            for profile in os.listdir(firefox_cache_base):
                profile_cache = os.path.join(firefox_cache_base, profile, "cache2")
                if os.path.exists(profile_cache):
                    try:
                        shutil.rmtree(profile_cache)
                        print(f"✅ Firefox cache cleared for profile: {profile}.")
                    except PermissionError:
                        print(f"⚠️ Cannot delete some files in: {profile_cache}. Close Firefox and retry.")

        print("✅ Browser cache cleared successfully.")
    except Exception as e:
        print(f"❌ Error clearing browser cache: {e}")


def modify_hosts_file(action, website_url):
    """
    Adds or removes a website from the hosts file.
    """
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
    redirect_ip = '127.0.0.1'
    entry = f"{redirect_ip} {website_url}\n"

    try:
        with open(hosts_path, 'r+') as file:
            lines = file.readlines()
            file.seek(0)

            if action == "block":
                if entry not in lines:
                    file.writelines(lines + [entry])
            elif action == "unblock":
                file.writelines(line for line in lines if line.strip() != entry.strip())

            file.truncate()

        print(f"✅ Hosts file updated successfully for {website_url}.")
        return True
    except PermissionError:
        print(f"❌ Permission error: Run this script as administrator to modify {hosts_path}.")
        return False
    except Exception as e:
        print(f"❌ Error modifying hosts file: {e}")
        return False



def on_script_notify(func_param):
    """ Handles script notifications and ensures JSON parsing is safe. """
    try:
        if func_param is None:
            print("⚠️ Received NoneType in on_script_notify. Skipping JSON parsing.")
            return  # Prevents the error

        func_param = json.loads(func_param)  # Safely parse JSON
        print("✅ Successfully parsed JSON:", func_param)

    except json.JSONDecodeError:
        print("❌ JSON parsing error. Invalid format:", func_param)
    except Exception as e:
        print(f"❌ Unexpected error in on_script_notify: {e}")



def block_website(website_url):
    """
    Blocks a website by adding it to the hosts file and clearing caches.
    """
    success_hosts = modify_hosts_file("block", website_url)
    clear_dns_cache()
    clear_browser_cache()
    terminate_chrome_processes()
    #clear_chrome_dns_cache()

    if success_hosts:
        print(f"✅ Website {website_url} has been successfully blocked.")
        return True
    else:
        print(f"❌ Failed to block {website_url}.")
        return False


def unblock_website(website_url):
    """
    Unblocks a website by removing it from the hosts file and clearing caches.
    """
    success_hosts = modify_hosts_file("unblock", website_url)
    clear_dns_cache()
    clear_browser_cache()

    #clear_chrome_dns_cache()

    if success_hosts:
        print(f"✅ Website {website_url} has been successfully unblocked.")
        return True
    else:
        print(f"❌ Failed to unblock {website_url}.")
        return False
