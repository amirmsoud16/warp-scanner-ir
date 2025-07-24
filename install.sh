#!/bin/bash
# Warp Scanner Project Installer (English)
REPO="https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main"
FILES=(scanner.py ips-v4.txt ips-v6.txt README.md)

# Check and install git if needed
if command -v git &> /dev/null; then
    echo "[+] git is already installed. Skipping."
else
    echo "[+] Installing git..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y git
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm git
    else
        echo "Please install git manually."
    fi
fi

# Check and install pip if needed
if command -v pip3 &> /dev/null; then
    echo "[+] pip3 is already installed. Skipping."
else
    echo "[+] Installing pip3..."
    python3 -m ensurepip --upgrade || true
fi

# Check and install requests if needed
if python3 -c "import requests" &> /dev/null; then
    echo "[+] Python requests library is already installed. Skipping."
else
    echo "[+] Installing Python requests library..."
    pip3 install --upgrade pip
    pip3 install requests
fi

# Check and install ping3 if needed
if python3 -c "import ping3" &> /dev/null; then
    echo "[+] Python ping3 library is already installed. Skipping."
else
    echo "[+] Installing Python ping3 library..."
    pip3 install ping3
fi

# حذف pyperclip و clipboard و speedtest-cli
# باقی کد نصب و دانلود فایل‌ها ...

# Download project files
echo "[+] Downloading project files from GitHub..."
for file in "${FILES[@]}"; do
    echo "Downloading $file ..."
    curl -sSL "$REPO/$file" -o "$file"
    if [ $? -ne 0 ]; then
        echo "Download of $file failed!"
        exit 1
    fi
    echo "$file downloaded."
done

echo "[+] Installation and download completed successfully!"
echo "Running the scanner..."
python3 scanner.py 
