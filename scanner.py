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

# Settings
IPV4_FILE = 'ips-v4.txt'
IPV6_FILE = 'ips-v6.txt'
PORTS_MAIN = [(2408, 'udp'), (443, 'tcp'), (443, 'udp')]
PORTS_RANDOM_COUNT = 500
PORT_RANGE = (1000, 60000)
IPS_PER_RANGE = 30
TIMEOUT = 0.1
MAX_WORKERS = 1000
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

def scan_ip_optimized(ip, n_random_ports):
    main_ports = [(2408, 'udp'), (443, 'tcp'), (443, 'udp')]
    random_ports = [(p, random.choice(['tcp', 'udp'])) for p in random.sample(range(1000, 60000), n_random_ports)]
    best, results = test_ip_ports_optimized(ip, main_ports, random_ports)
    country, city, org = geoip_lookup(ip)
    return {
        'ip': ip,
        'results': results,
        'best': best,
        'country': country,
        'city': city,
        'org': org
    }

def show_results_boxed(results):
    lines = ["--- Best IPs ---"]
    for b in results:
        lines.append(f"{b['ip']}:{b['best']['port']} {b['best']['proto']} | {b['country']} {b['city']} | Ping: {b['best']['latency']:.0f} ms")
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
    print_boxed(["WireGuard config:"] + config)
    print_boxed(["Quick wg:// link:", uri])

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

def do_scan(filename, n_ip, n_port, my_country):
    cidrs = load_cidr_list(filename)
    ips = []
    total_cidrs = len(cidrs)
    for idx, cidr in enumerate(cidrs, 1):
        for _ in range(n_ip):
            try:
                ip = random_ip_from_cidr(cidr)
                ips.append(ip)
            except Exception:
                continue
        print_progress(idx, total_cidrs, "Building IP list")
    print(f'Total IPs to scan: {len(ips)}')
    # Progress bar for scanning IPs and ports
    results = []
    total = len(ips)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ip = {executor.submit(scan_ip_optimized, ip, n_port): ip for ip in ips}
        for idx, future in enumerate(concurrent.futures.as_completed(future_to_ip), 1):
            res = future.result()
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
            n_ip = IPS_PER_RANGE
            n_port = PORTS_RANDOM_COUNT
            do_scan(filename, n_ip, n_port, my_country)

if __name__ == '__main__':
    main() 
