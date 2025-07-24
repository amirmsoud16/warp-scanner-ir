#!/bin/bash
set -e

WARPS_DIR="$HOME/WARPS"
REPO="https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main"
FILES=(scanner.py ips-v4.txt ips-v6.txt README.md)

# Ensure python3 and pip3 are installed (Termux or Linux)
if [ -n "$PREFIX" ] && [ -x "$(command -v pkg)" ]; then
    echo "[+] Detected Termux. Installing/updating Python 3 and pip3 ..."
    pkg update -y
    pkg upgrade -y
    pkg install -y python
elif command -v apt &> /dev/null; then
    echo "[+] Detected apt package manager. Installing/updating Python 3 and pip3 ..."
    if [ "$(id -u)" -ne 0 ]; then
        SUDO=sudo
    else
        SUDO=""
    fi
    $SUDO apt update -y
    $SUDO apt upgrade -y
    $SUDO apt install -y python3 python3-pip
fi

# Remove old WARPS directory if exists
if [ -d "$WARPS_DIR" ]; then
    echo "[+] Removing old WARPS directory..."
    rm -rf "$WARPS_DIR"
fi

# Create WARPS directory
mkdir -p "$WARPS_DIR"
cd "$WARPS_DIR"

# Install python3 if not present
if ! command -v python3 &> /dev/null; then
    echo "[+] Python3 not found. Please install Python 3 manually."
    exit 1
fi

# Install pip3 if not present
if ! command -v pip3 &> /dev/null; then
    echo "[+] pip3 not found. Please install pip3 manually."
    exit 1
fi

# Install Python dependencies (requests, urllib3, colorama, tqdm, tabulate)
echo "[+] Installing required Python packages: requests, urllib3, colorama, tqdm, tabulate ..."
pip3 install --user requests urllib3 colorama tqdm tabulate

# Ensure tabulate is installed system-wide as well (for some environments)
pip3 install tabulate

echo "Installing wireguard-tools (required for key generation)..."
apt update && apt install -y wireguard-tools

# Download files
for file in "${FILES[@]}"; do
    echo "Downloading $file ..."
    if [ -f "$WARPS_DIR/$file" ]; then
        rm -f "$WARPS_DIR/$file"
    fi
    curl -sO "$REPO/$file"
    if [ $? -ne 0 ]; then
        echo "Download of $file failed!"
        exit 1
    fi
    echo "$file downloaded."
done

# Final message
echo "[+] Installation complete! Starting the program..."
cd "$HOME/WARPS"
python3 scanner.py 
