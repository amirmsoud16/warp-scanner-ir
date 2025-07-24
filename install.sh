#!/bin/bash
set -e

WARPS_DIR="$HOME/WARPS"
REPO="https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main"
FILES=(scanner.py ips-v4.txt ips-v6.txt README.md)

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
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm python
    elif command -v pkg &> /dev/null; then
        pkg install -y python
    else
        echo "Please install python3 manually."
        exit 1
    fi
fi

# Install pip3 if not present
if ! command -v pip3 &> /dev/null; then
    echo "[+] pip3 not found. Attempting to install..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3-pip
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm python-pip
    elif command -v pkg &> /dev/null; then
        pkg install -y python-pip
    else
        echo "Please install pip3 manually."
        exit 1
    fi
fi
pip3 install --upgrade pip
pip3 install requests ping3

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
cd "\$HOME/WARPS"
python3 scanner.py
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
