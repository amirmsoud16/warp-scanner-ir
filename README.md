# Warp Anycast IP & Port Scanner

ابزاری حرفه‌ای برای پیدا کردن بهترین آی‌پی و پورت Warp (Cloudflare) با پینگ پایین و نزدیک‌ترین موقعیت جغرافیایی به اینترنت شما.

## ویژگی‌ها
- شناسایی موقعیت اینترنت شما (GeoIP)
- تست فقط آی‌پی‌های نزدیک به شما (بر اساس کشور)
- تولید آی‌پی تصادفی از رنج‌های CIDR (IPv4 و IPv6)
- تست پورت‌های اصلی (2408/UDP, 443/TCP/UDP) و چند پورت رندوم (TCP/UDP)
- سنجش پینگ و نمایش موقعیت جغرافیایی آی‌پی
- نمایش بهترین آی‌پی:پورت با کمترین پینگ و سرعت بالا
- منوی ترمینالی باکسی و زیبا

## نصب آسان
```bash
bash <(curl -Ls https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main/install.sh)
```
## نصب آسان در ترماکس
```bash
curl -Ls https://raw.githubusercontent.com/amirmsoud16/warp-scanner-ir/main/install.sh -o install.sh
bash install.sh
```
## نصب
```bash
bash install.sh
```
یا به صورت دستی:
```bash
pip install requests
```

## اجرا
```bash
python3 scanner.py
```

## فایل‌ها
- `scanner.py` : اسکریپت اصلی اسکنر
- `ips-v4.txt` : لیست رنج آی‌پی‌های IPv4
- `ips-v6.txt` : لیست رنج آی‌پی‌های IPv6
- `install.sh` : اسکریپت نصب پیش‌نیازها

---

## English

A professional tool to find the best Warp (Cloudflare) Anycast IP & Port with lowest ping and closest geo-location to your internet.

### Features
- Detects your internet location (GeoIP)
- Tests only IPs close to you (by country)
- Random IP generation from CIDR ranges (IPv4 & IPv6)
- Test main ports (2408/UDP, 443/TCP/UDP) and several random ports (TCP/UDP)
- Ping and geo-location display
- Shows the best IP:Port with lowest latency and high speed
- Beautiful boxed terminal menu

### Install
```bash
bash install.sh
```
Or manually:
```bash
pip install requests
```

### Run
```bash
python3 scanner.py
```

### Files
- `scanner.py` : Main scanner script
- `ips-v4.txt` : IPv4 CIDR ranges
- `ips-v6.txt` : IPv6 CIDR ranges
- `install.sh` : Install script 
