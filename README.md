# iGPS — iPhone GPS Location Simulator for Linux

[English](#english) | [中文](README_zh.md)

A powerful desktop tool to control your iPhone's GPS location from Linux. Route simulation, area roaming, joystick control — all from an intuitive map-based UI.

> Based on [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator) by **Marcel Afsar**, rewritten and enhanced for Linux.

---

## Why iGPS?

| Feature | What it does for you |
|---|---|
| **Map-first design** | Click anywhere on the map to set waypoints — no typing coordinates |
| **Road-snapped routing** | Follows real streets via OSRM, not straight lines. Car, bike, walk, or highway |
| **Area roaming** | Your phone wanders naturally within a radius — walk away and it keeps moving |
| **Joystick micro-control** | Fine-tune position step by step with D-pad or keyboard arrows |
| **Freeze & pin** | Lock your phone at any spot. Stop mid-simulation without reverting to real GPS |
| **One-click start** | `./start.sh` handles everything: tunnel setup, port cleanup, GUI launch |
| **Auto-cleanup** | Close the GUI → all background processes automatically terminated |

## How It Works

```mermaid
flowchart TD
    A[./start.sh] -->|sudo verify + tunnel| B[iGPS GUI]

    B --> C[ControlPanel<br/>Route / Roam / Joystick / System]
    B --> D[Leaflet Map<br/>Click • Right-click • Markers]

    C --> E[LocationController]
    D --> E
    D --> F[RouteFetcher<br/>OSRM road routing]

    E --> G[GPX Builder<br/>GPX file generation]
    F --> G

    E --> H[DeviceManager<br/>RSD tunnel • Device pairing]

    H --> I[pymobiledevice3<br/>DVT protocol • CLI bridge]

    I -->|USB| J{{iPhone 13<br/>iOS 26.6}}

    style A fill:#4f46e5,color:#fff
    style B fill:#1e293b,color:#e2e8f0
    style J fill:#000,color:#34c759,stroke:#34c759
    style I fill:#6366f1,color:#fff
    style H fill:#475569,color:#e2e8f0
```

**Data flow:** User clicks map → coordinates → GPX waypoints generated → sent to iPhone via DVT protocol over RSD tunnel → iPhone GPS spoofed.

## What Makes It Different

- **Linux native** — fully tested on Ubuntu 24.04. No VM, no Wine, no macOS required
- **iOS 17+ ready** — uses Apple's latest DVT protocol via RSD tunnel (`pymobiledevice3`)
- **Collapsible sidebar** — 4 sub-pages with SVG icons. Collapse to save screen space
- **Right-click context menu** — inspect coordinates, then right-click again to teleport or set route points
- **Dark theme throughout** — every dropdown, menu, and panel stays dark even on Linux GTK
- **Self-diagnosing** — `./start.sh --check` verifies USB, Developer Mode, and tunnel status

## Quick Start

```bash
./start.sh           # One command to launch everything
./start.sh --check   # Diagnostics only
```

Close the GUI → all resources automatically freed.

## Requirements

- Linux (Ubuntu 24.04 tested)
- Python 3.12+
- iPhone with Developer Mode enabled + USB connection
- `sudo` access (tunneld requires root)

## Original Author

**Marcel Afsar** — [marcelafsar/iphone-location-simulator](https://github.com/marcelafsar/iphone-location-simulator)

## License

MIT
