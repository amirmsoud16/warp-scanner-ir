#!/bin/bash
# نصب و دانلود فایل‌های پروژه Warp Scanner از گیت‌هاب
REPO="https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main"
FILES=(scanner.py ips-v4.txt ips-v6.txt README.md)

# نصب git (در صورت نیاز)
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

# نصب pip و requests
echo "[+] نصب pip (در صورت نیاز)..."
python3 -m ensurepip --upgrade || true

echo "[+] نصب کتابخانه‌های مورد نیاز..."
pip3 install --upgrade pip
pip3 install requests

# دانلود فایل‌های پروژه (بعد از نصب پیش‌نیازها)
echo "[+] دانلود فایل‌های پروژه از گیت‌هاب..."
for file in "${FILES[@]}"; do
    echo "در حال دانلود $file ..."
    curl -sSL "$REPO/$file" -o "$file"
    if [ $? -ne 0 ]; then
        echo "دانلود $file با خطا مواجه شد!"
        exit 1
    fi
    echo "$file دانلود شد."
done

echo "[+] نصب و دانلود با موفقیت انجام شد!"
echo "در حال اجرای اسکریپت اسکنر..."
python3 scanner.py 
