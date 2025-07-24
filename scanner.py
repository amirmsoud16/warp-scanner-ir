"""
Warp Anycast IP & Port Scanner
============================

A professional tool to find the best IP and port for Warp (Cloudflare) with low ping and closest geographic location to your internet.

Features:
- Scans a list of IPs and ports to find the best (lowest ping) endpoint.
- Generates a ready-to-use Hiddify/Sing-box (Warp) JSON config for the best IP.

Usage:
    python3 scanner.py

Requirements:
    - Python 3.6 or newer
    - requests
    - urllib3 (usually installed with requests)
    - ping3 (optional, for real ICMP ping)

Install requirements:
    pip install requests urllib3 ping3

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

# اطمینان از وجود $HOME/bin در PATH برای اجرای wgcf
home_bin = os.path.join(os.environ.get('HOME', ''), 'bin')
if home_bin and home_bin not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{home_bin}:{os.environ.get('PATH', '')}"

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

# افزودن گزینه به منو

def main_menu():
    while True:
        clear_screen()
        print_boxed([
            " WARP SCANNER MENU ",
            "1. Scan IPv4",
            "2. Scan IPv6",
            "0. Exit"
        ])
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            do_scan(IPV4_FILE)
        elif choice == "2":
            do_scan(IPV6_FILE)
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

# Remove show_wireguard_config, show_saved_configs, get_wgcf_private_key_and_config, and all config file handling logic

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

# ویرایش do_scan:
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
    n_ip = 20  # تعداد IPهایی که تست می‌شوند
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
        answer = input("Do you want to generate a Hiddify config for the best IP? [y/N]: ").strip().lower()
        if answer in ["y", "yes", "1"]:
            def get_hiddify_keys():
                import urllib.request, requests, re
                try:
                    output = urllib.request.urlopen("https://api.zeroteam.top/warp?format=sing-box", timeout=30).read().decode('utf-8')
                except Exception:
                    output = requests.get("https://api.zeroteam.top/warp?format=sing-box", timeout=30).text
                Address_pattern = r'"2606:4700:[0-9a-f:]+/128"'
                private_key_pattern = r'"private_key":"[0-9a-zA-Z/+]+="'
                reserved_pattern = r'"reserved":\[[0-9]+(,[0-9]+){2}\]'
                Address_search = re.search(Address_pattern, output)
                private_key_search = re.search(private_key_pattern, output)
                reserved_search = re.search(reserved_pattern, output)
                Address_key = Address_search.group(0).replace('"', '') if Address_search else None
                private_key = private_key_search.group(0).split(':')[1].replace('"', '') if private_key_search else None
                reserved = reserved_search.group(0).replace('"reserved":', '').replace('"', '') if reserved_search else None
                return Address_key, private_key, reserved
            Address_key, private_key, reserved = get_hiddify_keys()
            public_key = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="
            warp_json = {
                "outbounds": [
                    {
                        "protocol": "wireguard",
                        "settings": {
                            "address": [
                                "172.16.0.2/32",
                                Address_key
                            ],
                            "mtu": 1280,
                            "peers": [
                                {
                                    "endpoint": f"{best['ip']}:{best['best']['port']}",
                                    "publicKey": public_key
                                }
                            ],
                            "reserved": eval(reserved) if reserved else [0,0,0],
                            "secretKey": private_key
                        },
                        "tag": "warp"
                    },
                    {"protocol": "dns", "tag": "dns-out"},
                    {"protocol": "freedom", "settings": {}, "tag": "direct"},
                    {"protocol": "blackhole", "settings": {"response": {"type": "http"}}, "tag": "block"}
                ],
                "policy": {
                    "levels": {
                        "8": {
                            "connIdle": 300,
                            "downlinkOnly": 1,
                            "handshake": 4,
                            "uplinkOnly": 1
                        }
                    },
                    "system": {
                        "statsOutboundUplink": True,
                        "statsOutboundDownlink": True
                    }
                },
                "remarks": "hydra",
                "routing": {
                    "domainStrategy": "IPIfNonMatch",
                    "rules": [
                        {
                            "network": "tcp,udp",
                            "outboundTag": "warp",
                            "type": "field"
                        }
                    ]
                },
                "stats": {}
            }
            import json, sys, os
            config_text = json.dumps(warp_json, indent=2, ensure_ascii=False)
            print_boxed(["==== Hiddify/Sing-box Warp JSON Config (Best Ping) ===="])
            print(config_text)
            # Save config as .txt
            is_termux = 'com.termux' in sys.executable or 'termux' in sys.executable or 'ANDROID_STORAGE' in os.environ
            if is_termux:
                # Android/Termux: save to Downloads
                save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'storage', 'downloads')
                if not os.path.isdir(save_dir):
                    save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'downloads')
                os.makedirs(save_dir, exist_ok=True)
                file_path = os.path.join(save_dir, 'warp_hiddify_config.txt')
            else:
                # Linux: save to WARPS folder
                warps_dir = os.path.expanduser('~/WARPS')
                os.makedirs(warps_dir, exist_ok=True)
                file_path = os.path.join(warps_dir, 'warp_hiddify_config.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(config_text)
            print_boxed([f"Config saved as {file_path}"])
            input("Press Enter to return to menu...")
        else:
            print_boxed(["Config generation skipped by user."])
            input("Press Enter to return to menu...")
    else:
        print_boxed(["No suitable IP found."])

if icmp_ping is None:
    print_boxed(["[!] For real ICMP ping, please install ping3:", "pip install ping3"])

def main():
    main_menu()

if __name__ == '__main__':
    main() 
