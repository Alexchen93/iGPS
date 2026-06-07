# iGPS — iPhone GPS Location Simulator for Linux

[English](#english) | [中文](README_zh.md)

Based on [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator), rewritten and enhanced for Linux.

## Original Author

**Marcel Afsar** — [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)

## Features

- iPhone GPS location simulation via `pymobiledevice3` (iOS 17+ DVT / RSD tunnel)
- Route planning with address search (walking / cycling / driving / highway)
- Area roaming — continuous movement within a configurable radius
- Joystick directional micro-control
- Location freeze / reset / restore real GPS
- Collapsible sidebar with SVG vector icons
- Right-click context menu on map (teleport / set start / set destination)
- Dark-themed QComboBox dropdowns
- Auto-cleanup on GUI close (tunneld + port release via `trap EXIT`)

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| GUI | PyQt6 + QtWebEngine (Leaflet.js) |
| Device control | pymobiledevice3 |
| Map tiles | OpenStreetMap / CartoDB |
| Platform | Linux (tested on Ubuntu 24.04) |

## Quick Start

```bash
# Start (auto-setup RSD tunnel + launch GUI)
./start.sh

# Diagnostics only
./start.sh --check
```

Close the GUI window → all processes are automatically cleaned up.

## Requirements

- Linux (Ubuntu 24.04 tested)
- Python 3.12+
- iPhone with Developer Mode enabled
- USB connection
- `sudo` access (tunneld requires root)

## Project Structure

```
src/
├── main.py                    # Entry point
├── gui/
│   ├── main_window.py         # Main window + left/right split layout
│   ├── control_panel.py       # Sidebar nav + 4 sub-pages
│   ├── map_widget.py          # QtWebEngine + Leaflet JS bridge
│   ├── map_template.html      # Leaflet map HTML/JS
│   ├── style.qss              # Global dark theme stylesheet
│   └── icons/                 # 25 SVG vector icons
├── core/
│   ├── device_manager.py      # iPhone connection (RSD tunnel)
│   ├── location_controller.py # GPX generation + location execution
│   ├── coordinate_utils.py    # Geodesic distance calculation
│   └── route_generator.py     # Route waypoint generation
└── utils/
    ├── config_manager.py      # config.yaml loader
    ├── logger.py              # Loguru log setup
    └── gpx_handler.py         # GPX file I/O

tests/
└── test_imports.py            # Smoke tests (5/5)
```

## UI Layout

```
┌──────────────┬──────────────────────────┐
│  device bar  │                          │
│ [connect][◀] │                          │
├──────────────┤       🗺️ Map             │
│  sidebar nav │                          │
│  (4 pages)   │                          │
│  ⚫ 定位路線  │        [status card]     │
│  ⚫ 區域漫遊  │                          │
│  ⚫ 搖桿控制  │                          │
│  ⚫ 系統控制  │                          │
└──────────────┴──────────────────────────┘
   520px fixed       fills remaining
```

## License

MIT — see original [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)
