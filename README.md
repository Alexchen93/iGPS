# iGPS — iPhone GPS Location Simulator for Linux

Based on [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator), rewritten and enhanced for Linux.

> 基於 marcelafsar/iphone-location-simulator，專為 Linux 環境改寫與增強的 iPhone GPS 定位控制台。

## Original Author

**Marcel Afsar** — [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)

## Features / 功能

- iPhone GPS location simulation via `pymobiledevice3` (iOS 17+ DVT / RSD tunnel)
- Route planning with address search (walking / cycling / driving / highway)
- Area roaming (continuous movement within a radius)
- Joystick directional control
- Location freeze / reset
- Collapsible sidebar with SVG icons
- Dark-themed QComboBox dropdowns
- Right-click context menu on map
- Auto-cleanup on exit (tunneld + port release)

## Tech Stack / 技術棧

| Layer | Tech |
|---|---|
| Language | Python 3.12 |
| GUI | PyQt6 + QtWebEngine (Leaflet.js) |
| Device | pymobiledevice3 |
| Map tiles | OpenStreetMap / CartoDB |
| Platform | Linux (tested on Ubuntu 24.04) |

## Quick Start / 快速開始

```bash
# Start (auto-setup RSD tunnel + launch GUI)
./start.sh

# Diagnostics only (no launch)
./start.sh --check
```

Close the GUI window to automatically clean up all processes.

## Requirements / 需求

- Linux (Ubuntu 24.04 tested)
- Python 3.12+
- iPhone with Developer Mode enabled
- USB connection
- `sudo` access (tunneld requires root)

## Project Structure / 專案結構

```
src/
├── main.py                    # Entry point
├── gui/
│   ├── main_window.py         # Main window + layout
│   ├── control_panel.py       # Sidebar navigation + 4 sub-pages
│   ├── map_widget.py          # QtWebEngine + Leaflet bridge
│   ├── map_template.html      # Leaflet map HTML/JS
│   ├── style.qss              # Global dark theme
│   └── icons/                 # SVG vector icons (25)
├── core/
│   ├── device_manager.py      # iPhone connection (tunnel/RSD)
│   ├── location_controller.py # GPX generation + pymobiledevice3
│   ├── coordinate_utils.py    # Distance calculation
│   └── route_generator.py     # Route waypoint generation
└── utils/
    ├── config_manager.py      # config.yaml loader
    ├── logger.py              # Logging setup
    └── gpx_handler.py         # GPX file I/O
```
