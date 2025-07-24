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

# Check and install pyperclip if needed
if python3 -c "import pyperclip" &> /dev/null; then
    echo "[+] Python pyperclip library is already installed. Skipping."
else
    echo "[+] Installing Python pyperclip library..."
    pip3 install pyperclip
fi

# Clipboard prerequisites for each OS
OS_TYPE=$(uname | tr '[:upper:]' '[:lower:]')
if [[ "$OS_TYPE" == *"mingw"* || "$OS_TYPE" == *"msys"* || "$OS_TYPE" == *"cygwin"* ]]; then
    # Windows (Git Bash, Cygwin, etc.)
    if python3 -c "import win32clipboard" &> /dev/null; then
        echo "[+] pywin32 is already installed. Skipping."
    else
        echo "[+] Installing pywin32 for Windows clipboard support..."
        pip3 install pywin32
    fi
elif [[ "$OS_TYPE" == *"linux"* ]]; then
    # Check for Termux
    if grep -qi termux <<< "$PREFIX"; then
        if command -v termux-clipboard-set &> /dev/null; then
            echo "[+] termux-api is already installed. Skipping."
        else
            echo "[+] Installing termux-api for Termux clipboard support..."
            pkg install -y termux-api
        fi
    else
        # Standard Linux
        if command -v xclip &> /dev/null; then
            echo "[+] xclip is already installed. Skipping."
        elif command -v xsel &> /dev/null; then
            echo "[+] xsel is already installed. Skipping."
        elif command -v apt &> /dev/null; then
            echo "[+] Installing xclip for clipboard support..."
            sudo apt update && sudo apt install -y xclip
        elif command -v yum &> /dev/null; then
            echo "[+] Installing xclip for clipboard support..."
            sudo yum install -y xclip
        elif command -v dnf &> /dev/null; then
            echo "[+] Installing xclip for clipboard support..."
            sudo dnf install -y xclip
        elif command -v pacman &> /dev/null; then
            echo "[+] Installing xclip for clipboard support..."
            sudo pacman -Sy --noconfirm xclip
        else
            echo "[!] Please install xclip or xsel manually for clipboard support."
        fi
    fi
elif [[ "$OS_TYPE" == *"darwin"* ]]; then
    echo "[+] macOS detected. Clipboard support should work by default."
else
    echo "[!] Unknown OS. Clipboard support may not work."
fi

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
