#!/bin/bash
echo "🛑 關閉 iPhone 定位模擬器..."
pkill -f "src/main.py" 2>/dev/null && echo "✅ GUI 已關閉" || echo "⚠️ GUI 沒有在執行"
echo ""
echo "Tunneld 保持執行（下次啟動更快）"
echo "如需完全關閉: sudo pkill -f tunneld"
