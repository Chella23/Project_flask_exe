import os
import platform
import socket
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


import platform

def modify_hosts_file(action, websites_text):
    """
    Modifies the hosts file to block or unblock websites.
    
    Parameters:
        action (str): Either "block" or "unblock".
        websites_text (str): A string containing one or more website URLs, 
                             separated by newlines.
    """
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts' if platform.system() == "Windows" else '/etc/hosts'
    redirect_ip = '127.0.0.1'

    # Extract non-empty, stripped website URLs from the input text.
    websites = [line.strip() for line in websites_text.splitlines() if line.strip()]
    
    try:
        with open(hosts_path, 'r+') as file:
            # Read the existing lines from the hosts file.
            lines = file.readlines()
            file.seek(0)
            
            if action == "block":
                # Create a set of current entries (stripped) to avoid duplicates.
                existing_entries = {line.strip() for line in lines}
                # For each website, create the entry and add it if not already present.
                for website in websites:
                    entry = f"{redirect_ip} {website}"
                    if entry not in existing_entries:
                        lines.append(entry + "\n")
            
            elif action == "unblock":
                # Filter out only the entries corresponding to the websites provided.
                def is_unblock_entry(line):
                    stripped = line.strip()
                    # If the line exactly matches the entry for any of the provided websites, remove it.
                    for website in websites:
                        if stripped == f"{redirect_ip} {website}":
                            return False
                    return True

                lines = [line for line in lines if is_unblock_entry(line)]
            
            # Write back the modified lines to the hosts file.
            file.writelines(lines)
            file.truncate()

        print(f"✅ Hosts file updated successfully for the provided websites.")
        return True

    except PermissionError:
        print(f"❌ Permission error: Run this script as administrator to modify {hosts_path}.")
        return False

    except Exception as e:
        print(f"❌ Error modifying hosts file: {e}")
        return False



def resolve_ipv4(website):
    """
    Resolves a website domain to its IPv4 address.
    Returns the IPv4 address as a string if successful, or None if it fails.
    """
    try:
        # getaddrinfo returns a list of address info for the given host.
        # We filter for AF_INET to get IPv4 addresses.
        addr_info = socket.getaddrinfo(website, None, socket.AF_INET)
        if addr_info:
            ip_address = addr_info[0][4][0]
            return ip_address
    except Exception as e:
        print(f"❌ Unable to resolve {website}: {e}")
    return None

def block_firewall(website):
    """
    Blocks the website at the firewall level.
    
    For Windows, this function creates a firewall rule that blocks outbound traffic 
    to the website's resolved IPv4 address.
    For Linux, an iptables rule is added (requires root privileges).
    For macOS, a placeholder message is shown.
    
    Parameters:
      website (str): The website domain (e.g., "www.example.com")
    
    Returns:
      bool: True if successful, False otherwise.
    """
    system = platform.system()
    try:
        ip_address = resolve_ipv4(website)
        if not ip_address:
            return False

        if system == "Windows":
            rule_name = f"Block_{website}"
            # Create a firewall rule using netsh command with the resolved IPv4 address.
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=out",
                "action=block",
                f"remoteip={ip_address}"
            ]
            subprocess.run(cmd, check=True)
            print(f"✅ Windows Firewall rule added to block {website} ({ip_address}).")
            return True

        elif system == "Linux":
            cmd = ["sudo", "iptables", "-A", "OUTPUT", "-d", ip_address, "-j", "DROP"]
            subprocess.run(cmd, check=True)
            print(f"✅ iptables rule added to block {website} ({ip_address}).")
            return True

        elif system == "Darwin":
            print("⚠️ macOS firewall blocking is not implemented. Consider using pf.")
            return False

        else:
            print("⚠️ Unsupported operating system for firewall blocking.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Error adding firewall rule: {e}")
        return False

def unblock_firewall(website):
    """
    Unblocks the website at the firewall level.
    
    For Windows, this function deletes the firewall rule for the website.
    For Linux, the corresponding iptables rule is removed.
    For macOS, a placeholder message is shown.
    
    Parameters:
      website (str): The website domain (e.g., "www.example.com")
    
    Returns:
      bool: True if successful, False otherwise.
    """
    system = platform.system()
    try:
        ip_address = resolve_ipv4(website)
        if not ip_address:
            return False

        if system == "Windows":
            rule_name = f"Block_{website}"
            cmd = [
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f"name={rule_name}"
            ]
            subprocess.run(cmd, check=True)
            print(f"✅ Windows Firewall rule removed for {website}.")
            return True

        elif system == "Linux":
            cmd = ["sudo", "iptables", "-D", "OUTPUT", "-d", ip_address, "-j", "DROP"]
            subprocess.run(cmd, check=True)
            print(f"✅ iptables rule removed for {website} ({ip_address}).")
            return True

        elif system == "Darwin":
            print("⚠️ macOS firewall unblocking is not implemented. Consider using pf.")
            return False

        else:
            print("⚠️ Unsupported operating system for firewall unblocking.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Error removing firewall rule: {e}")
        return False

def block_website(website_url):
    """
    Blocks a website by adding it to the hosts file and clearing caches.
    """
    success_hosts = modify_hosts_file("block", website_url)
    success_firewall = block_firewall(website_url)
    clear_dns_cache()
    clear_browser_cache()
    terminate_chrome_processes()
    #clear_chrome_dns_cache()

    if success_hosts and success_firewall:
       
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
    success_firewall = block_firewall(website_url)
    clear_dns_cache()
    clear_browser_cache()

    #clear_chrome_dns_cache()

    if success_hosts and success_firewall:

        print(f"✅ Website {website_url} has been successfully unblocked.")
        return True
    else:
        print(f"❌ Failed to unblock {website_url}.")
        return False
