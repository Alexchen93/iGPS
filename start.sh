#!/bin/bash
# ==============================================
# iGPS 定位控制台 - 一鍵啟動腳本
# 關閉 GUI 視窗後會自動清理所有相關程序
# ==============================================

PROJECT_DIR="/home/alex/文件/iphone-location-simulator"

clear
echo "╔═══════════════════════════════════════════╗"
echo "║     iGPS 定位控制台                       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── 診斷模式 ──
if [ "$1" = "--check" ]; then
    echo "── 診斷模式 ──"
    echo ""
    cd "$PROJECT_DIR"
    if .venv/bin/python -m pymobiledevice3 --version >/dev/null 2>&1; then
        echo "   ✅ pymobiledevice3 已安裝"
    else
        echo "   ❌ pymobiledevice3 未安裝"
    fi
    if .venv/bin/python -m pymobiledevice3 usbmux list 2>/dev/null | grep -q iPhone; then
        echo "   ✅ iPhone 已透過 USB 連接"
    else
        echo "   ⚠️  未偵測到 iPhone USB 連線"
    fi
    DEV_MODE=$(cd "$PROJECT_DIR" && .venv/bin/python -m pymobiledevice3 amfi developer-mode-status 2>/dev/null)
    if [ "$DEV_MODE" = "true" ]; then
        echo "   ✅ iPhone 開發者模式已開啟"
    else
        echo "   ⚠️  iPhone 開發者模式未開啟"
    fi
    echo ""
    exit 0
fi

# ── 清理函式：確保關閉時一定執行 ──
cleanup() {
    echo ""
    echo "── 清理資源 ──"
    pkill -f "simulate-location" 2>/dev/null
    echo "   釋放 port 49151..."
    sudo fuser -k 49151/tcp 2>/dev/null
    sleep 1
    echo "   ✅ 已清理完畢"
    echo ""
}
trap cleanup EXIT

# ── 步驟 1：驗證 sudo ──
echo "── 步驟 1/3：驗證權限 ──"
echo "⚠️  需要 sudo 權限，請輸入密碼"
sudo -v
if [ $? -ne 0 ]; then
    echo "❌ 密碼錯誤或取消"
    read -p "按 Enter 關閉..."
    exit 1
fi
echo "✅ 權限驗證成功"
echo ""

# ── 步驟 2：啟動 Tunneld ──
echo "── 步驟 2/3：啟動 Tunneld ──"

# 釋放舊 port
echo "   釋放 port 49151..."
sudo fuser -k 49151/tcp 2>/dev/null
sleep 1

if ss -tlnp 2>/dev/null | grep -q 49151; then
    echo "   ⚠️  port 仍被佔用，強制清除..."
    PID=$(sudo ss -tlnp 2>/dev/null | grep 49151 | grep -oP "pid=\K[0-9]+" | head -1)
    [ -n "$PID" ] && sudo kill -9 "$PID" 2>/dev/null
    sleep 2
    if ss -tlnp 2>/dev/null | grep -q 49151; then
        echo "   ❌ 無法釋放 port 49151，請重開機"
        read -p "按 Enter 關閉..."
        exit 1
    fi
fi
echo "   ✅ Port 49151 已釋放"

# 啟動 Tunneld
echo "   啟動 Tunneld..."
cd "$PROJECT_DIR"
sudo .venv/bin/pymobiledevice3 remote tunneld \
    --host 127.0.0.1 --port 49151 --protocol tcp > /tmp/tunneld.log 2>&1 &
TUNNEL_PID=$!

for i in 1 2 3 4 5 6 7 8; do
    sleep 1
    if ss -tlnp 2>/dev/null | grep -q 49151; then
        echo "   ✅ Tunneld 啟動成功 (PID: $TUNNEL_PID)"
        break
    fi
    if [ $i -eq 8 ]; then
        echo "   ❌ Tunneld 未在 8 秒內啟動"
        tail -5 /tmp/tunneld.log 2>/dev/null
        read -p "按 Enter 關閉..."
        exit 1
    fi
done

echo ""

# ── 步驟 3：啟動 GUI（前景執行，關閉後自動清理）──
echo "── 步驟 3/3：啟動控制介面 ──"
echo "   關閉 GUI 視窗後將自動清理所有資源"
cd "$PROJECT_DIR"

export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority
.venv/bin/python src/main.py

# GUI 已關閉 → cleanup() 會透過 trap EXIT 自動執行
