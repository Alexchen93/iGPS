# iGPS — iPhone GPS 定位控制台（Linux 版）

[English](README.md) | [中文](#中文)

基於 [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator) 改寫，專為 Linux 環境優化與增強。

## 原作者

**Marcel Afsar** — [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)

## 功能

- 透過 `pymobiledevice3` 模擬 iPhone GPS 定位（iOS 17+ DVT / RSD tunnel）
- 路線規劃：地址搜尋、步行 / 騎車 / 開車 / 高速公路模式
- 區域漫遊：在指定半徑內持續移動，可拔線運作
- 搖桿方向微調
- 位置凍結 / 重置 / 恢復真實 GPS
- 折疊式側欄導航（SVG 向量圖示）
- 地圖右鍵選單（手機定位 / 設為起點 / 設為終點）
- 深色主題 QComboBox 下拉選單
- 關閉 GUI 自動清理（tunneld + port 釋放）

## 技術棧

| 層 | 技術 |
|---|---|
| 語言 | Python 3.12 |
| GUI | PyQt6 + QtWebEngine (Leaflet.js) |
| 裝置控制 | pymobiledevice3 |
| 地圖圖磚 | OpenStreetMap / CartoDB |
| 平台 | Linux（Ubuntu 24.04 測試） |

## 快速開始

```bash
# 啟動（自動建立 RSD tunnel + 啟動 GUI）
./start.sh

# 僅診斷，不啟動
./start.sh --check
```

關閉 GUI 視窗後所有程序自動清理。

## 需求

- Linux（Ubuntu 24.04 已測試）
- Python 3.12+
- iPhone 已開啟開發者模式
- USB 連線
- `sudo` 權限（tunneld 需要 root）

## 專案結構

```
src/
├── main.py                    # 程式進入點
├── gui/
│   ├── main_window.py         # 主視窗 + 左右分欄佈局
│   ├── control_panel.py       # 側欄導航 + 4 個子頁面
│   ├── map_widget.py          # QtWebEngine + Leaflet JS 橋接
│   ├── map_template.html      # Leaflet 地圖 HTML/JS
│   ├── style.qss              # 全域深色主題樣式
│   └── icons/                 # 25 個 SVG 向量圖示
├── core/
│   ├── device_manager.py      # iPhone 連線管理（RSD tunnel）
│   ├── location_controller.py # GPX 生成 + 定位執行
│   ├── coordinate_utils.py    # 地理距離計算
│   └── route_generator.py     # 路線節點生成
└── utils/
    ├── config_manager.py      # config.yaml 讀取器
    ├── logger.py              # Loguru 日誌設定
    └── gpx_handler.py         # GPX 檔案讀寫

tests/
└── test_imports.py            # 基本冒煙測試（5/5 pass）
```

## 介面佈局

```
┌──────────────┬──────────────────────────┐
│  裝置狀態列   │                          │
│ [連線] [◀]   │                          │
├──────────────┤       🗺️ 地圖             │
│  側欄導航     │                          │
│  (4 頁)      │                          │
│  ⚫ 定位路線  │        [狀態面板]         │
│  ⚫ 區域漫遊  │                          │
│  ⚫ 搖桿控制  │                          │
│  ⚫ 系統控制  │                          │
└──────────────┴──────────────────────────┘
   520px 固定      剩餘空間填滿
```

## 授權

MIT — 參見原始專案 [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)
