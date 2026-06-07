"""
Map Widget - Flicker-free Leaflet map served via localhost HTTP to bypass file:// tile restrictions
Created by Marcel Afsar (原作者)
"""

import json
import http.server
import socketserver
import threading
from pathlib import Path
from typing import List, Tuple, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtCore import QUrl, pyqtSignal, QTimer
from loguru import logger


class CustomWebEnginePage(QWebEnginePage):
    """Custom page that intercepts console.log messages from JavaScript"""
    def __init__(self, parent=None, console_callback=None):
        super().__init__(parent)
        self.console_callback = console_callback

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if self.console_callback:
            self.console_callback(message)
        # Only log JS errors, not routine messages
        if level.value >= QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel.value:
            logger.debug(f"JS error: {message} (line {lineNumber})")


class MapWidget(QWidget):
    """Full-screen Leaflet map widget — served from localhost to allow tile loading"""

    # Signals: emit (latitude, longitude)
    map_clicked = pyqtSignal(float, float)
    location_clicked = pyqtSignal(float, float)
    destination_clicked = pyqtSignal(float, float)
    coordinate_clicked = pyqtSignal(float, float)
    coordinate_context_menu_requested = pyqtSignal(float, float)
    mouse_moved = pyqtSignal(float, float)

    def __init__(self, parent=None, config=None):
        super().__init__(parent)

        if config:
            mc = config.get("map.default_center", {})
            self.center_lat = mc.get("latitude", 22.7826)
            self.center_lon = mc.get("longitude", 120.4038)
            self.zoom = config.get("map.default_zoom", 15)
        else:
            self.center_lat = 22.7826
            self.center_lon = 120.4038
            self.zoom = 15
        self._is_loaded = False
        self._pending_commands: List[str] = []
        self._map_server = None
        self._map_port: Optional[int] = None

        self._init_ui()
        self._start_map_server()
        self._load_map_template()

    def _init_ui(self):
        """Initialize the web view"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        # Allow localhost to access remote tile servers
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self.custom_page = CustomWebEnginePage(self.web_view, self._on_console_message)
        self.web_view.setPage(self.custom_page)
        layout.addWidget(self.web_view)

        self.web_view.loadFinished.connect(self._on_load_finished)

    def _start_map_server(self):
        """
        Start a local HTTP server to serve the map HTML and assets.
        Loading from http://localhost instead of file:// lets the browser
        make HTTPS tile requests without being blocked by Qt's security policy.
        """
        gui_dir = str(Path(__file__).parent)

        class SilentHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=gui_dir, **kwargs)

            def log_message(self, format, *args):
                pass  # Suppress HTTP server logs

        try:
            # Port 0 = OS picks a free port automatically
            server = socketserver.TCPServer(('127.0.0.1', 0), SilentHandler)
            server.allow_reuse_address = True
            self._map_port = server.server_address[1]
            self._map_server = server

            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            logger.info(f"Map HTTP server started on http://127.0.0.1:{self._map_port}/")
        except Exception as e:
            logger.error(f"Failed to start map HTTP server: {e}")
            self._map_port = None

    def _load_map_template(self):
        """Load map via localhost HTTP server (bypasses file:// HTTPS restrictions)"""
        if self._map_port:
            url = f"http://127.0.0.1:{self._map_port}/map_template.html"
            logger.debug(f"Loading map from: {url}")
            self.web_view.setUrl(QUrl(url))
        else:
            # Fallback: try local file
            template_path = Path(__file__).parent / "map_template.html"
            if template_path.exists():
                logger.warning("Map server unavailable — falling back to file:// (tiles may not load)")
                self.web_view.setUrl(QUrl.fromLocalFile(str(template_path.absolute())))
            else:
                logger.error(f"Map template not found: {template_path.absolute()}")

    def _on_load_finished(self, success: bool):
        """Handle page load completion"""
        if success:
            logger.info("Map view loaded successfully")
            self._is_loaded = True

            # Initialize map only (no default marker)
            self.run_js(f"initMap({self.center_lat}, {self.center_lon}, {self.zoom});")

            # Execute any pending commands
            for cmd in self._pending_commands:
                self.web_view.page().runJavaScript(cmd)
            self._pending_commands.clear()
        else:
            logger.error("Failed to load map view")

    def _on_console_message(self, message: str):
        """Receive JavaScript messages via console.log interception"""
        try:
            if message.startswith("CLICK:START:"):
                coords_str = message.split(":", 2)[2]
                lat, lon = map(float, coords_str.split(","))
                self.map_clicked.emit(lat, lon)
            elif message.startswith("DRAG:START:"):
                coords_str = message.split(":", 2)[2]
                lat, lon = map(float, coords_str.split(","))
                self.location_clicked.emit(lat, lon)
            elif message.startswith("CLICK:DEST:") or message.startswith("DRAG:DEST:"):
                coords_str = message.split(":", 2)[2]
                lat, lon = map(float, coords_str.split(","))
                self.destination_clicked.emit(lat, lon)
            elif message.startswith("CLICK:INSPECT:"):
                coords_str = message.split(":", 2)[2]
                lat, lon = map(float, coords_str.split(","))
                # If within ~200m of the last inspected spot, show context menu instead
                if hasattr(self, '_last_inspect'):
                    import math
                    dlat = lat - self._last_inspect[0]
                    dlon = lon - self._last_inspect[1]
                    dist = math.sqrt(dlat*dlat + dlon*dlon) * 111000
                    if dist < 200:
                        self.coordinate_context_menu_requested.emit(lat, lon)
                        return
                self._last_inspect = (lat, lon)
                self.coordinate_clicked.emit(lat, lon)
            elif message.startswith("MOUSE:MOVE:"):
                coords_str = message.split(":", 2)[2]
                lat, lon = map(float, coords_str.split(","))
                self.mouse_moved.emit(lat, lon)
        except Exception as e:
            logger.error(f"Error parsing map coordinates: {e}")

    def run_js(self, script: str):
        """Safely execute JavaScript"""
        if self._is_loaded:
            self.web_view.page().runJavaScript(script)
        else:
            self._pending_commands.append(script)

    def set_center(self, latitude: float, longitude: float, zoom: Optional[int] = None):
        """Pan the map to a location"""
        self.center_lat = latitude
        self.center_lon = longitude
        if zoom is not None:
            self.zoom = zoom
        self.run_js(f"panTo({latitude}, {longitude}, {zoom or 'null'});")

    def add_marker(self, latitude: float, longitude: float,
                   label: str = "", color: str = "blue", popup: Optional[str] = None):
        """Update the current phone position marker."""
        self.run_js(f"updateCurrentPosition({latitude}, {longitude});")

    def add_start_marker(self, latitude: float, longitude: float):
        """Mark a planned route start without moving the phone."""
        self.run_js(f"setStartPoint({latitude}, {longitude});")

    def set_destination_marker(self, latitude: float, longitude: float):
        """Mark a planned route destination."""
        self.run_js(f"setDestination({latitude}, {longitude});")

    def add_coordinate_marker(self, latitude: float, longitude: float):
        """Mark an inspected coordinate from right-click."""
        self.run_js(f"markCoordinate({latitude}, {longitude});")

    def clear_markers(self):
        """Clear planned overlays; current phone marker is preserved by clearMap()."""
        self.run_js("clearMap();")

    def add_route_line(self, coordinates: List[Tuple[float, float]],
                       color: str = "blue", weight: int = 3, opacity: float = 0.7):
        """Draw a route line on the map"""
        coords_json = json.dumps(coordinates)
        self.run_js(f"drawRoute('{coords_json}');")

    def clear_route_lines(self):
        """Clear all route lines"""
        self.run_js("clearMap();")

    def draw_radius_circle(self, latitude: float, longitude: float, radius_m: float):
        """Draw a visual radius circle for Area Roaming"""
        self.run_js(f"drawCircle({latitude}, {longitude}, {radius_m});")

    def clear_radius_circle(self):
        """Clear the visual radius circle"""
        self.run_js("clearCircle();")

    def refresh_map(self):
        """No-op for backwards compatibility"""
        self.run_js("if (map) { map.invalidateSize(false); }")

    def resizeEvent(self, event):
        """Tell Leaflet its viewport changed after Qt resizes the web view."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self.refresh_map)

    def show_route(self, waypoints: List[Tuple[float, float]],
                   show_markers: bool = True, auto_fit: bool = True):
        """Draw a route from start to end on the map"""
        if not waypoints:
            return
        if len(waypoints) > 1:
            end_lat, end_lon = waypoints[-1]
            self.run_js(f"setDestination({end_lat}, {end_lon});")
        coords_json = json.dumps(waypoints)
        self.run_js(f"drawRoute('{coords_json}');")

    def highlight_location(self, latitude: float, longitude: float):
        """Pan to a specific location"""
        self.set_center(latitude, longitude)

    def get_bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get approximate visible bounds"""
        delta = 0.01 * (15 - self.zoom)
        return (
            (self.center_lat - delta, self.center_lon - delta),
            (self.center_lat + delta, self.center_lon + delta)
        )

    def export_map(self, file_path: str) -> bool:
        """Export map (stub)"""
        logger.warning("Map export is not implemented.")
        return True

    def closeEvent(self, event):
        """Shut down HTTP server on close"""
        if self._map_server:
            self._map_server.shutdown()
        super().closeEvent(event)
