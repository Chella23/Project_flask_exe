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
import re



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


import re
import subprocess
import platform
import socket

def resolve_ips(website):
    """
    Resolves a website's IPv4 and IPv6 addresses using nslookup with Google's public DNS (8.8.8.8).
    Returns a list of unique public IP addresses.
    """
    try:
        result = subprocess.run(
            ["nslookup", website],  # Use system's default resolver
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        output = result.stdout

        # Regex for IPv4 and IPv6 addresses
        ipv4_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        ipv6_pattern = r'([a-fA-F0-9:]+:[a-fA-F0-9:]+)'

        ipv4_matches = re.findall(ipv4_pattern, output)
        ipv6_matches = re.findall(ipv6_pattern, output)

        # Remove duplicates and filter out private/local network IPs
        all_ips = list(dict.fromkeys(ipv4_matches + ipv6_matches))
        public_ips = [ip for ip in all_ips if not is_private_ip(ip)]

        if public_ips:
            return public_ips
        else:
            print(f"\u274C No public IP addresses found for {website}.")
            return None

    except Exception as e:
        print(f"\u274C Error resolving {website} with nslookup: {e}")
        return None

def is_private_ip(ip):
    """
    Checks if the given IP is private (local network) or public.
    Ensures we don't block local connections.
    """
    try:
        socket.inet_pton(socket.AF_INET, ip)  # Check IPv4
        private_ranges = ["10.", "172.16.", "192.168.", "127.", "169.254."]
        return any(ip.startswith(prefix) for prefix in private_ranges)
    except OSError:
        pass  # If not IPv4, continue to IPv6

    try:
        socket.inet_pton(socket.AF_INET6, ip)  # Check IPv6
        return ip.startswith(("fe80:", "fc00:", "fd00:", "::1"))  # Link-local or loopback
    except OSError:
        return False

def block_firewall(websites):
    """
    Blocks each website by creating a single firewall rule per website.
    All resolved IPs for the website are grouped under one rule.
    """
    system = platform.system()
    websites_list = [w.strip() for w in websites.replace(",", "\n").splitlines() if w.strip()]
    success = True

    for website in websites_list:
        ips = resolve_ips(website)
        if not ips:
            success = False
            continue

        if system == "Windows":
            rule_name = f"Block_{website}"
            remote_ips = ",".join(ips)  # All IPs in one rule

            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=out",
                "action=block",
                f"remoteip={remote_ips}"
            ]
            try:
                subprocess.run(cmd, check=True)
                print(f"\u2705 Windows Firewall rule added for {website} with IPs: {remote_ips}")
            except subprocess.CalledProcessError as e:
                print(f"\u274C Error adding firewall rule for {website}: {e}")
                success = False

        elif system == "Linux":
            for ip in ips:
                cmd = ["sudo", "iptables", "-A", "OUTPUT", "-d", ip, "-j", "DROP"]
                try:
                    subprocess.run(cmd, check=True)
                    print(f"\u2705 iptables rule added for {website} with IP: {ip}")
                except subprocess.CalledProcessError as e:
                    print(f"\u274C Error adding iptables rule for {website}: {e}")
                    success = False

        elif system == "Darwin":
            print("\u26A0\uFE0F macOS firewall blocking is not implemented. Consider using pf.")
            success = False

        else:
            print("\u26A0\uFE0F Unsupported operating system for firewall blocking.")
            success = False

    return success


def unblock_firewall(websites):
    """
    Unblocks each website by removing its corresponding firewall rule.
    """
    system = platform.system()
    websites_list = [w.strip() for w in websites.replace(",", "\n").splitlines() if w.strip()]
    success = True

    for website in websites_list:
        if system == "Windows":
            rule_name = f"Block_{website}"
            cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
            try:
                subprocess.run(cmd, check=True)
                print(f"✅ Windows Firewall rule removed for {website}.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error removing firewall rule for {website}: {e}")
                success = False

        elif system == "Linux":
            try:
                # Check for existing rules before deleting
                result = subprocess.run(
                    ["sudo", "iptables", "-L", "OUTPUT", "-n"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                output = result.stdout

                # Extract blocked IPs
                pattern = rf"DROP\s+all\s+\-\-\s+.+\s+(\d+\.\d+\.\d+\.\d+)"
                blocked_ips = re.findall(pattern, output)

                if not blocked_ips:
                    print(f"⚠️ No iptables rules found for {website}.")
                    continue

                # Remove only the rules that were previously added
                for ip in blocked_ips:
                    cmd = ["sudo", "iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"]
                    subprocess.run(cmd, check=True)
                    print(f"✅ iptables rule removed for {website} ({ip}).")

            except subprocess.CalledProcessError as e:
                print(f"❌ Error removing iptables rules for {website}: {e}")
                success = False

        elif system == "Darwin":
            print("⚠️ macOS firewall unblocking is not implemented. Consider using pf.")
            success = False

        else:
            print("⚠️ Unsupported operating system for firewall unblocking.")
            success = False

    return success

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



def block_website(website_url):
    """
    Blocks a website by adding it to the hosts file and clearing caches.
    """
    success_firewall = block_firewall(website_url)
    success_hosts = modify_hosts_file("block", website_url)
    
    clear_dns_cache()
    clear_browser_cache()
 
    #clear_chrome_dns_cache()

    if success_firewall  and success_hosts:
       
        print(f"✅ Website {website_url} has been successfully blocked.")
        return True
    else:
        print(f"❌ Failed to block {website_url}.")
        return False


def unblock_website(website_url):
    """
    Unblocks a website by removing it from the hosts file and clearing caches.
    """
    success_firewall = unblock_firewall(website_url)
    success_hosts = modify_hosts_file("unblock", website_url)
    
    clear_dns_cache()
    clear_browser_cache()

    #clear_chrome_dns_cache()

    if success_firewall  and success_hosts:

        print(f"✅ Website {website_url} has been successfully unblocked.")
        return True
    else:
        print(f"❌ Failed to unblock {website_url}.")
        return False
