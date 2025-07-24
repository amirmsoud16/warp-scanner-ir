#!/usr/bin/env python3
"""
WARP Hiddify Config Generator - Professional Edition
Author: amiri | github.com/amirmsoud16
"""
import os, sys, random, time, requests, json, urllib.request, re, argparse, subprocess
from functools import partial

# --- Dependency Management ---
def ensure_package(pkg, import_name=None):
    import importlib
    try:
        importlib.import_module(import_name or pkg)
        return True
    except ImportError:
        print(f"[!] {pkg} is not installed.")
        ans = input(f"Do you want to install {pkg}? [Y/n]: ").strip().lower()
        if ans in ["", "y", "yes", "1"]:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                print(f"[+] {pkg} installed. Please rerun the program.")
                sys.exit(0)
            except Exception as e:
                print(f"[!] Failed to install {pkg}: {e}")
                sys.exit(1)
        else:
            print(f"[!] {pkg} is required for best experience. Continuing without it.")
            return False

# --- Color and Banner Utilities ---
def try_import_colorama():
    try:
        from colorama import init, Fore, Style
        init(autoreset=True)
        return True, Fore, Style
    except ImportError:
        return False, None, None

# --- Table Utility ---
def try_import_tabulate():
    try:
        from tabulate import tabulate
        return tabulate
    except ImportError:
        return None

# --- Main Script ---
# Check for colorama and tqdm (offer install if missing)
COLOR, Fore, Style = try_import_colorama()
if not COLOR:
    ensure_package('colorama')
try:
    from tqdm import tqdm
except ImportError:
    ensure_package('tqdm')

TABULATE = try_import_tabulate()


def c(text, color):
    """Colorize text if colorama is available."""
    if not COLOR:
        return text
    return getattr(Fore, color.upper(), Fore.WHITE) + str(text) + Style.RESET_ALL

def banner():
    """Prints a beautiful ASCII banner and welcome message."""
    art = r"""
 __        __   _                            _  _  _           _           
 \ \      / /__| | ___ ___  _ __ ___   ___  | || || | ___  ___| |_ ___ _ __ 
  \ \ /\ / / _ \ |/ __/ _ \| '_ ` _ \ / _ \ | || || |/ _ \/ __| __/ _ \ '__|
   \ V  V /  __/ | (_| (_) | | | | | |  __/ | || || |  __/ (__| ||  __/ |   
    \_/\_/ \___|_|\___\___/|_| |_| |_|\___| |_||_||_|\___|\___|\__\___|_|   
"""
    print(c(art, 'cyan'))
    print(c("WARP Hiddify Config Generator", 'magenta'))
    print(c("by amiri | github.com/amirmsoud16", 'yellow'))
    print()
    print(c("Welcome! This tool scans IPs and generates a ready-to-use Hiddify/Sing-box config with the best IP.", 'green'))
    print()

def print_boxed(lines, color='green'):
    """Prints a box around the given lines with optional color."""
    width = max(len(line) for line in lines) + 4
    border = c("\n" + "┌" + "─" * (width - 2) + "┐", color)
    print(border)
    for line in lines:
        print(c("│ " + line.ljust(width - 3) + "│", color))
    print(c("└" + "─" * (width - 2) + "┘\n", color))

# --- Input and File Utilities ---
def load_ips(filename):
    """Loads IPs from a file, ignoring comments and empty lines."""
    try:
        with open(filename, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print_boxed([f"Error reading {filename}: {e}"], 'red')
        return []

def choose_filename(default_name):
    """Prompt user for a filename, with a default."""
    name = input(f"Enter config filename (default: {default_name}): ").strip()
    return name if name else default_name

# --- Scanning and Progress ---
def ping_ip(ip, port=443, timeout=0.4):
    """Ping an IP on the given port using TCP. Returns latency in ms or None on failure."""
    import socket
    start = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        latency = (time.time() - start) * 1000
        return latency
    except Exception:
        return None

def progress_bar(iterable, total=None, desc="", color='cyan'):
    try:
        from tqdm import tqdm
        return tqdm(iterable, total=total, desc=desc, ncols=70)
    except ImportError:
        if desc:
            print(c(f"[!] tqdm not installed. Progress bar will be basic. To install: pip install tqdm", 'yellow'))
        total = total or len(iterable)
        for i, item in enumerate(iterable, 1):
            percent = int((i / total) * 100)
            bar = ('#' * (percent // 2)).ljust(50)
            sys.stdout.write(f"\r{desc}: [{bar}] {percent}% ({i}/{total})")
            sys.stdout.flush()
            yield item
        print()

# --- Hiddify Config Generation ---
def get_hiddify_keys():
    """Fetches WireGuard keys and reserved values from the API."""
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

def build_hiddify_config(best_ip, port, Address_key, private_key, reserved):
    """Builds the Hiddify/Sing-box JSON config for the best IP."""
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
                            "endpoint": f"{best_ip}:{port}",
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
    return json.dumps(warp_json, indent=2, ensure_ascii=False)

# --- Saving and Output ---
def save_config(config_text, is_termux, filename):
    """Saves the config file to Downloads (Android) or ~/WARPS (Linux)."""
    if is_termux:
        save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'storage', 'downloads')
        if not os.path.isdir(save_dir):
            save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'downloads')
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)
    else:
        warps_dir = os.path.expanduser('~/WARPS')
        os.makedirs(warps_dir, exist_ok=True)
        file_path = os.path.join(warps_dir, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(config_text)
        print_boxed([f"Config saved as {file_path}"], 'yellow')
    except Exception as e:
        print_boxed([f"Failed to save config: {e}"], 'red')

def save_scan_log(log_rows, is_termux, filename):
    """Saves the scan log as a CSV file in the same folder as the config."""
    if is_termux:
        save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'storage', 'downloads')
        if not os.path.isdir(save_dir):
            save_dir = os.path.join(os.environ.get('HOME', '/data/data/com.termux/files/home'), 'downloads')
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)
    else:
        warps_dir = os.path.expanduser('~/WARPS')
        os.makedirs(warps_dir, exist_ok=True)
        file_path = os.path.join(warps_dir, filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('IP,Port,Latency(ms),Status\n')
            for row in log_rows:
                f.write(','.join(str(x) for x in row) + '\n')
        print_boxed([f"Scan log saved as {file_path}"], 'yellow')
    except Exception as e:
        print_boxed([f"Failed to save scan log: {e}"], 'red')

# --- Main Logic ---
def scan_and_generate(ip_file, count=20, port=443, output_name=None, no_color=False, non_interactive=False):
    """Scans IPs, finds the best, and generates/saves the Hiddify config."""
    global COLOR
    if no_color:
        COLOR = False
    ips = load_ips(ip_file)
    if not ips:
        print_boxed([f"No IPs found in {ip_file}"], 'red')
        return
    print(c(f"Testing {min(count, len(ips))} IPs. Please wait...", 'cyan'))
    best_ip = None
    best_latency = None
    scan_log = []
    scan_rows = []
    for ip in progress_bar(random.sample(ips, min(count, len(ips))), total=min(count, len(ips)), desc="Scanning", color='magenta'):
        latency = ping_ip(ip, port=port)
        if latency is not None:
            print(c(f"{ip}:{port} - {latency:.1f} ms", 'green'))
            scan_rows.append([ip, port, f"{latency:.1f}", "OK"])
            if best_latency is None or latency < best_latency:
                best_ip, best_latency = ip, latency
        else:
            print(c(f"{ip}:{port} - timeout", 'red'))
            scan_rows.append([ip, port, "timeout", "FAIL"])
    # Show table of results
    if TABULATE:
        from tabulate import tabulate
        print(tabulate(scan_rows, headers=["IP", "Port", "Latency(ms)", "Status"], tablefmt="fancy_grid"))
    else:
        print_boxed(["[!] tabulate not installed. Table output will be basic. To install: pip install tabulate"], 'yellow')
        for row in scan_rows:
            print(f"{row[0]}:{row[1]} - {row[2]} ms - {row[3]}")
    if not best_ip:
        print_boxed(["No reachable IP found."], 'red')
        return
    print_boxed([f"Best IP: {best_ip}:{port} ({best_latency:.1f} ms)"])
    if not non_interactive:
        answer = input(c("Do you want to generate a Hiddify config for this IP? [y/N]: ", 'yellow')).strip().lower()
        if answer not in ["y", "yes", "1"]:
            print_boxed(["Config generation skipped by user."], 'yellow')
            return
    Address_key, private_key, reserved = get_hiddify_keys()
    config_text = build_hiddify_config(best_ip, port, Address_key, private_key, reserved)
    print_boxed(["==== Hiddify/Sing-box Warp JSON Config (Best Ping) ===="], 'cyan')
    print(c(config_text, 'white'))
    is_termux = 'com.termux' in sys.executable or 'termux' in sys.executable or 'ANDROID_STORAGE' in os.environ
    filename = output_name or (choose_filename('warp_hiddify_config.txt') if not non_interactive else 'warp_hiddify_config.txt')
    save_config(config_text, is_termux, filename)
    # Ask to save scan log
    if not non_interactive:
        save_log = input(c("Do you want to save the scan log as CSV? [y/N]: ", 'yellow')).strip().lower()
        if save_log in ["y", "yes", "1"]:
            log_name = os.path.splitext(filename)[0] + "_scanlog.csv"
            save_scan_log(scan_rows, is_termux, log_name)
    if not non_interactive:
        input(c("Press Enter to exit...", 'magenta'))

# --- CLI and Entry Point ---
def print_help():
    help_text = f"""
WARP Hiddify Config Generator - CLI Usage

Options:
  --ipv4            Use ips-v4.txt for scanning (default if neither --ipv4 nor --ipv6 is given)
  --ipv6            Use ips-v6.txt for scanning
  --count N         Number of IPs to scan (default: 20)
  --port P          Port to test for ping (default: 443)
  --output FILE     Output config filename (default: warp_hiddify_config.txt)
  --no-color        Disable colored output
  --help            Show this help message and exit

Examples:
  python3 scanner.py --ipv4 --count 30 --port 443 --output myconfig.txt
  python3 scanner.py --ipv6 --no-color

If no arguments are given, interactive mode will be used.
"""
    print(help_text)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--ipv4', action='store_true')
    parser.add_argument('--ipv6', action='store_true')
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--port', type=int, default=443)
    parser.add_argument('--output', type=str)
    parser.add_argument('--no-color', action='store_true')
    parser.add_argument('--help', action='store_true')
    args, unknown = parser.parse_known_args()

    if args.help:
        print_help()
        return

    # If any CLI arg except --help is given, use non-interactive mode
    non_interactive = any([
        args.ipv4, args.ipv6, args.count != 20, args.port != 443, args.output, args.no_color
    ])

    if non_interactive:
        banner()
        ip_file = 'ips-v4.txt' if args.ipv4 or not args.ipv6 else 'ips-v6.txt'
        scan_and_generate(ip_file, count=args.count, port=args.port, output_name=args.output, no_color=args.no_color, non_interactive=True)
    else:
        banner()
        print_boxed(["1. Scan IPv4", "2. Scan IPv6", "0. Exit"], 'magenta')
        choice = input(c("Enter your choice: ", 'yellow')).strip()
        if choice == "1":
            ip_file = "ips-v4.txt"
        elif choice == "2":
            ip_file = "ips-v6.txt"
        else:
            print(c("Goodbye!", 'cyan'))
            return
        # Ask for count and port interactively
        try:
            count = int(input(c("How many IPs to scan? (default 20): ", 'yellow')).strip() or "20")
        except Exception:
            count = 20
        try:
            port = int(input(c("Which port to test? (default 443): ", 'yellow')).strip() or "443")
        except Exception:
            port = 443
        scan_and_generate(ip_file, count=count, port=port)

if __name__ == '__main__':
    main() 
