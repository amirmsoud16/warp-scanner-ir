"""
Warp Anycast IP & Port Scanner
=============================

A professional tool to find the best IP and port for Warp (Cloudflare) with low ping and closest geographic location to your internet.

Usage:
    python3 scanner.py

Requirements:
    pip install requests

"""

import ipaddress
import random
import socket
import time
import concurrent.futures
import requests
import sys
import base64
import secrets
import threading
import itertools
import os

try:
    from ping3 import ping as icmp_ping
except ImportError:
    icmp_ping = None

# Settings
IPV4_FILE = 'ips-v4.txt'
IPV6_FILE = 'ips-v6.txt'
PORTS_MAIN = [(2408, 'udp'), (443, 'tcp'), (443, 'udp')]
PORTS_RANDOM_COUNT = 500
PORT_RANGE = (1000, 60000)
IPS_PER_RANGE = 100
TIMEOUT = 0.4
MAX_WORKERS = 150
GEOIP_URL = 'https://ipinfo.io/{ip}/json'

# --- Display Tools ---
def print_boxed(text_lines):
    width = max(len(line) for line in text_lines) + 4
    print("\n" + "┌" + "─" * (width - 2) + "┐")
    for line in text_lines:
        print("│ " + line.ljust(width - 3) + "│")
    print("└" + "─" * (width - 2) + "┘\n")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    while True:
        clear_screen()
        print_boxed([
            " WARP SCANNER MENU ",
            "1. Scan IPv4",
            "2. Scan IPv6",
            "3. Show saved configs",
            "0. Exit"
        ])
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            do_scan(IPV4_FILE)
        elif choice == "2":
            do_scan(IPV6_FILE)
        elif choice == "3":
            show_saved_configs()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Press Enter...")
            input()

# --- GeoIP ---
def get_my_location():
    try:
        r = requests.get('http://ip-api.com/json/', timeout=5)
        data = r.json()
        return {
            'ip': data.get('query', ''),
            'country': data.get('country', ''),
            'city': data.get('city', '')
        }
    except Exception:
        return {'ip': '', 'country': '', 'city': ''}

def geoip_lookup(ip):
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
        if r.status_code == 200:
            data = r.json()
            return data.get('country', ''), data.get('city', ''), data.get('org', '')
    except Exception:
        pass
    return '', '', ''

# --- IP/Port Test ---
def load_cidr_list(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def random_ip_from_cidr(cidr):
    net = ipaddress.ip_network(cidr, strict=False)
    if net.num_addresses < 4:
        return str(net.network_address)
    if isinstance(net, ipaddress.IPv4Network):
        hosts = list(net.hosts())
        return str(random.choice(hosts))
    else:
        return str(random.choice(list(net.hosts())))

def random_ports(count, exclude_ports=None):
    exclude_ports = exclude_ports or set()
    ports = set()
    while len(ports) < count:
        p = random.randint(*PORT_RANGE)
        if p not in exclude_ports:
            ports.add(p)
    return list(ports)

def ping_tcp(ip, port, timeout=TIMEOUT):
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        latency = (time.time() - start) * 1000
        return True, latency
    except Exception:
        return False, None

def ping_udp(ip, port, timeout=TIMEOUT):
    try:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(b'\x00', (ip, port))
        latency = (time.time() - start) * 1000
        s.close()
        return True, latency
    except Exception:
        return False, None

def test_ip_ports_optimized(ip, main_ports, random_ports):
    # ابتدا پورت‌های اصلی
    results = []
    open_ports = []
    for port, proto in main_ports:
        if proto == 'tcp':
            ok, latency = ping_tcp(ip, port)
        else:
            ok, latency = ping_udp(ip, port)
        results.append({'port': port, 'proto': proto, 'ok': ok, 'latency': latency})
        if ok:
            open_ports.append({'port': port, 'proto': proto, 'latency': latency})
    # اگر هیچ پورت اصلی باز نبود، پورت‌های رندوم را تست کن
    if not open_ports:
        for port, proto in random_ports:
            if proto == 'tcp':
                ok, latency = ping_tcp(ip, port)
            else:
                ok, latency = ping_udp(ip, port)
            results.append({'port': port, 'proto': proto, 'ok': ok, 'latency': latency})
            if ok:
                open_ports.append({'port': port, 'proto': proto, 'latency': latency})
    if not open_ports:
        return None, results
    best = min(open_ports, key=lambda x: x['latency'] if x['latency'] else 9999)
    return best, results

def real_icmp_ping(ip, timeout=TIMEOUT):
    if icmp_ping is None:
        return None
    try:
        latency = icmp_ping(ip, timeout=timeout)
        if latency is not None:
            return latency * 1000  # ms
        else:
            return None
    except Exception:
        return None

def scan_ip_optimized(ip, n_random_ports):
    main_ports = [(2408, 'udp'), (443, 'tcp'), (443, 'udp')]
    random_ports = [(p, random.choice(['tcp', 'udp'])) for p in random.sample(range(1000, 60000), n_random_ports)]
    best, port_results = test_ip_ports_optimized(ip, main_ports, random_ports)
    icmp_latency = real_icmp_ping(ip)
    country, city, org = geoip_lookup(ip)
    return {
        'ip': ip,
        'best': best,
        'icmp_latency': icmp_latency,
        'country': country,
        'city': city,
        # سایر فیلدها در صورت نیاز
    }

def test_download_speed(ip, port):
    try:
        url = f'http://{ip}:{port}/speedtest/random4000x4000.jpg'  # Example URL, might need adjustment
        start = time.time()
        r = requests.get(url, timeout=3, stream=True)
        total = 0
        for chunk in r.iter_content(1024):
            total += len(chunk)
            if total > 1.5 * 1024 * 1024:  # Download only 1.5MB
                break
        elapsed = time.time() - start
        if elapsed == 0:
            return 'N/A'
        speed_mbps = (total * 8) / (elapsed * 1_000_000)
        return f'{speed_mbps:.2f} Mbps'
    except Exception:
        return 'N/A'

def show_results_boxed(results, show_download=False):
    clear_screen()
    COLORS = ['\033[92m', '\033[93m', '\033[94m', '\033[91m', '\033[95m', '\033[96m', '\033[90m']
    RESET = '\033[0m'
    lines = ["--- Best IPs (sorted by ICMP Ping) ---"]
    for idx, b in enumerate(results):
        icmp_lat = b.get('icmp_latency')
        icmp_str = f"{icmp_lat:.0f} ms" if icmp_lat else "N/A"
        line = f"{b['ip']}:{b['best']['port']} {b['best']['proto']} | {b['country']} {b['city']} | ICMP Ping: {icmp_str}"
        color = COLORS[idx % len(COLORS)]
        lines.append(f"{color}{line}{RESET}")
    print_boxed(lines)

def ask_wireguard_config(ip, port):
    print_boxed([f"Do you want a WireGuard config for this IP?", f"{ip}:{port}", "1. Yes", "2. No"])
    while True:
        ans = input("Your choice: ").strip()
        if ans in ["1", "2"]:
            return ans == "1"

def generate_private_key():
    # Generate 32-byte private key and convert to base64 (compatible with WireGuard)
    key = secrets.token_bytes(32)
    return base64.b64encode(key).decode()

def show_wireguard_config(ip, port):
    import base64
    public_key = '...'  # می‌توانید کلید پابلیک Warp را اینجا قرار دهید
    endpoint = f'{ip}:{port}'
    config = f'''[Interface]\nPrivateKey = {generate_private_key()}\nAddress = 172.16.0.2/32, 2606:4700:110:8765::2/128\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = {public_key}\nAllowedIPs = 0.0.0.0/0, ::/0\nEndpoint = {endpoint}\nPersistentKeepalive = 25'''
    config_b64 = base64.urlsafe_b64encode(config.encode()).decode()
    wg_uri = f'wg://{config_b64}'
    v2rayn_uri = f'wgcf://{config_b64}'
    print("\033[96m==== WireGuard Config ====" + "\033[0m")
    print(config)
    print("\n\033[92m==== wg:// URI ====" + "\033[0m")
    print(wg_uri)
    print("\n\033[93m==== wgcf:// (for v2rayN) ====" + "\033[0m")
    print(v2rayn_uri)
    # ذخیره کانفیک
    saved_name = None
    while True:
        name = input("Enter a name to save this config (or leave empty to skip): ").strip()
        if name == "":
            break
        os.makedirs("configs", exist_ok=True)
        filename = os.path.join("configs", f"{name}.conf")
        if os.path.exists(filename):
            print("A config with this name already exists. Choose another name.")
            continue
        with open(filename, "w") as f:
            f.write(config)
        print(f"Config saved as configs/{name}.conf")
        saved_name = name
        break
    # پس از ذخیره، منوی مشاهده کانفیک
    if saved_name:
        while True:
            see = input("Do you want to view a config? [y/n]: ").strip().lower()
            if see in ["y", "yes"]:
                show_saved_configs(view_only=True)
                break
            elif see in ["n", "no", ""]:
                break
            else:
                print("Please enter y or n.")
    print("\nPress Enter to return to menu...")
    input()

def show_saved_configs(view_only=False):
    clear_screen()
    print_boxed(["Saved WireGuard Configs"])
    configs_dir = "configs"
    if not os.path.isdir(configs_dir):
        print("No configs found.")
        print("\nPress Enter to return to menu...")
        input()
        return
    files = [f for f in os.listdir(configs_dir) if f.endswith(".conf")]
    if not files:
        print("No configs found.")
        print("\nPress Enter to return to menu...")
        input()
        return
    for idx, fname in enumerate(files, 1):
        print(f"{idx}- {os.path.splitext(fname)[0]}")
    if view_only:
        try:
            num = int(input("Enter config number to view: ").strip())
            if 1 <= num <= len(files):
                with open(os.path.join(configs_dir, files[num-1]), "r") as f:
                    print("\n\033[96m==== Config Content ====" + "\033[0m")
                    print(f.read())
            else:
                print("Invalid number.")
        except Exception:
            print("Invalid input.")
        print("\nPress Enter to return to menu...")
        input()
        return
    # منوی کوچک برای مشاهده/حذف/خروج
    while True:
        print("\n[1] View config\n[2] Delete config\n[0] Exit")
        action = input("Enter your choice: ").strip()
        if action == "1":
            try:
                num = int(input("Enter config number to view: ").strip())
                if 1 <= num <= len(files):
                    with open(os.path.join(configs_dir, files[num-1]), "r") as f:
                        print("\n\033[96m==== Config Content ====" + "\033[0m")
                        print(f.read())
                else:
                    print("Invalid number.")
            except Exception:
                print("Invalid input.")
            print("\nPress Enter to return to menu...")
            input()
        elif action == "2":
            try:
                num = int(input("Enter config number to delete: ").strip())
                if 1 <= num <= len(files):
                    os.remove(os.path.join(configs_dir, files[num-1]))
                    print("Config deleted.")
                    files = [f for f in os.listdir(configs_dir) if f.endswith(".conf")]
                    for idx, fname in enumerate(files, 1):
                        print(f"{idx}- {os.path.splitext(fname)[0]}")
                else:
                    print("Invalid number.")
            except Exception:
                print("Invalid input.")
            print("\nPress Enter to return to menu...")
            input()
        elif action == "0":
            break
        else:
            print("Invalid choice.")

def print_progress(current, total, message="Progress"):
    percent = int((current / total) * 100) if total else 100
    bar = ('#' * (percent // 2)).ljust(50)
    sys.stdout.write(f"\r{message}: [{bar}] {percent}% ({current}/{total})")
    sys.stdout.flush()
    if current == total:
        print()

class Spinner:
    def __init__(self, message="Loading..."):
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])
        self.stop_running = False
        self.message = message
        self.thread = threading.Thread(target=self.run)

    def run(self):
        while not self.stop_running:
            sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')

    def start(self):
        self.stop_running = False
        self.thread.start()

    def stop(self):
        self.stop_running = True
        self.thread.join()

# تغییر در do_scan برای استفاده از اولین پورت باز

def do_scan(filename):
    cidrs = load_cidr_list(filename)
    all_ips = []
    total_cidrs = len(cidrs)
    for idx, cidr in enumerate(cidrs, 1):
        net = ipaddress.ip_network(cidr, strict=False)
        for ip in net.hosts():
            all_ips.append(str(ip))
        print_progress(idx, total_cidrs, "Building IP list")
    sys.stdout.write("\n")
    print_boxed([f"Total available IPs: {len(all_ips)}"])
    n_ip = 100  # تعداد IPهایی که تست می‌شوند
    selected_ips = random.sample(all_ips, n_ip)
    print(f'Total IPs to scan: {len(selected_ips)}')
    results = []
    total = len(selected_ips)
    for idx, ip in enumerate(selected_ips, 1):
        res = scan_ip_optimized(ip, 0)  # فقط پورت‌های اصلی
        if res['best']:
            results.append(res)
        print_progress(idx, total, "Scanning IPs and ports")
    # مرتب‌سازی بر اساس کمترین ICMP Ping
    results_sorted = sorted(
        (b for b in results if b['best'] and b.get('icmp_latency') and b['icmp_latency'] > 0),
        key=lambda x: x['icmp_latency']
    )
    show_results_boxed(results_sorted[:10], show_download=False)
    if results_sorted:
        best = results_sorted[0]
        while True:
            ans = input(f"Do you want WireGuard config with {best['ip']}:{best['best']['port']} (Best Ping)? [Y/n]: ").strip().lower()
            if ans in ["", "y", "yes"]:
                show_wireguard_config(best['ip'], best['best']['port'])
                break
            elif ans in ["n", "no"]:
                break
            else:
                print("Please enter Y or N.")
    else:
        print_boxed(["No suitable IP found."])

if icmp_ping is None:
    print_boxed(["[!] For real ICMP ping, please install ping3:", "pip install ping3"])

def main():
    while True:
        choice = main_menu()
        if choice == '0':
            clear_screen()
            print_boxed(["Exiting. Good luck!"])
            break
        elif choice in ['1', '2']:
            clear_screen()
            my_country, my_city, my_ip = get_my_location()
            print_boxed([f"Your Internet Location:", f"Country: {my_country}", f"City: {my_city}", f"IP: {my_ip}"])
            start = input("Start scanning? [Y/n]: ").strip().lower()
            if start not in ["", "y", "yes"]:
                continue
            clear_screen()
            filename = IPV4_FILE if choice == '1' else IPV6_FILE
            do_scan(filename)

if __name__ == '__main__':
    main() 
