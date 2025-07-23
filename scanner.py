"""
Warp Anycast IP & Port Scanner
=============================

ابزاری حرفه‌ای برای پیدا کردن بهترین آی‌پی و پورت Warp (Cloudflare) با پینگ پایین و نزدیک‌ترین موقعیت جغرافیایی به اینترنت شما.

اجرا:
    python3 scanner.py

نیازمندی‌ها:
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

# تنظیمات
IPV4_FILE = 'ips-v4.txt'
IPV6_FILE = 'ips-v6.txt'
PORTS_MAIN = [(2408, 'udp'), (443, 'tcp'), (443, 'udp')]
PORTS_RANDOM_COUNT = 5
PORT_RANGE = (1000, 60000)
IPS_PER_RANGE = 5
TIMEOUT = 1.5
GEOIP_URL = 'https://ipinfo.io/{ip}/json'

# --- ابزارهای نمایشی ---
def print_boxed(text_lines):
    width = max(len(line) for line in text_lines) + 4
    print("\n" + "┌" + "─" * (width - 2) + "┐")
    for line in text_lines:
        print("│ " + line.ljust(width - 3) + "│")
    print("└" + "─" * (width - 2) + "┘\n")

def main_menu():
    menu_lines = [
        "   Warp Anycast IP Scanner   ",
        "============================",
        " 1. تست اینترنت",
        " 2. اسکن آی‌پی‌های Warp نسخه 4 (IPv4)",
        " 3. اسکن آی‌پی‌های Warp نسخه 6 (IPv6)",
        " 0. خروج"
    ]
    print_boxed(menu_lines)
    while True:
        choice = input('انتخاب شما: ').strip()
        if choice in ['1', '2', '3', '0']:
            return choice

# --- GeoIP ---
def get_my_location():
    try:
        r = requests.get('https://ipinfo.io/json', timeout=3)
        if r.status_code == 200:
            data = r.json()
            return data.get('country', ''), data.get('city', ''), data.get('ip', '')
    except Exception:
        pass
    return '', '', ''

def geoip_lookup(ip):
    try:
        r = requests.get(GEOIP_URL.format(ip=ip), timeout=2)
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

def test_ip_ports(ip, ports):
    results = []
    for port, proto in ports:
        if proto == 'tcp':
            ok, latency = ping_tcp(ip, port)
        else:
            ok, latency = ping_udp(ip, port)
        results.append({'port': port, 'proto': proto, 'ok': ok, 'latency': latency})
    return results

def scan_ip(ip, n_port):
    ports = PORTS_MAIN.copy()
    exclude = set(p for p, _ in ports)
    for p in random_ports(n_port, exclude_ports=exclude):
        ports.append((p, random.choice(['tcp', 'udp'])))
    results = test_ip_ports(ip, ports)
    best = min((r for r in results if r['ok']), key=lambda x: x['latency'] if x['latency'] else 9999, default=None)
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
    lines = ["--- بهترین آی‌پی‌ها ---"]
    for b in results:
        lines.append(f"{b['ip']}:{b['best']['port']} {b['best']['proto']} | {b['country']} {b['city']} | پینگ: {b['best']['latency']:.0f} ms")
    print_boxed(lines)

def ask_wireguard_config(ip, port):
    print_boxed([f"آیا کانفیگ وایرگارد با این آی‌پی می‌خواهید؟", f"{ip}:{port}", "1. بله", "2. خیر"])
    while True:
        ans = input("انتخاب شما: ").strip()
        if ans in ["1", "2"]:
            return ans == "1"

def generate_private_key():
    # تولید کلید خصوصی 32 بایتی و تبدیل به base64 (سازگار با WireGuard)
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
    print_boxed(["کانفیگ متنی WireGuard:"] + config)
    print_boxed(["لینک سریع wg://:", uri])

def do_scan(filename, n_ip, n_port, my_country):
    cidrs = load_cidr_list(filename)
    ips = []
    for cidr in cidrs:
        for _ in range(n_ip):
            try:
                ip = random_ip_from_cidr(cidr)
                ips.append(ip)
            except Exception:
                continue
    # فیلتر آی‌پی‌های نزدیک (بر اساس کشور)
    print('در حال شناسایی آی‌پی‌های نزدیک...')
    close_ips = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_ip = {executor.submit(geoip_lookup, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            country, city, org = future.result()
            ip = future_to_ip[future]
            if country == my_country:
                close_ips.append(ip)
    print(f'تعداد آی‌پی نزدیک به شما: {len(close_ips)}')
    # تست پینگ و پورت فقط روی آی‌پی‌های نزدیک
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_ip = {executor.submit(scan_ip, ip, n_port): ip for ip in close_ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            res = future.result()
            results.append(res)
    bests = sorted((r for r in results if r['best']), key=lambda x: x['best']['latency'])[:10]
    show_results_boxed(bests)
    if bests:
        if ask_wireguard_config(bests[0]['ip'], bests[0]['best']['port']):
            show_wireguard_config(bests[0]['ip'], bests[0]['best']['port'])
        else:
            print_boxed(["کانفیگ ساخته نشد."])
    else:
        print_boxed(["هیچ آی‌پی مناسبی پیدا نشد."])

def main():
    while True:
        choice = main_menu()
        if choice == '0':
            print_boxed(["خروج از برنامه. موفق باشید!"])
            break
        elif choice == '1':
            my_country, my_city, my_ip = get_my_location()
            print_boxed([f"موقعیت اینترنت شما:", f"کشور: {my_country}", f"شهر: {my_city}", f"IP: {my_ip}"])
        elif choice in ['2', '3']:
            my_country, my_city, my_ip = get_my_location()
            filename = IPV4_FILE if choice == '2' else IPV6_FILE
            try:
                n_ip = int(input(f'تعداد آی‌پی تستی از هر رنج (پیش‌فرض {IPS_PER_RANGE}): ') or IPS_PER_RANGE)
            except:
                n_ip = IPS_PER_RANGE
            try:
                n_port = int(input(f'تعداد پورت رندوم برای هر آی‌پی (پیش‌فرض {PORTS_RANDOM_COUNT}): ') or PORTS_RANDOM_COUNT)
            except:
                n_port = PORTS_RANDOM_COUNT
            do_scan(filename, n_ip, n_port, my_country)

if __name__ == '__main__':
    main() 