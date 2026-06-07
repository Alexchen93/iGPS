"""
Main Window - iGPS
Premium PyQt6 desktop app with WASD joystick, phone detection, and route simulation.
Created by Marcel Afsar (原作者)
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QStatusBar, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QFont, QIcon
from loguru import logger

from core.device_manager import DeviceManager
from core.location_controller import LocationController
from pathlib import Path

_ICONS = Path(__file__).parent / "icons"
from gui.control_panel import ControlPanel
from gui.map_widget import MapWidget
from utils.config_manager import ConfigManager


class WalkSimulationThread(QThread):
    """Runs route simulation in a background thread to keep UI responsive"""
    
    progress_updated = pyqtSignal(float, float, float)  # lat, lon, progress
    route_calculated = pyqtSignal(float, float)  # total_dist, total_time
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, location_controller, start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops: bool, transport_mode: str = 'driving'):
        super().__init__()
        self.location_controller = location_controller
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.speed = speed
        self.interval = interval
        self.simulate_stops = simulate_stops
        self.transport_mode = transport_mode

    def run(self):
        try:
            success = self.location_controller.simulate_walk(
                self.start_lat,
                self.start_lon,
                self.end_lat,
                self.end_lon,
                self.speed,
                self.interval,
                self.progress_updated.emit,
                self.simulate_stops,
                self.transport_mode,
                self.route_calculated.emit
            )
            if success:
                self.finished.emit()
            else:
                self.error.emit("Route simulation was interrupted")
        except Exception as e:
            self.error.emit(str(e))


class RoamSimulationThread(QThread):
    """Runs area roam simulation in a background thread"""
    
    progress_updated = pyqtSignal(float, float, float)  # lat, lon, progress
    route_calculated = pyqtSignal(float, float)  # total_dist, total_time
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, location_controller, center_lat, center_lon, radius_m, duration_mins, speed, transport_mode):
        super().__init__()
        self.location_controller = location_controller
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_m = radius_m
        self.duration_mins = duration_mins
        self.speed = speed
        self.transport_mode = transport_mode

    def run(self):
        try:
            success = self.location_controller.simulate_roam(
                self.center_lat,
                self.center_lon,
                self.radius_m,
                self.duration_mins,
                self.speed,
                1.0,
                self.progress_updated.emit,
                self.transport_mode,
                self.route_calculated.emit
            )
            if success:
                self.finished.emit()
            else:
                self.error.emit("Roam simulation was interrupted")
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.config = ConfigManager()
        self.device_manager = DeviceManager()
        self.location_controller = None
        self.walk_thread = None
        self.total_dist = 0.0
        self.total_time = 0.0
        self.is_frozen = False
        self._map_pick_mode = None
        self._run_state = "就緒"
        self._last_runtime_position = None
        
        self._init_ui()
        self._load_stylesheet()
        self._setup_status_check()
        
    def _init_ui(self):
        """Initialize the UI with sidebar + map layout"""
        self.setWindowTitle("iGPS 定位控制台")
        self.resize(1200, 850)
        self.setMinimumSize(1100, 700)

        # Central widget with horizontal layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        root_layout = QHBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── LEFT: Sidebar panel ──
        self.left_container = QWidget()
        self.left_container.setFixedWidth(520)
        self.left_container.setMinimumWidth(64)
        self.left_container.setStyleSheet("background: #141519;")
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Device bar (top of sidebar)
        self.device_bar = self._create_device_bar()
        self.device_bar.setFixedHeight(60)
        left_layout.addWidget(self.device_bar)

        # Control panel (fills remaining sidebar space directly, no scroll wrapper)
        self.control_panel = ControlPanel()
        left_layout.addWidget(self.control_panel, 1)

        root_layout.addWidget(self.left_container)

        # ── RIGHT: Map area ──
        self.map_container = QWidget()
        map_layout = QGridLayout(self.map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)

        # Map widget fills the container
        self.map_widget = MapWidget(self.map_container)
        map_layout.addWidget(self.map_widget, 0, 0)

        root_layout.addWidget(self.map_container, 1)

        # Keep route/roam progress centered without showing the old floating controls.
        self._map_auto_track = True

        # Map status card: layout-owned overlay so it follows window resize.
        self.map_status_shell = QWidget(self.map_container)
        status_shell_layout = QVBoxLayout(self.map_status_shell)
        status_shell_layout.setContentsMargins(0, 0, 16, 16)
        status_shell_layout.setSpacing(0)

        self.map_status_card = QWidget(self.map_status_shell)
        self.map_status_card.setObjectName("map_status_card")
        self.map_status_card.setFixedWidth(320)

        status_layout = QVBoxLayout(self.map_status_card)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(5)

        self.map_status_title = QLabel("地圖狀態")
        self.map_status_title.setObjectName("map_status_title")
        status_layout.addWidget(self.map_status_title)

        self.mouse_coord_label = QLabel("滑鼠：--, --")
        self.mouse_coord_label.setObjectName("map_status_line")
        status_layout.addWidget(self.mouse_coord_label)

        self.runtime_status_label = QLabel("執行：就緒")
        self.runtime_status_label.setObjectName("map_status_line")
        status_layout.addWidget(self.runtime_status_label)

        self.interrupt_pin_btn = QPushButton("中斷並固定當前位置")
        self.interrupt_pin_btn.setObjectName("interrupt_pin_btn")
        self.interrupt_pin_btn.setIcon(QIcon(str(_ICONS / "stop.svg")))
        self.interrupt_pin_btn.clicked.connect(self._on_interrupt_and_pin)
        self.interrupt_pin_btn.hide()
        status_layout.addWidget(self.interrupt_pin_btn)
        status_shell_layout.addWidget(
            self.map_status_card,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        map_layout.addWidget(
            self.map_status_shell,
            0,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        map_layout.setRowStretch(0, 1)
        map_layout.setColumnStretch(0, 1)

        # Connect signals
        self.control_panel.set_location_requested.connect(self._on_set_location)
        self.control_panel.set_destination_requested.connect(self._on_destination_set)
        self.control_panel.map_pick_requested.connect(self._on_map_pick_requested)
        self.control_panel.map_overlays_clear_requested.connect(self._on_clear_map_overlays)
        self.control_panel.walk_simulation_requested.connect(self._on_walk_simulation)
        self.control_panel.stop_requested.connect(self._on_stop)
        self.control_panel.clear_requested.connect(self._on_clear)
        self.control_panel.freeze_requested.connect(self._on_freeze_location)
        self.control_panel.joystick_step_requested.connect(self._on_joystick_step)
        self.control_panel.roam_requested.connect(self._on_roam_requested)
        self.control_panel.roam_radius_changed.connect(self._on_roam_radius_changed)
        self.map_widget.map_clicked.connect(self._on_map_clicked)
        self.map_widget.location_clicked.connect(self._on_start_marker_dragged)
        self.map_widget.destination_clicked.connect(self._on_map_destination_clicked)
        self.map_widget.coordinate_clicked.connect(self._on_map_coordinate_clicked)
        self.map_widget.coordinate_context_menu_requested.connect(self._on_map_context_menu)
        self.map_widget.mouse_moved.connect(self._on_map_mouse_moved)

        # Enable keyboard focus for WASD
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        # Disable controls until connected
        self.control_panel.set_enabled(False)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就緒 - 請連接 iPhone 後開始")

        # Load is_frozen state
        self.is_frozen = self.config.get("features.is_frozen", False)
        if self.is_frozen:
            self.control_panel.set_freeze_state(is_frozen=True, can_unfreeze=False)
            self.device_status_label.setText("手機未連線（位置已凍結）")
            self.device_status_label.setStyleSheet(
                "font-weight: 600; font-size: 12px; color: #ff3b30; border: none; background: transparent;"
            )
            self.connect_btn.setText("等待中...")
            self.connect_btn.setEnabled(False)


    def _create_device_bar(self) -> QWidget:
        """Create the floating device connection bar with phone info"""
        bar = QWidget()
        bar.setObjectName("device_bar")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        
        # Device icon + status
        self.device_status_label = QLabel("尚未連接裝置")
        self.device_status_label.setObjectName("device_status_label")
        self.device_status_label.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #ff453a; border: none; background: transparent;"
        )
        layout.addWidget(self.device_status_label, 1)
        
        # Battery label (hidden until connected)
        self.battery_label = QLabel("")
        self.battery_label.setObjectName("battery_label")
        self.battery_label.setStyleSheet(
            "font-size: 11px; color: #b0b3c6; border: none; background: transparent;"
        )
        self.battery_label.hide()
        layout.addWidget(self.battery_label)
        
        # Direct map-to-phone location button
        self.direct_loc_btn = QPushButton("直接定位")
        self.direct_loc_btn.setObjectName("direct_loc_btn")
        self.direct_loc_btn.setIcon(QIcon(str(_ICONS / "target.svg")))
        self.direct_loc_btn.setIconSize(QSize(16, 16))
        self.direct_loc_btn.setToolTip("按下後，在地圖左鍵點擊即可直接設定手機位置")
        self.direct_loc_btn.clicked.connect(self._on_direct_location_requested)
        self.direct_loc_btn.setFixedWidth(100)
        layout.addWidget(self.direct_loc_btn)

        # Connect button
        self.connect_btn = QPushButton("連線")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.clicked.connect(self._on_connect)
        self.connect_btn.setFixedWidth(100)
        layout.addWidget(self.connect_btn)
        

        # Toggle sidebar collapse
        self.toggle_menu_btn = QPushButton()
        self.toggle_menu_btn.setObjectName("toggle_menu_btn")
        self.toggle_menu_btn.setFixedSize(32, 32)
        self.toggle_menu_btn.setIconSize(QSize(18, 18))
        self.toggle_menu_btn.setIcon(QIcon(str(_ICONS / "sidebar-collapse.svg")))
        self.toggle_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_menu_btn.setToolTip("隱藏左側欄")
        self.toggle_menu_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                color: #A0AEC0;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(99,102,241,0.2);
                border-color: rgba(99,102,241,0.4);
                color: #C7D2FE;
            }
        """)
        self.toggle_menu_btn.clicked.connect(self._on_toggle_menu)
        layout.addWidget(self.toggle_menu_btn)

        return bar

    def _on_toggle_menu(self):
        """Toggle between full and icon-only collapsed sidebar"""
        is_collapsed = self.left_container.width() < 100
        if is_collapsed:
            self.left_container.setFixedWidth(520)
            self.device_status_label.show()
            self.direct_loc_btn.show()
            self.connect_btn.show()
            self.toggle_menu_btn.setIcon(QIcon(str(_ICONS / "sidebar-collapse.svg")))
            self.toggle_menu_btn.setToolTip("隱藏左側欄")
            self.control_panel.set_collapsed(False)
        else:
            self.left_container.setFixedWidth(64)
            self.device_status_label.hide()
            self.battery_label.hide()
            self.direct_loc_btn.hide()
            self.connect_btn.hide()
            self.toggle_menu_btn.setIcon(QIcon(str(_ICONS / "sidebar-expand.svg")))
            self.toggle_menu_btn.setToolTip("展開左側欄")
            self.control_panel.set_collapsed(True)

    def _load_stylesheet(self):
        """Load QSS stylesheet"""
        qss_path = Path(__file__).parent / "style.qss"
        if qss_path.exists():
            try:
                self.setStyleSheet(qss_path.read_text(encoding='utf-8'))
                logger.info("Stylesheet applied")
            except Exception as e:
                logger.error(f"Failed to load stylesheet: {e}")
    
    def _setup_status_check(self):
        """Setup timer for periodic device status checks"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_device_status)
        self.status_timer.start(3000)  # Check every 3 seconds
    
    def _check_device_status(self):
        """Check device connection status and update UI"""
        if self.device_manager.is_connected():
            if not self.device_manager.check_connection_fast():
                self._handle_device_unplugged()
                return
                
            device_info = self.device_manager.get_device_info()
            if device_info:
                name = device_info.get('name', 'iPhone')
                model = device_info.get('model', '')
                version = device_info.get('version', '')
                battery = device_info.get('battery_level')
                
                if getattr(self, 'is_frozen', False):
                    status = f"{name}（位置已凍結）"
                    self.device_status_label.setText(status)
                    self.device_status_label.setStyleSheet(
                        "font-weight: 600; font-size: 12px; color: #6366F1; border: none; background: transparent;"
                    )
                else:
                    status = f"{name}"
                    if model and model != name:
                        status += f"  •  {model}"
                    if version:
                        status += f"  •  {version}"
                        
                    self.device_status_label.setText(status)
                    self.device_status_label.setStyleSheet(
                        "font-weight: 600; font-size: 12px; color: #34c759; border: none; background: transparent;"
                    )
                
                # Battery indicator
                if battery is not None:
                    bat_icon = "[|||]" if battery > 20 else "[!]"
                    self.battery_label.setText(f"{bat_icon} {battery}%")
                    self.battery_label.setStyleSheet(
                        f"font-size: 11px; color: {'#34c759' if battery > 20 else '#ff453a'}; "
                        "font-weight: 600; border: none; background: transparent;"
                    )
                    self.battery_label.show()
                else:
                    self.battery_label.hide()
        else:
            if getattr(self, 'is_frozen', False):
                self.device_status_label.setText("手機未連線（位置已凍結）")
                self.device_status_label.setStyleSheet(
                    "font-weight: 600; font-size: 12px; color: #ff3b30; border: none; background: transparent;"
                )
                self.battery_label.hide()
                self.connect_btn.setText("等待中...")
                self.connect_btn.setEnabled(False)
                self.control_panel.set_enabled(False)
                self.control_panel.set_freeze_state(is_frozen=True, can_unfreeze=False)
                
                # Try to detect if the device was plugged back in (lightweight check only)
                try:
                    import requests as _req
                    resp = _req.get("http://127.0.0.1:49151/", timeout=1.0)
                    tunnels = resp.json()
                    if tunnels and isinstance(tunnels, dict) and len(tunnels) > 0:
                        logger.info("Frozen device detected in tunnels. Attempting reconnect...")
                        self.statusBar.showMessage("偵測到已凍結裝置，正在重新連線...")
                        
                        from PyQt6.QtWidgets import QApplication
                        QApplication.processEvents()
                        
                        if self.device_manager.connect():
                            self.location_controller = LocationController(self.device_manager)
                            self.control_panel.set_enabled(True)
                            self.control_panel.set_freeze_state(is_frozen=True, can_unfreeze=True)
                            self.connect_btn.setText("中斷連線")
                            self.connect_btn.setEnabled(True)
                            self.statusBar.showMessage("裝置已重新連線，可解除凍結。")
                except Exception:
                    pass  # silent — device not plugged in yet
            else:
                self.device_status_label.setText("尚未連接裝置")
                self.device_status_label.setStyleSheet(
                    "font-weight: 600; font-size: 12px; color: #ff453a; border: none; background: transparent;"
                )
                self.battery_label.hide()
                self.connect_btn.setText("連線")
                self.connect_btn.setEnabled(True)
                self.control_panel.set_enabled(False)
            
    def _on_connect(self):
        """Handle connect/disconnect button"""
        if self.device_manager.is_connected():
            # Disconnect
            if self.location_controller and not getattr(self, 'is_frozen', False):
                self.location_controller.clear_location()
            self.device_manager.disconnect()
            self.location_controller = None
            self.connect_btn.setText("連線")
            self.control_panel.set_enabled(False)
            self.battery_label.hide()
            self.statusBar.showMessage("已中斷裝置連線")
            logger.info("Disconnected from device")
        else:
            # Connect
            self.statusBar.showMessage("正在連接 iPhone...")
            self.connect_btn.setText("...")
            self.connect_btn.setEnabled(False)
            
            # Force UI update before blocking call
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            if self.device_manager.connect():
                self.location_controller = LocationController(self.device_manager)
                self.connect_btn.setText("中斷連線")
                self.connect_btn.setEnabled(True)
                self.control_panel.set_enabled(True)
                
                device_info = self.device_manager.get_device_info()
                name = device_info.get('name', 'iPhone') if device_info else 'iPhone'
                self.statusBar.showMessage(f"已連接到 {name}")
                
                # Do NOT automatically drop a marker on the map so it stays blank
                # until the user specifically searches or clicks somewhere.
                self.statusBar.showMessage(f"已連接到 {name}。請搜尋地址或點擊地圖設定位置。")
                
                logger.info("Device connected successfully")
            else:
                self.connect_btn.setText("連線")
                self.connect_btn.setEnabled(True)
                self.statusBar.showMessage("連線失敗")
                QMessageBox.warning(
                    self,
                    "連線錯誤",
                    "無法連接你的 iPhone。\n\n"
                    "請檢查：\n"
                    "1. iPhone 已透過 USB 連接\n"
                    "2. 已開啟 Developer Mode\n"
                    "   （設定 > 隱私權與安全性 > 開發者模式）\n"
                    "3. 手機螢幕已解鎖，且已按「信任」\n"
                    "4. Linux 上 tunneld 已用 sudo 啟動"
                )
                logger.error("Device connection failed")
    
    def _on_set_location(self, lat: float, lon: float):
        """Teleport to location"""
        if not self.location_controller:
            return
        
        if self.location_controller.set_location(lat, lon):
            self.map_widget.set_center(lat, lon)
            self.map_widget.add_marker(lat, lon)
            self.statusBar.showMessage(f"已移動到 ({lat:.6f}, {lon:.6f})")
            logger.info(f"Location set: ({lat}, {lon})")
        else:
            QMessageBox.critical(self, "錯誤", "設定位置失敗，請檢查 RSD tunnel 連線。")
            
    def _on_direct_location_requested(self):
        """Arm the next map click to immediately set the phone location."""
        self._map_pick_mode = "direct"
        self.statusBar.showMessage("請在地圖上左鍵點選要直接定位的位置")

    def _on_map_pick_requested(self, mode: str):
        """Arm the next left-click on the map to select a route/roam point."""
        self._map_pick_mode = mode
        labels = {"start": "起點", "destination": "終點", "roam": "漫遊中心"}
        label = labels.get(mode, "位置")
        self.statusBar.showMessage(f"請在地圖上左鍵點選{label}")

    def _on_map_clicked(self, lat: float, lon: float):
        """Handle map left-click only after the user arms a pick mode."""
        if self._map_pick_mode == "direct":
            self.control_panel.set_coordinates(lat, lon)
            self._map_pick_mode = None
            if self.device_manager.is_connected() and self.location_controller:
                self._on_set_location(lat, lon)
            else:
                self.statusBar.showMessage("尚未連接手機，無法直接定位")
        elif self._map_pick_mode == "start":
            self.control_panel.set_coordinates(lat, lon)
            self.map_widget.add_start_marker(lat, lon)
            self.statusBar.showMessage(f"已標示起點：({lat:.6f}, {lon:.6f})")
            self._map_pick_mode = None
        elif self._map_pick_mode == "destination":
            self.control_panel.set_end_location(lat, lon)
            self.map_widget.set_destination_marker(lat, lon)
            self.statusBar.showMessage(f"已標示終點：({lat:.6f}, {lon:.6f})")
            self._map_pick_mode = None
        elif self._map_pick_mode == "roam":
            self.control_panel.set_coordinates(lat, lon)
            self.map_widget.add_start_marker(lat, lon)
            self.map_widget.draw_radius_circle(lat, lon, float(self.control_panel.radius_slider.value()))
            self.statusBar.showMessage(f"已標示漫遊中心：({lat:.6f}, {lon:.6f})")
            self._map_pick_mode = None
        else:
            self.statusBar.showMessage("請先按上方「直接定位」，或左側「地圖選起點 / 終點 / 漫遊中心」")

    def _on_start_marker_dragged(self, lat: float, lon: float):
        """Dragging the active phone marker keeps the old direct-move behavior."""
        self.control_panel.set_coordinates(lat, lon)
        self.statusBar.showMessage(f"已移動起點：({lat:.6f}, {lon:.6f})")
        if self.device_manager.is_connected():
            self._on_set_location(lat, lon)

    def _on_map_destination_clicked(self, lat: float, lon: float):
        """Handle destination marker drag."""
        self.control_panel.set_end_location(lat, lon)
        self.map_widget.set_destination_marker(lat, lon)
        self.statusBar.showMessage(f"已調整終點：({lat:.6f}, {lon:.6f})")

    def _on_map_context_menu(self, lat: float, lon: float):
        """Right-click on the same inspected spot: show context menu."""
        menu = QMenu(self.map_widget)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1d28;
                border: 1px solid #2D3143;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                color: #E2E8F0;
                background-color: transparent;
                padding: 9px 28px;
                margin: 2px 4px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: rgba(99,102,241,0.35);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.06);
                margin: 4px 8px;
            }
        """)

        # Always: teleport phone
        tel_action = menu.addAction("手機定位到這裡")
        tel_action.triggered.connect(lambda: self._do_direct_teleport(lat, lon))

        menu.addSeparator()

        # Page-specific options
        active_idx = self.control_panel.stack.currentIndex()
        # 定位路線 page (index 0)
        if active_idx == 0:
            start_action = menu.addAction("設為起點")
            start_action.triggered.connect(lambda: self._do_set_start(lat, lon))
            dest_action = menu.addAction("設為終點")
            dest_action.triggered.connect(lambda: self._do_set_destination(lat, lon))
        # 區域漫遊 page (index 1)
        elif active_idx == 1:
            roam_action = menu.addAction("設為漫遊中心")
            roam_action.triggered.connect(lambda: self._do_set_roam_center(lat, lon))

        menu.exec(self.map_widget.mapToGlobal(QPoint(int(self.map_widget.rect().center().x()), int(self.map_widget.rect().center().y()))))

    def _do_direct_teleport(self, lat, lon):
        self.control_panel.set_coordinates(lat, lon)
        if self.device_manager.is_connected() and self.location_controller:
            self._on_set_location(lat, lon)
            self.statusBar.showMessage(f"已定位到 ({lat:.6f}, {lon:.6f})")
        else:
            self.statusBar.showMessage("尚未連接手機，無法直接定位")

    def _do_set_start(self, lat, lon):
        self.control_panel.set_coordinates(lat, lon)
        self.map_widget.add_start_marker(lat, lon)
        self.statusBar.showMessage(f"已標示起點：({lat:.6f}, {lon:.6f})")

    def _do_set_destination(self, lat, lon):
        self.control_panel.set_end_location(lat, lon)
        self.map_widget.set_destination_marker(lat, lon)
        self.statusBar.showMessage(f"已標示終點：({lat:.6f}, {lon:.6f})")

    def _do_set_roam_center(self, lat, lon):
        self.control_panel.set_coordinates(lat, lon)
        self.map_widget.add_start_marker(lat, lon)
        self.map_widget.draw_radius_circle(lat, lon, float(self.control_panel.radius_slider.value()))
        self.statusBar.showMessage(f"已標示漫遊中心：({lat:.6f}, {lon:.6f})")

    def _on_map_coordinate_clicked(self, lat: float, lon: float):
        """Right-click only inspects and marks a coordinate; it never moves the phone."""
        self.map_widget.add_coordinate_marker(lat, lon)
        self.statusBar.showMessage(f"座標標示：({lat:.6f}, {lon:.6f})")

    def _on_map_mouse_moved(self, lat: float, lon: float):
        """Update the map status panel with the current cursor coordinate."""
        self.mouse_coord_label.setText(f"滑鼠：{lat:.6f}, {lon:.6f}")

    def _set_runtime_state(self, text: str):
        self._run_state = text
        self.runtime_status_label.setText(f"執行：{text}")
        is_interruptible = text.startswith("路線模擬中") or text.startswith("區域漫遊中") or text.startswith("執行中") or text == "暫停等待中"
        self.interrupt_pin_btn.setVisible(is_interruptible)

    def _on_destination_set(self, lat: float, lon: float):
        """Update destination marker visually from control panel"""
        self.map_widget.set_destination_marker(lat, lon)

    def _on_clear_map_overlays(self):
        """Clear planned map overlays while keeping the current phone marker."""
        self._map_pick_mode = None
        self.map_widget.clear_markers()
        self.statusBar.showMessage("已清除地圖標示，只保留目前位置")
            
    def _on_walk_simulation(self, start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops, transport_mode='driving'):
        """Start route simulation"""
        if not self.location_controller:
            QMessageBox.warning(self, "錯誤", "尚未連接裝置")
            return

        self.total_dist = 0.0
        self.total_time = 0.0

        # Set starting position on device and map
        self._last_runtime_position = (start_lat, start_lon)
        self.location_controller.set_location(start_lat, start_lon)
        self.map_widget.add_marker(start_lat, start_lon)

        # Pre-fetch OSRM road route to show on map before movement begins
        try:
            route_data = self.location_controller._get_road_route(
                start_lat, start_lon, end_lat, end_lon, transport_mode
            )
            if route_data and route_data.get('geometry'):
                coords = route_data['geometry']['coordinates']
                road_waypoints = [(lat, lon) for lon, lat in coords]
                self.map_widget.show_route(road_waypoints, show_markers=True, auto_fit=True)
            else:
                # Straight-line fallback
                waypoints = [(start_lat, start_lon), (end_lat, end_lon)]
                self.map_widget.show_route(waypoints, show_markers=True, auto_fit=True)
        except Exception as e:
            logger.warning(f"Could not pre-fetch route for map preview: {e}")
            waypoints = [(start_lat, start_lon), (end_lat, end_lon)]
            self.map_widget.show_route(waypoints, show_markers=True, auto_fit=True)

        # Run simulation in background thread
        self.walk_thread = WalkSimulationThread(
            self.location_controller,
            start_lat, start_lon,
            end_lat, end_lon,
            speed, interval,
            simulate_stops,
            transport_mode
        )
        self.walk_thread.progress_updated.connect(self._on_walk_progress)
        self.walk_thread.route_calculated.connect(self._on_walk_route_calculated)
        self.walk_thread.finished.connect(self._on_walk_finished)
        self.walk_thread.error.connect(self._on_walk_error)
        self.walk_thread.start()

        mode_labels = {
            'walking': '步行', 'cycling': '騎車',
            'driving': '市區開車', 'highway': '高速公路'
        }
        label = mode_labels.get(transport_mode, transport_mode)
        self._set_runtime_state(f"路線模擬中 - {label} {speed:.0f} km/h")
        self.statusBar.showMessage(f"正在模擬路線 - {label}，速度 {speed:.0f} km/h")
        logger.info(f"Route simulation started: {speed} km/h, mode={transport_mode}, traffic={simulate_stops}")
    
    def _on_roam_radius_changed(self, lat: float, lon: float, radius: float):
        """Draw radius circle on map"""
        self.map_widget.draw_radius_circle(lat, lon, radius)

    def _on_roam_requested(self, lat, lon, radius, duration, speed, mode):
        if not self.location_controller:
            QMessageBox.warning(self, "錯誤", "尚未連接裝置")
            return

        self.total_dist = 0.0
        self.total_time = 0.0

        self._last_runtime_position = (lat, lon)
        self.location_controller.set_location(lat, lon)
        self.map_widget.add_marker(lat, lon)
        self.map_widget.draw_radius_circle(lat, lon, radius)

        self.walk_thread = RoamSimulationThread(
            self.location_controller,
            lat, lon, radius, duration, speed, mode
        )
        self.walk_thread.progress_updated.connect(self._on_walk_progress)
        self.walk_thread.route_calculated.connect(self._on_walk_route_calculated)
        self.walk_thread.finished.connect(self._on_walk_finished)
        self.walk_thread.error.connect(self._on_walk_error)
        self.walk_thread.start()

        self._set_runtime_state(f"區域漫遊中 - 半徑 {radius}m")
        self.statusBar.showMessage(f"區域漫遊中 - 半徑 {radius}m，時間 {duration} 分鐘")
        logger.info(f"Roam simulation started: {radius}m radius, {duration} mins")
    
    def _on_walk_route_calculated(self, total_dist: float, total_time: float):
        """Called when total route distance and duration are calculated"""
        self.total_dist = total_dist
        self.total_time = total_time

    def _on_walk_progress(self, lat: float, lon: float, progress: float):
        """Update UI with simulation progress"""
        self._last_runtime_position = (lat, lon)
        self.map_widget.add_marker(lat, lon)
        self.control_panel.set_coordinates(lat, lon)
        
        # Auto-center map while simulations are running.
        if self._map_auto_track and progress >= 0:
            self.map_widget.set_center(lat, lon)
        
        if progress < 0:
            self._set_runtime_state("暫停等待中")
            self.statusBar.showMessage(f"等待紅綠燈或路口停頓... ({lat:.6f}, {lon:.6f})")
        else:
            self._set_runtime_state(f"執行中 {progress*100:.0f}%")
            self.statusBar.showMessage(f"{progress*100:.0f}% - ({lat:.6f}, {lon:.6f})")
    
    def _on_walk_finished(self):
        """Route or roam simulation completed."""
        self.map_widget.clear_markers()
        self._set_runtime_state("完成")
        self.statusBar.showMessage("模擬完成，已清除地圖規劃標示")
        QMessageBox.information(self, "完成", "模擬已完成，地圖只保留目前位置。")
    
    def _on_walk_error(self, error_msg: str):
        self._set_runtime_state("錯誤")
        self.statusBar.showMessage(f"錯誤：{error_msg}")
        QMessageBox.critical(self, "錯誤", f"發生錯誤：\n{error_msg}")

    def _on_interrupt_and_pin(self):
        """Stop the current simulation and keep the phone at the latest known position."""
        pinned = self._last_runtime_position
        if not pinned and self.location_controller:
            pinned = self.location_controller.get_current_location()
        if not pinned:
            pinned = (self.control_panel.lat_input.value(), self.control_panel.lon_input.value())

        if self.location_controller:
            self.location_controller.stop_simulation()
        if self.walk_thread and self.walk_thread.isRunning():
            self.walk_thread.terminate()
            self.walk_thread.wait()

        lat, lon = pinned
        if self.location_controller and self.device_manager.is_connected():
            self.location_controller.set_location(lat, lon)
        self.control_panel.set_coordinates(lat, lon)
        self.map_widget.add_marker(lat, lon)
        self.map_widget.clear_markers()
        self._set_runtime_state(f"已中斷並固定 {lat:.6f}, {lon:.6f}")
        self.statusBar.showMessage(f"已中斷並固定當前位置：({lat:.6f}, {lon:.6f})")
        
    def _on_focus_location(self):
        """Pan map back to current spoofed location"""
        if not self.location_controller:
            return
        loc = self.location_controller.get_current_location()
        if loc:
            self.map_widget.set_center(loc[0], loc[1])
            self.statusBar.showMessage(f"地圖已聚焦到：({loc[0]:.6f}, {loc[1]:.6f})")
            
    def _on_joystick_step(self, direction: str):
        """Handle D-Pad / WASD joystick step"""
        if not self.location_controller:
            return
            
        current_loc = self.location_controller.get_current_location()
        if not current_loc:
            current_loc = (self.control_panel.lat_input.value(), self.control_panel.lon_input.value())
            
        lat, lon = current_loc
        
        # Scale step size based on speed setting
        speed = self.control_panel.speed_slider.value() / 10.0
        step_factor = max(0.00003, (speed / 10.0) * 0.0001)
        
        if direction == "N":
            lat += step_factor
        elif direction == "S":
            lat -= step_factor
        elif direction == "E":
            lon += step_factor
        elif direction == "W":
            lon -= step_factor
            
        if self.location_controller.set_location(lat, lon):
            self.map_widget.add_marker(lat, lon)
            self.map_widget.set_center(lat, lon)
            self.control_panel.set_coordinates(lat, lon)
            self.statusBar.showMessage(f"已移動到 ({lat:.6f}, {lon:.6f})")
            
    def _on_stop(self):
        """Stop simulation"""
        self.map_widget.clear_radius_circle()
        if self.location_controller:
            self.location_controller.stop_simulation()
            if self.walk_thread and self.walk_thread.isRunning():
                self.walk_thread.terminate()
                self.walk_thread.wait()
            self._set_runtime_state("已停止")
            self.statusBar.showMessage("模擬已停止")
    
    def _on_clear(self):
        """Reset GPS to real location"""
        self._on_stop()
        if self.location_controller:
            self.statusBar.showMessage("正在重置 GPS...")
            if self.location_controller.clear_location():
                self.map_widget.clear_markers()
                self.map_widget.clear_route_lines()
                self.statusBar.showMessage("GPS 已重置為真實位置，地圖已清除。")

    def _on_freeze_location(self):
        """Handle 'Freeze Location' / 'Unfreeze GPS' button click"""
        if getattr(self, 'is_frozen', False):
            self._on_unfreeze()
            return
            
        if not self.location_controller or not self.device_manager.is_connected():
            QMessageBox.warning(self, "錯誤", "尚未連接裝置")
            return
            
        lat = self.control_panel.lat_input.value()
        lon = self.control_panel.lon_input.value()
        
        self.statusBar.showMessage(f"正在凍結 GPS 到 ({lat:.6f}, {lon:.6f})...")
        if self.location_controller.set_location(lat, lon):
            self.is_frozen = True
            self.config.set('features.is_frozen', True)
            self.config.save()
            
            self.map_widget.set_center(lat, lon)
            self.map_widget.add_marker(lat, lon)
            self.control_panel.set_freeze_state(is_frozen=True, can_unfreeze=True)
            
            QMessageBox.information(
                self,
                "位置已凍結",
                "位置已成功凍結！\n\n"
                "現在可以安全拔除 USB 線。模擬位置會維持在同一個座標，"
                "直到你重新接上手機並點擊「解除 GPS 凍結」，或重新啟動手機。"
            )
            
            device_info = self.device_manager.get_device_info()
            name = device_info.get('name', 'iPhone') if device_info else 'iPhone'
            self.device_status_label.setText(f"{name}（位置已凍結）")
            self.device_status_label.setStyleSheet(
                "font-weight: 600; font-size: 12px; color: #6366F1; border: none; background: transparent;"
            )
            self.statusBar.showMessage(f"位置已凍結於 ({lat:.6f}, {lon:.6f})，可安全拔線。")
        else:
            QMessageBox.critical(self, "錯誤", "凍結位置失敗，請檢查連線。")
            
    def _on_unfreeze(self):
        """Unfreeze GPS and restore real location"""
        if not self.location_controller or not self.device_manager.is_connected():
            QMessageBox.warning(self, "錯誤", "尚未連接裝置，請先接上手機。")
            return
            
        self.statusBar.showMessage("正在解除 GPS 凍結...")
        if self.location_controller.clear_location():
            self.is_frozen = False
            self.config.set('features.is_frozen', False)
            self.config.save()
            
            self.map_widget.clear_markers()
            self.map_widget.clear_route_lines()
            self.control_panel.set_freeze_state(is_frozen=False)
            self.control_panel.set_enabled(True)
            self.connect_btn.setText("中斷連線")
            self.connect_btn.setEnabled(True)
            
            QMessageBox.information(
                self,
                "GPS 已解除凍結",
                "位置已成功解除凍結。\n"
                "現在已恢復真實 GPS 座標。"
            )
            
            device_info = self.device_manager.get_device_info()
            if device_info:
                name = device_info.get('name', 'iPhone')
                model = device_info.get('model', '')
                version = device_info.get('version', '')
                status = f"{name}"
                if model and model != name:
                    status += f"  •  {model}"
                if version:
                    status += f"  •  {version}"
                self.device_status_label.setText(status)
                self.device_status_label.setStyleSheet(
                    "font-weight: 600; font-size: 12px; color: #34c759; border: none; background: transparent;"
                )
            self.statusBar.showMessage("GPS 已解除凍結，真實位置已恢復。")
        else:
            QMessageBox.critical(self, "錯誤", "解除 GPS 凍結失敗。")
            
    def _handle_device_unplugged(self):
        """Clean up state on host when device is physically disconnected"""
        logger.warning("Device unplugged. Cleaning up session...")
        
        if self.location_controller:
            self.location_controller.stop_simulation()
            
        self.device_manager.disconnect()
        self.location_controller = None
        self.battery_label.hide()
        
        if getattr(self, 'is_frozen', False):
            self.device_status_label.setText("手機未連線（位置已凍結）")
            self.device_status_label.setStyleSheet(
                "font-weight: 600; font-size: 12px; color: #ff3b30; border: none; background: transparent;"
            )
            self.control_panel.set_enabled(False)
            self.control_panel.set_freeze_state(is_frozen=True, can_unfreeze=False)
            self.connect_btn.setText("等待中...")
            self.connect_btn.setEnabled(False)
            self.statusBar.showMessage("手機已拔除，模擬位置仍凍結在裝置上。")
        else:
            self.device_status_label.setText("尚未連接裝置")
            self.device_status_label.setStyleSheet(
                "font-weight: 600; font-size: 12px; color: #ff453a; border: none; background: transparent;"
            )
            self.control_panel.set_enabled(False)
            self.connect_btn.setText("連線")
            self.connect_btn.setEnabled(True)
            self.statusBar.showMessage("手機已中斷連線。")
                
    def keyPressEvent(self, event):
        """Hook WASD and arrow keys for joystick control"""
        if not self.device_manager.is_connected() or not self.location_controller:
            super().keyPressEvent(event)
            return
            
        key = event.key()
        if key == Qt.Key.Key_W or key == Qt.Key.Key_Up:
            self._on_joystick_step("N")
        elif key == Qt.Key.Key_S or key == Qt.Key.Key_Down:
            self._on_joystick_step("S")
        elif key == Qt.Key.Key_D or key == Qt.Key.Key_Right:
            self._on_joystick_step("E")
        elif key == Qt.Key.Key_A or key == Qt.Key.Key_Left:
            self._on_joystick_step("W")
        else:
            super().keyPressEvent(event)
            
    def resizeEvent(self, event):
        """Let child layouts settle after window resize."""
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Clean up on window close"""
        if self.device_manager.is_connected():
            if self.location_controller and not getattr(self, 'is_frozen', False):
                self.location_controller.clear_location()
            self.device_manager.disconnect()
        event.accept()
