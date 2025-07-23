#!/bin/bash
# نصب پیش‌نیازهای اسکنر Warp

echo "[+] نصب git (در صورت نیاز)..."
if command -v apt &> /dev/null; then
    sudo apt update && sudo apt install -y git
elif command -v yum &> /dev/null; then
    sudo yum install -y git
elif command -v dnf &> /dev/null; then
    sudo dnf install -y git
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm git
else
    echo "لطفاً git را به صورت دستی نصب کنید."
fi

echo "[+] نصب pip (در صورت نیاز)..."
python3 -m ensurepip --upgrade || true

echo "[+] نصب کتابخانه‌های مورد نیاز..."
pip3 install --upgrade pip
pip3 install requests

echo "[+] نصب با موفقیت انجام شد!"
echo "در حال اجرای اسکریپت اسکنر..."
python3 scanner.py 