#!/bin/bash
# ==============================================
# iPhone 定位模擬器 - 一鍵啟動腳本
# ==============================================

PROJECT_DIR="/home/alex/文件/iphone-location-simulator"
LOG_FILE="/tmp/iphone-sim-gui.log"

clear
echo "╔═══════════════════════════════════════════╗"
echo "║     📱 iPhone 定位模擬器                  ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# ── 步驟 1：先取得 sudo ──
echo "── 步驟 1/3：驗證權限 ──"
echo "⚠️  需要 sudo 權限，請輸入密碼"
echo ""
sudo -v
if [ $? -ne 0 ]; then
    echo "❌ 密碼錯誤或取消，結束"
    read -p "按 Enter 關閉..."
    exit 1
fi
echo "✅ 權限驗證成功"
echo ""

# ── 步驟 2：釋放 port + 啟動 Tunneld ──
echo "── 步驟 2/3：啟動 Tunneld ──"

# 用 fuser 強制釋放 port（不管誰佔用）
echo "   釋放 port 49151..."
sudo fuser -k 49151/tcp 2>/dev/null
sleep 1

# 確認真的清乾淨
if ss -tlnp 2>/dev/null | grep -q 49151; then
    echo "   ⚠️  port 仍被佔用，強制清除..."
    PID=$(sudo ss -tlnp 2>/dev/null | grep 49151 | grep -oP "pid=\K[0-9]+" | head -1)
    [ -n "$PID" ] && sudo kill -9 "$PID" 2>/dev/null
    sleep 2
    if ss -tlnp 2>/dev/null | grep -q 49151; then
        echo "   ❌ 無法釋放 port 49151，請重開機後再試"
        read -p "   按 Enter 關閉..."
        exit 1
    fi
fi
echo "   ✅ Port 49151 已釋放"

# 啟動新的
echo "   啟動 Tunneld..."
cd "$PROJECT_DIR"
sudo .venv/bin/pymobiledevice3 remote tunneld \
    --host 127.0.0.1 --port 49151 --protocol tcp > /tmp/tunneld.log 2>&1 &
TUNNEL_PID=$!

# 等它監聽（最多 8 秒）
for i in 1 2 3 4 5 6 7 8; do
    sleep 1
    if ss -tlnp 2>/dev/null | grep -q 49151; then
        echo "   ✅ Tunneld 啟動成功 (PID: $TUNNEL_PID)"
        break
    fi
    if [ $i -eq 8 ]; then
        echo "   ❌ Tunneld 未在 8 秒內啟動"
        echo "   Log:"
        tail -5 /tmp/tunneld.log 2>/dev/null
        read -p "   按 Enter 關閉..."
        exit 1
    fi
done

echo ""

# ── 步驟 3：啟動 GUI ──
echo "── 步驟 3/3：啟動控制介面 ──"
cd "$PROJECT_DIR"

export DISPLAY=:1
export XAUTHORITY=/run/user/1000/gdm/Xauthority

nohup .venv/bin/python src/main.py > "$LOG_FILE" 2>&1 &
GUI_PID=$!
sleep 3

if kill -0 $GUI_PID 2>/dev/null; then
    echo ""
    echo "╔═══════════════════════════════════════════╗"
    echo "║  🟢 全部就緒                              ║"
    echo "║  📍 在 GUI 點「連接裝置」開始控制 GPS     ║"
    echo "║  📋 Tunneld: $TUNNEL_PID  GUI: $GUI_PID   ║"
    echo "╚═══════════════════════════════════════════╝"
else
    echo ""
    echo "❌ GUI 啟動失敗，錯誤訊息："
    tail -15 "$LOG_FILE"
fi

echo ""
echo "（關閉此終端機不會影響 GUI，可直接關閉）"
echo ""
read -p "按 Enter 關閉此視窗..."
