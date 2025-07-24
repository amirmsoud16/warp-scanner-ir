#!/bin/bash
set -e

WARPS_DIR="$HOME/WARPS"
REPO="https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main"
FILES=(scanner.py ips-v4.txt ips-v6.txt README.md)

# Detect Termux
if [ -n "$PREFIX" ] && [ -x "$(command -v pkg)" ]; then
    IS_TERMUX=1
else
    IS_TERMUX=0
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
    echo "[+] Python3 not found. Attempting to install..."
    if [ "$IS_TERMUX" = 1 ]; then
        pkg install -y python
    elif command -v apt &> /dev/null; then
        apt update && apt install -y python3
    elif command -v yum &> /dev/null; then
        yum install -y python3
    elif command -v dnf &> /dev/null; then
        dnf install -y python3
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm python
    else
        echo "Please install python3 manually."
        exit 1
    fi
fi

# Install pip3 if not present
if ! command -v pip3 &> /dev/null; then
    echo "[+] pip3 not found. Attempting to install..."
    if [ "$IS_TERMUX" = 1 ]; then
        pkg install -y python-pip
    elif command -v apt &> /dev/null; then
        apt update && apt install -y python3-pip
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip
    elif command -v dnf &> /dev/null; then
        dnf install -y python3-pip
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm python-pip
    else
        echo "[+] Trying to install pip3 using get-pip.py ..."
        curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py && rm get-pip.py
    fi
    if ! command -v pip3 &> /dev/null; then
        echo "[!] pip3 installation failed. Please install pip3 manually."
        exit 1
    fi
fi

# Install Python dependencies (requests, ping3)
if [ "$IS_TERMUX" = 1 ]; then
    pip3 install requests ping3
else
    pip3 install --user requests ping3
fi

# Check and install wgcf if needed
if ! command -v wgcf &> /dev/null; then
    echo "[+] wgcf not found. Attempting to install..."
    if [ "$IS_TERMUX" = 1 ]; then
        pkg install -y golang
        go install github.com/ViRb3/wgcf@latest
        cp ~/go/bin/wgcf ~/bin/wgcf
        chmod +x ~/bin/wgcf
        echo "[+] wgcf installed in ~/bin."
    else
        ARCH=$(uname -m)
        if [ "$ARCH" = "x86_64" ]; then ARCH=amd64; fi
        if [ "$ARCH" = "aarch64" ]; then ARCH=arm64; fi
        WGCF_URL="https://github.com/ViRb3/wgcf/releases/latest/download/wgcf_${ARCH}_linux.tar.gz"
        mkdir -p "$HOME/bin"
        cd "$HOME/bin"
        curl -LO "$WGCF_URL"
        tar xzf wgcf_${ARCH}_linux.tar.gz
        chmod +x wgcf
        rm wgcf_${ARCH}_linux.tar.gz
        echo "[+] wgcf installed in $HOME/bin."
        export PATH="$HOME/bin:$PATH"
        cd "$WARPS_DIR"
    fi
fi

# Download files
for file in "${FILES[@]}"; do
    echo "Downloading $file ..."
    curl -sSL "$REPO/$file" -o "$file"
    if [ $? -ne 0 ]; then
        echo "Download of $file failed!"
        exit 1
    fi
    echo "$file downloaded."
done

# Create launcher script in WARPS_DIR
cat > "$WARPS_DIR/WARPS" <<EOF
#!/bin/bash
python3 "\$HOME/WARPS/scanner.py"
EOF
chmod +x "$WARPS_DIR/WARPS"

# Optionally add to $HOME/bin for easy access
if [ ! -d "$HOME/bin" ]; then
    mkdir -p "$HOME/bin"
fi
cp "$WARPS_DIR/WARPS" "$HOME/bin/WARPS"
export PATH="$HOME/bin:$PATH"

# Final message and run menu
echo "[+] Installation complete! Run 'WARPS' from anywhere to start the menu."
cd "$WARPS_DIR"
python3 scanner.py 
