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
    clear_screen()
    menu_lines = [
        "   Warp Anycast IP Scanner   ",
        "============================",
        " 1. Scan Warp IPv4 IPs",
        " 2. Scan Warp IPv6 IPs",
        " 0. Exit"
    ]
    print_boxed(menu_lines)
    while True:
        choice = input('Your choice: ').strip()
        if choice in ['1', '2', '0']:
            return choice

# --- GeoIP ---
def get_my_location():
    try:
        r = requests.get('http://ip-api.com/json/', timeout=3)
        if r.status_code == 200:
            data = r.json()
            return data.get('country', ''), data.get('city', ''), data.get('query', '')
    except Exception:
        pass
    return '', '', ''

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
    best, results = test_ip_ports_optimized(ip, main_ports, random_ports)
    country, city, org = geoip_lookup(ip)
    icmp_latency = real_icmp_ping(ip)
    return {
        'ip': ip,
        'results': results,
        'best': best,
        'country': country,
        'city': city,
        'org': org,
        'icmp_latency': icmp_latency
    }

def show_results_boxed(results):
    clear_screen()
    COLORS = ['\033[92m', '\033[93m', '\033[94m', '\033[91m', '\033[95m', '\033[96m', '\033[90m']
    RESET = '\033[0m'
    # مرتب‌سازی بر اساس کمترین ICMP Ping
    results_sorted = sorted(
        (b for b in results if b['best'] and b.get('icmp_latency')),
        key=lambda x: x['icmp_latency']
    )
    lines = ["--- Best IPs (sorted by ICMP Ping) ---"]
    for idx, b in enumerate(results_sorted[:10]):
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
    warp_pubkey = "m+ZkK4G8C3yUeJ8V+RaHcRUW2KIiMzZk1K+1vF3yXwE="
    private_key = generate_private_key()
    address = "172.16.0.2/32"
    dns = "1.1.1.1"
    allowed_ips = "0.0.0.0/0, ::/0"
    keepalive = "25"
    config = [
        "[Interface]",
        f"PrivateKey = {private_key}",
        f"Address = {address}",
        f"DNS = {dns}",
        "",
        "[Peer]",
        f"PublicKey = {warp_pubkey}",
        f"AllowedIPs = {allowed_ips}",
        f"Endpoint = {ip}:{port}",
        f"PersistentKeepalive = {keepalive}"
    ]
    uri = (
        f"wg://{warp_pubkey}@{ip}:{port}?privatekey={private_key}"
        f"&address={address}&dns={dns}&allowedips={allowed_ips.replace(' ', '')}&persistentkeepalive={keepalive}"
    )
    clear_screen()
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    # ساخت باکس زیبا
    box_width = max(len(line) for line in config + [uri]) + 8
    print(f"{CYAN}{'┌' + '─' * (box_width - 2) + '┐'}{RESET}")
    print(f"{GREEN}│{' WireGuard Config '.center(box_width - 2)}│{RESET}")
    print(f"{CYAN}{'├' + '─' * (box_width - 2) + '┤'}{RESET}")
    for line in config:
        print(f"{GREEN}│ {line.ljust(box_width - 4)} │{RESET}")
    print(f"{CYAN}{'├' + '─' * (box_width - 2) + '┤'}{RESET}")
    print(f"{YELLOW}│{' wg:// link: '.ljust(box_width - 2)}│{RESET}")
    print(f"{YELLOW}│ {uri.ljust(box_width - 4)} │{RESET}")
    print(f"{CYAN}{'└' + '─' * (box_width - 2) + '┘'}{RESET}")
    input("Press Enter to exit...")
    clear_screen()

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

def do_scan(filename, my_country):
    cidrs = load_cidr_list(filename)
    all_ips = []
    for cidr in cidrs:
        net = ipaddress.ip_network(cidr, strict=False)
        for ip in net.hosts():
            all_ips.append(str(ip))
    total_ips = len(all_ips)
    print_boxed([f"Total available IPs: {total_ips}"])
    n_ip = 100
    while True:
        print("Which ports to test?")
        print("  [1] Main ports (2408/UDP, 443/TCP/UDP)")
        print("  [2] 100 random ports (900-10000)")
        port_mode = input("Enter your choice [1/2]: ").strip()
        if port_mode in ["1", "main", "m", ""]:
            use_random_ports = False
            break
        elif port_mode in ["2", "random", "r"]:
            use_random_ports = True
            break
        else:
            print("Please enter 1 for main or 2 for random.")
    selected_ips = random.sample(all_ips, n_ip)
    print(f'Total IPs to scan: {len(selected_ips)}')
    results = []
    total = len(selected_ips)
    for idx, ip in enumerate(selected_ips, 1):
        if use_random_ports:
            res = scan_ip_random_ports(ip, 100)
        else:
            res = scan_ip_optimized(ip, 0)
        if res['best']:
            results.append(res)
        print_progress(idx, total, "Scanning IPs and ports")
    bests = sorted((r for r in results if r['best']), key=lambda x: x['best']['latency'])[:10]
    show_results_boxed(bests)
    if bests:
        if ask_wireguard_config(bests[0]['ip'], bests[0]['best']['port']):
            show_wireguard_config(bests[0]['ip'], bests[0]['best']['port'])
        else:
            print_boxed(["Config not generated."])
    else:
        print_boxed(["No suitable IP found."])

def scan_ip_random_ports(ip, n_random_ports):
    random_ports = [(p, random.choice(['tcp', 'udp'])) for p in random.sample(range(900, 10001), n_random_ports)]
    best, results = test_ip_ports_optimized(ip, [], random_ports)
    country, city, org = geoip_lookup(ip)
    icmp_latency = real_icmp_ping(ip)
    return {
        'ip': ip,
        'results': results,
        'best': best,
        'country': country,
        'city': city,
        'org': org,
        'icmp_latency': icmp_latency
    }

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
            do_scan(filename, my_country)

if __name__ == '__main__':
    main() 
