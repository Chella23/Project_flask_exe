import os
import platform
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

def clear_dns_cache():

    #Clear the DNS cache to ensure immediate blocking.

    try:
        if platform.system() == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], check=True)
        elif platform.system() == "Linux":
            subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=True)
        elif platform.system() == "Darwin":
            subprocess.run(["sudo", "dscacheutil", "-flushcache"], check=True)
        print("DNS cache cleared successfully.")
    except Exception as e:
        print(f"Error clearing DNS cache: {e}")


def resolve_domain_to_ip(domain):
   
   # Resolve a domain name to its corresponding IP address.
 
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        print(f"Error: Could not resolve the domain {domain} to an IP address.")
        return None


def modify_hosts_file(action, website_url):
  
 #   Add or remove the website from the hosts file for blocking/unblocking.
 
    hosts_path = '/etc/hosts' if platform.system() != 'Windows' else r'C:\Windows\System32\drivers\etc\hosts'
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
        return True
    except Exception as e:
        print(f"Error modifying hosts file: {e}")
        return False



def configure_firewall(action, website_url):
    
 #   Block or unblock the website at the firewall level.
  
    try:
        if platform.system() == "Windows":
            ip_address = resolve_domain_to_ip(website_url)
            if not ip_address:
                return False

            rule_name = f"Block {website_url}"
            cmd = (
                f"netsh advfirewall firewall add rule name=\"{rule_name}\" dir=out action=block remoteip={ip_address}"
                if action == "block"
                else f"netsh advfirewall firewall delete rule name=\"{rule_name}\""
            )
            subprocess.run(cmd, shell=True, check=True)
        else:
            if action == "block":
                subprocess.run(['iptables', '-A', 'OUTPUT', '-p', 'tcp', '-d', website_url, '-j', 'DROP'], check=True)
            elif action == "unblock":
                subprocess.run(['iptables', '-D', 'OUTPUT', '-p', 'tcp', '-d', website_url, '-j', 'DROP'], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error configuring firewall: {e}")
        return False








def configure_dns_filtering(action, website_url):

   # Use DNS filtering to block/unblock a website.

    try:
        if platform.system() == "Windows":
            print("DNS filtering on Windows is not implemented yet.")
            return False
        else:
            dnsmasq_config = '/etc/dnsmasq.conf'
            entry = f"address=/{website_url}/127.0.0.1\n"

            with open(dnsmasq_config, 'a' if action == "block" else 'r+') as file:
                lines = file.readlines()
                if action == "block" and entry not in lines:
                    file.write(entry)
                elif action == "unblock":
                    file.seek(0)
                    file.writelines(line for line in lines if line.strip() != entry.strip())
            subprocess.run(['systemctl', 'restart', 'dnsmasq'], check=True)
        return True
    except Exception as e:
        print(f"Error configuring DNS filtering: {e}")
        return False


def configure_proxy_server(action, website_url):
  
    #Use a proxy server for blocking/unblocking websites.
  
    try:
        proxy_config_path = '/etc/squid/squid.conf' if platform.system() != 'Windows' else 'C:\\squid\\etc\\squid.conf'
        block_entry = f"acl blocked_sites dstdomain {website_url}\nhttp_access deny blocked_sites\n"

        if not os.path.exists(proxy_config_path):
            print(f"Error: Proxy configuration file {proxy_config_path} not found.")
            return False

        with open(proxy_config_path, 'a' if action == "block" else 'r+') as file:
            lines = file.readlines()
            if action == "block" and block_entry not in lines:
                file.write(block_entry)
            elif action == "unblock":
                file.seek(0)
                file.writelines(line for line in lines if block_entry not in line)

        subprocess.run(['systemctl', 'restart', 'squid'], check=True)
        return True
    except Exception as e:
        print(f"Error configuring proxy server: {e}")
        return False


def middleware_blocking(action, website_url):
    """
    Block website at middleware level using a custom HTTP server or proxy.
    """
    if action == "block":
        try:
            class BlockHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Access to this site is blocked.")

            server = HTTPServer(('127.0.0.1',8080), BlockHandler)
            print(f"Middleware blocking {website_url} at port 8080.")
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping middleware blocking.")
            return False
    else:
        print("Stopping middleware blocking is manual for this demonstration.")
        return True

def block_website(website_url):
    """
    Block a website at multiple levels (hosts file, firewall, middleware, proxy, and DNS filtering).
    """
    success_hosts = modify_hosts_file("block", website_url)
    success_firewall = configure_firewall("block", website_url)
    success_dns = configure_dns_filtering("block", website_url)
    success_proxy = configure_proxy_server("block", website_url)
    middleware_blocking("block", website_url)

    if success_hosts and success_firewall and success_dns and success_proxy:
        print(f"Website {website_url} has been successfully blocked.")
        return True
    else:
        print(f"Failed to block the website {website_url}.")
        return False


def unblock_website(website_url):
    """
    Unblock a website at multiple levels (hosts file, firewall, middleware, proxy, and DNS filtering).
    """
    success_hosts = modify_hosts_file("unblock", website_url)
    success_firewall = configure_firewall("unblock", website_url)
    success_dns = configure_dns_filtering("unblock", website_url)
    success_proxy = configure_proxy_server("unblock", website_url)

    if success_hosts and success_firewall and success_dns and success_proxy:
        print(f"Website {website_url} has been successfully unblocked.")
        return True
    else:
        print(f"Failed to unblock the website {website_url}.")
        return False