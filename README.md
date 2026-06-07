# iGPS 定位控制台

基於 [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator) 開發的 iPhone GPS 定位模擬器，專為 Linux 環境改寫與增強。

## 原作者

**Marcel Afsar** — [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)

## 功能

- iPhone 13 (iOS 17+) GPS 定位模擬
- 地圖路線規劃與模擬（步行 / 騎車 / 開車 / 高速公路）
- 區域漫遊（指定半徑內持續移動）
- 搖桿微調方向
- 位置凍結與重置
- 折疊式側欄導航（SVG 圖示）
- QComboBox 深色主題

## 技術棧

- Python 3.12 + PyQt6 + QtWebEngine
- Leaflet 地圖
- pymobiledevice3（iPhone 連線 / RSD tunnel）

## 快速開始

```bash
# 啟動 (自動建立 RSD tunnel + GUI)
./start.sh

# 關閉
./stop.sh
```

## 需求

- Linux（已在 Ubuntu 24.04 測試）
- Python 3.12+
- iPhone 開啟開發者模式
- USB 連線
- `sudo` 權限（tunneld 需要 root）
