"""
Control Panel - iPhone 定位模擬器
側欄導航 + 子頁面切換
"""

import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QSlider, QDoubleSpinBox,
    QComboBox, QGridLayout, QCheckBox, QMessageBox,
    QStackedWidget, QFrame, QSizePolicy, QButtonGroup, QListView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon
from loguru import logger
from core.coordinate_utils import CoordinateUtils
from pathlib import Path

_ICONS = Path(__file__).parent / "icons"

class NavButton(QPushButton):
    """側欄導航按鈕 (SVG icon)"""
    def __init__(self, icon_path, text, page_id, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        self._full_text = f"  {text}"
        self._icon_path = icon_path
        if icon_path:
            self.setIcon(QIcon(icon_path))
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_collapsed(False)

    def set_collapsed(self, collapsed: bool):
        """Switch between full text and icon-only mode without clipping icons."""
        if collapsed:
            self.setText("")
            self.setToolTip(self._full_text.strip())
            self.setFixedSize(52, 48)
            self.setIconSize(QSize(22, 22))
            self.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 0px;
                    margin: 0px;
                    border: none;
                    border-radius: 8px;
                    color: #B0B8C8;
                    background: transparent;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.10);
                    color: #E2E8F0;
                }
                QPushButton:checked {
                    background: rgba(99, 102, 241, 0.28);
                    color: #C7D2FE;
                    border: none;
                }
            """)
        else:
            self.setText(self._full_text)
            self.setToolTip("")
            self.setFixedSize(120, 48)
            self.setIconSize(QSize(22, 22))
            self.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 0px 8px 0px 15px;
                    margin: 0px;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    color: #B0B8C8;
                    background: transparent;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.10);
                    color: #E2E8F0;
                }
                QPushButton:checked {
                    background: rgba(99, 102, 241, 0.25);
                    color: #C7D2FE;
                    font-weight: bold;
                    border: none;
                }
            """)


class PageTitle(QLabel):
    """頁面標題"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #E2E8F0;
            padding: 4px 0 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        """)


class ControlPanel(QWidget):
    """側欄控制面板 — 子頁面導航"""
    
    # Collapse state
    _collapsed = False

    # Signals (keep all existing)
    set_location_requested = pyqtSignal(float, float)
    set_destination_requested = pyqtSignal(float, float)
    map_pick_requested = pyqtSignal(str)
    map_overlays_clear_requested = pyqtSignal()
    walk_simulation_requested = pyqtSignal(float, float, float, float, float, float, bool, str)
    stop_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    freeze_requested = pyqtSignal()
    joystick_step_requested = pyqtSignal(str)
    roam_requested = pyqtSignal(float, float, float, float, float, str)
    roam_radius_changed = pyqtSignal(float, float, float)

    PAGES = [
        ("page_location", str(_ICONS / "route.svg"),    "定位路線"),
        ("page_roam",     str(_ICONS / "roam.svg"),     "區域漫遊"),
        ("page_joystick", str(_ICONS / "joystick.svg"), "搖桿控制"),
        ("page_system",   str(_ICONS / "settings.svg"), "系統控制"),
    ]

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._config = config
        self._nav_buttons: dict = {}
        self._create_layout()
        self._create_pages()
        self._connect_nav()
        # 預設顯示第一頁
        self._nav_buttons["page_location"].setChecked(True)
        self.stack.setCurrentIndex(0)

    def _style_combo(self, combo: QComboBox):
        """Force a dark popup view so native GTK/Qt popup frames do not show white."""
        view = QListView(combo)
        view.setObjectName("dark_combo_popup")
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setUniformItemSizes(True)
        view.setAutoFillBackground(True)
        view.viewport().setAutoFillBackground(True)
        view.viewport().setStyleSheet("background-color: #14181F;")
        view.setStyleSheet("""
            QListView#dark_combo_popup {
                background-color: #14181F;
                color: #E2E8F0;
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 8px;
                padding: 4px;
                outline: 0;
                show-decoration-selected: 1;
            }
            QListView#dark_combo_popup::item {
                min-height: 32px;
                padding: 7px 12px;
                border-radius: 4px;
                background-color: #14181F;
                color: #E2E8F0;
            }
            QListView#dark_combo_popup::item:hover,
            QListView#dark_combo_popup::item:selected {
                background-color: #3B82F6;
                color: #FFFFFF;
            }
        """)
        combo.setView(view)
        combo.setStyleSheet(combo.styleSheet() + """
            QComboBox { background-color: rgba(10, 14, 22, 0.95); color: #E2E8F0; }
            QComboBox QAbstractItemView { background-color: #14181F; color: #E2E8F0; }
        """)

    # ── 主佈局：左側導航 + 右側頁面 ──
    def _create_layout(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左側導航列
        self._nav_frame = QFrame()
        self._nav_frame.setFixedWidth(132)
        self._nav_frame.setStyleSheet("""
            QFrame {
                background: #141519;
                border-right: 1px solid #27282D;
            }
        """)
        nav_layout = QVBoxLayout(self._nav_frame)
        nav_layout.setContentsMargins(6, 12, 6, 12)
        nav_layout.setSpacing(2)

        # 導航標題
        self._nav_title = QLabel(" 導航選單")
        self._nav_title.setStyleSheet("color: #818CF8; font-size: 12px; font-weight: bold; padding: 4px 8px 10px 8px;")
        nav_layout.addWidget(self._nav_title)

        # 導航按鈕群組（確保只有一個選中）
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        for page_id, icon, label in self.PAGES:
            btn = NavButton(icon, label, page_id)
            self._nav_group.addButton(btn)
            nav_layout.addWidget(btn)
            self._nav_buttons[page_id] = btn

        nav_layout.addStretch()

        # 版本號
        self._ver_label = QLabel(" v1.0.0")
        self._ver_label.setStyleSheet("color: #555A65; font-size: 10px; padding: 8px;")
        self._ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self._ver_label)

        root.addWidget(self._nav_frame)

        # 右側頁面堆疊
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        root.addWidget(self.stack, 1)

    # ── 頁面切換 ──
    def _connect_nav(self):
        for page_id, btn in self._nav_buttons.items():
            btn.clicked.connect(lambda checked, pid=page_id: self._switch_page(pid))

    def _switch_page(self, page_id: str):
        idx_map = {pid: i for i, (pid, _, _) in enumerate(self.PAGES)}
        self.stack.setCurrentIndex(idx_map[page_id])

    # ── 建立子頁面 ──
    def _create_pages(self):
        self.stack.addWidget(self._page_location())
        self.stack.addWidget(self._page_roam())
        self.stack.addWidget(self._page_joystick())
        self.stack.addWidget(self._page_system())

    # ═══════════════════════════════════════
    #  PAGE 1 — 即時定位
    # ═══════════════════════════════════════
    def _page_location(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(PageTitle("即時定位 / 路線模擬"))

        # 搜尋地址
        search_group = QGroupBox("地址搜尋")
        search_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        s_layout = QVBoxLayout(search_group)
        s_layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("輸入地址（例如：台北 101）")
        self.search_input.returnPressed.connect(lambda: self._on_search(is_dest=False))
        s_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("搜尋並設為起點")
        self.search_btn.setIcon(QIcon(str(_ICONS / "search.svg")))
        self.search_btn.clicked.connect(lambda: self._on_search(is_dest=False))
        s_layout.addWidget(self.search_btn)

        self.dest_search_input = QLineEdit()
        self.dest_search_input.setPlaceholderText("目的地地址...")
        self.dest_search_input.returnPressed.connect(lambda: self._on_search(is_dest=True))
        s_layout.addWidget(self.dest_search_input)

        self.dest_search_btn = QPushButton("搜尋並設為終點")
        self.dest_search_btn.setIcon(QIcon(str(_ICONS / "search.svg")))
        self.dest_search_btn.clicked.connect(lambda: self._on_search(is_dest=True))
        s_layout.addWidget(self.dest_search_btn)

        layout.addWidget(search_group)

        # 座標手動輸入
        coord_group = QGroupBox("手動座標")
        coord_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        c_layout = QVBoxLayout(coord_group)
        c_layout.setSpacing(6)

        grid = QGridLayout()
        grid.addWidget(QLabel("起點緯度："), 0, 0)
        self.lat_input = QDoubleSpinBox()
        self.lat_input.setRange(-90, 90)
        self.lat_input.setDecimals(6)
        self.lat_input.setValue(self._config.get("map.default_center.latitude", 22.7826) if self._config else 22.7826)
        grid.addWidget(self.lat_input, 0, 1)

        grid.addWidget(QLabel("起點經度："), 0, 2)
        self.lon_input = QDoubleSpinBox()
        self.lon_input.setRange(-180, 180)
        self.lon_input.setDecimals(6)
        self.lon_input.setValue(self._config.get("map.default_center.longitude", 120.4038) if self._config else 120.4038)
        grid.addWidget(self.lon_input, 0, 3)

        grid.addWidget(QLabel("終點緯度："), 1, 0)
        self.end_lat_input = QDoubleSpinBox()
        self.end_lat_input.setRange(-90, 90)
        self.end_lat_input.setDecimals(6)
        self.end_lat_input.setValue(self._config.get("map.default_center.latitude", 22.7826) + 0.01 if self._config else 22.7926)
        grid.addWidget(self.end_lat_input, 1, 1)

        grid.addWidget(QLabel("終點經度："), 1, 2)
        self.end_lon_input = QDoubleSpinBox()
        self.end_lon_input.setRange(-180, 180)
        self.end_lon_input.setDecimals(6)
        self.end_lon_input.setValue(self._config.get("map.default_center.longitude", 120.4038) + 0.01 if self._config else 120.4138)
        grid.addWidget(self.end_lon_input, 1, 3)
        c_layout.addLayout(grid)

        btn_row = QHBoxLayout()
        self.set_location_btn = QPushButton("移動到起點")
        self.set_location_btn.setIcon(QIcon(str(_ICONS / "location.svg")))
        self.set_location_btn.clicked.connect(self._on_set_location)
        btn_row.addWidget(self.set_location_btn)
        self.copy_loc_btn = QPushButton("複製起點")
        self.copy_loc_btn.setIcon(QIcon(str(_ICONS / "copy.svg")))
        self.copy_loc_btn.clicked.connect(self._on_copy_location)
        btn_row.addWidget(self.copy_loc_btn)
        c_layout.addLayout(btn_row)

        map_pick_row = QHBoxLayout()
        self.pick_start_btn = QPushButton("地圖選起點")
        self.pick_start_btn.setIcon(QIcon(str(_ICONS / "target.svg")))
        self.pick_start_btn.clicked.connect(lambda: self.map_pick_requested.emit("start"))
        map_pick_row.addWidget(self.pick_start_btn)

        self.pick_dest_btn = QPushButton("地圖選終點")
        self.pick_dest_btn.setIcon(QIcon(str(_ICONS / "route.svg")))
        self.pick_dest_btn.clicked.connect(lambda: self.map_pick_requested.emit("destination"))
        map_pick_row.addWidget(self.pick_dest_btn)
        c_layout.addLayout(map_pick_row)

        self.clear_map_btn = QPushButton("清除地圖標示")
        self.clear_map_btn.setIcon(QIcon(str(_ICONS / "reset.svg")))
        self.clear_map_btn.clicked.connect(self.map_overlays_clear_requested.emit)
        c_layout.addWidget(self.clear_map_btn)

        layout.addWidget(coord_group)

        # 路線模擬設定和起終點座標放在同一頁，避免跨子頁面設定。
        route_group = QGroupBox("路線模擬")
        route_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        route_layout = QVBoxLayout(route_group)
        route_layout.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("模式："))
        self.preset_combo = QComboBox()
        self._style_combo(self.preset_combo)
        self.preset_combo.addItems([
            "自動（依距離判斷）",
            "步行（<=8 km/h）",
            "騎車（<=30 km/h）",
            "市區開車（<=50 km/h）",
            "高速公路（<=90 km/h）"
        ])
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.preset_combo, 1)
        route_layout.addLayout(mode_row)

        speed_label_row = QHBoxLayout()
        speed_label_row.addWidget(QLabel("速度："))
        self.speed_value_label = QLabel("35.0 km/h")
        self.speed_value_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        speed_label_row.addWidget(self.speed_value_label)
        speed_label_row.addStretch()
        route_layout.addLayout(speed_label_row)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 500)
        self.speed_slider.setValue(350)
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        route_layout.addWidget(self.speed_slider)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("更新頻率："))
        self.interval_input = QDoubleSpinBox()
        self.interval_input.setRange(0.1, 10.0)
        self.interval_input.setValue(1.0)
        self.interval_input.setSingleStep(0.1)
        self.interval_input.setSuffix(" s")
        interval_row.addWidget(self.interval_input)
        route_layout.addLayout(interval_row)

        self.stops_checkbox = QCheckBox("模擬紅綠燈、轉彎與出口停頓")
        self.stops_checkbox.setChecked(True)
        route_layout.addWidget(self.stops_checkbox)

        self.walk_btn = QPushButton("計算路線並開始移動")
        self.walk_btn.setIcon(QIcon(str(_ICONS / "play.svg")))
        self.walk_btn.setObjectName("walk_btn")
        self.walk_btn.setMinimumHeight(44)
        self.walk_btn.clicked.connect(self._on_walk_simulation)
        route_layout.addWidget(self.walk_btn)

        layout.addWidget(route_group)
        layout.addStretch()
        return page

    # ═══════════════════════════════════════
    #  PAGE 2 — 區域漫遊
    # ═══════════════════════════════════════
    def _page_roam(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(PageTitle("區域漫遊"))
        tip = QLabel("手機會在指定半徑內持續自動移動，可拔線後繼續運作。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #B0B8C8; font-size: 11px; margin-bottom: 4px;")
        layout.addWidget(tip)

        # 半徑
        rad_group = QGroupBox("漫遊範圍")
        rad_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        r_layout = QVBoxLayout(rad_group)
        r_layout.setSpacing(6)

        rad_row = QHBoxLayout()
        rad_row.addWidget(QLabel("半徑："))
        self.radius_label = QLabel("500 m")
        self.radius_label.setStyleSheet("color: #34c759; font-weight: bold; font-size: 14px;")
        rad_row.addWidget(self.radius_label)
        rad_row.addStretch()
        r_layout.addLayout(rad_row)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 5000)
        self.radius_slider.setValue(self._config.get("roam.default_radius", 500) if self._config else 500)
        self.radius_slider.valueChanged.connect(self._on_radius_changed)
        r_layout.addWidget(self.radius_slider)

        self.pick_roam_center_btn = QPushButton("地圖選漫遊中心")
        self.pick_roam_center_btn.setIcon(QIcon(str(_ICONS / "target.svg")))
        self.pick_roam_center_btn.clicked.connect(lambda: self.map_pick_requested.emit("roam"))
        r_layout.addWidget(self.pick_roam_center_btn)

        self.clear_roam_map_btn = QPushButton("清除地圖標示")
        self.clear_roam_map_btn.setIcon(QIcon(str(_ICONS / "reset.svg")))
        self.clear_roam_map_btn.clicked.connect(self.map_overlays_clear_requested.emit)
        r_layout.addWidget(self.clear_roam_map_btn)

        layout.addWidget(rad_group)

        # 參數
        param_group = QGroupBox("漫遊參數")
        param_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        p_layout = QVBoxLayout(param_group)
        p_layout.setSpacing(6)

        s_row = QHBoxLayout()
        s_row.addWidget(QLabel("速度："))
        self.roam_speed_combo = QComboBox()
        self._style_combo(self.roam_speed_combo)
        self.roam_speed_combo.addItems([
            "步行（約 5 km/h）",
            "騎車（約 15 km/h）",
            "市區開車（約 35 km/h）",
            "快速行駛（約 80 km/h）"
        ])
        s_row.addWidget(self.roam_speed_combo)
        p_layout.addLayout(s_row)

        d_row = QHBoxLayout()
        d_row.addWidget(QLabel("時間："))
        self.duration_input = QDoubleSpinBox()
        self.duration_input.setRange(1.0, 1440.0)
        self.duration_input.setValue(float(self._config.get("roam.default_duration", 30)) if self._config else 30.0)
        self.duration_input.setSuffix(" min")
        d_row.addWidget(self.duration_input)
        p_layout.addLayout(d_row)

        layout.addWidget(param_group)

        # 按鈕
        btn_row = QHBoxLayout()
        self.start_roam_btn = QPushButton("開始漫遊")
        self.start_roam_btn.setIcon(QIcon(str(_ICONS / "walk.svg")))
        self.start_roam_btn.setMinimumHeight(40)
        self.start_roam_btn.clicked.connect(self._on_start_roaming)
        btn_row.addWidget(self.start_roam_btn)

        layout.addLayout(btn_row)

        layout.addStretch()
        return page

    # ═══════════════════════════════════════
    #  PAGE 3 — 搖桿控制
    # ═══════════════════════════════════════
    def _page_joystick(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        layout.addWidget(PageTitle("搖桿控制"))

        desc = QLabel("使用按鈕或鍵盤 WASD / 方向鍵逐步移動定位")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #B0B8C8; font-size: 12px;")
        layout.addWidget(desc)

        # D-Pad
        dpad_widget = QWidget()
        dpad_layout = QGridLayout(dpad_widget)
        dpad_layout.setContentsMargins(0, 10, 0, 10)
        dpad_layout.setSpacing(8)

        btn_style = """
            QPushButton {
                background-color: #2a2b35;
                border-radius: 10px;
                font-size: 22px;
                font-weight: bold;
                color: #E2E8F0;
                min-width: 60px;
                min-height: 60px;
            }
            QPushButton:hover { background-color: #3a3b48; }
            QPushButton:pressed { background-color: #6366F1; }
        """

        self.btn_up = QPushButton("▲")
        self.btn_up.setStyleSheet(btn_style)
        self.btn_up.clicked.connect(lambda: self.joystick_step_requested.emit("N"))

        self.btn_down = QPushButton("▼")
        self.btn_down.setStyleSheet(btn_style)
        self.btn_down.clicked.connect(lambda: self.joystick_step_requested.emit("S"))

        self.btn_left = QPushButton("◀")
        self.btn_left.setStyleSheet(btn_style)
        self.btn_left.clicked.connect(lambda: self.joystick_step_requested.emit("W"))

        self.btn_right = QPushButton("▶")
        self.btn_right.setStyleSheet(btn_style)
        self.btn_right.clicked.connect(lambda: self.joystick_step_requested.emit("E"))

        dpad_layout.addWidget(self.btn_up, 0, 1, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_left, 1, 0, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_right, 1, 2, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_down, 2, 1, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(dpad_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # 快捷鍵提示
        keys = QLabel("⌨️ 鍵盤快捷鍵：W A S D 或 ↑ ← ↓ →")
        keys.setStyleSheet("color: #64748B; font-size: 11px;")
        keys.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(keys)

        layout.addStretch()
        return page

    # ═══════════════════════════════════════
    #  PAGE 4 — 系統控制
    # ═══════════════════════════════════════
    def _page_system(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        layout.addWidget(PageTitle("系統控制"))

        # 停止 / 重置
        ctrl_group = QGroupBox("定位控制")
        ctrl_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        c_layout = QVBoxLayout(ctrl_group)
        c_layout.setSpacing(8)

        self.stop_btn = QPushButton("停止模擬")
        self.stop_btn.setIcon(QIcon(str(_ICONS / "stop.svg")))
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self._on_stop)
        c_layout.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("重置 GPS（恢復真實位置）")
        self.clear_btn.setIcon(QIcon(str(_ICONS / "reset.svg")))
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.clicked.connect(self._on_clear)
        c_layout.addWidget(self.clear_btn)

        layout.addWidget(ctrl_group)

        # 凍結
        freeze_group = QGroupBox("位置凍結")
        freeze_group.setStyleSheet("QGroupBox { font-weight: bold; color: #C7D2FE; }")
        f_layout = QVBoxLayout(freeze_group)
        f_layout.setSpacing(6)

        self.freeze_btn = QPushButton("凍結位置")
        self.freeze_btn.setIcon(QIcon(str(_ICONS / "snowflake.svg")))
        self.freeze_btn.setObjectName("freeze_btn")
        self.freeze_btn.setMinimumHeight(40)
        self.freeze_btn.clicked.connect(self._on_freeze)
        f_layout.addWidget(self.freeze_btn)

        info = QLabel("凍結後位置固定在目前座標，直到解除凍結或重啟手機。")
        info.setWordWrap(True)
        info.setStyleSheet("color: #B0B8C8; font-size: 11px;")
        f_layout.addWidget(info)

        layout.addWidget(freeze_group)
        layout.addStretch()
        return page

    # ═══════════════════════════════════════
    #  保留所有公開方法（main_window 依賴）
    # ═══════════════════════════════════════

    def _on_search(self, is_dest=False):
        input_box = self.dest_search_input if is_dest else self.search_input
        btn = self.dest_search_btn if is_dest else self.search_btn
        query = input_box.text().strip()
        if not query:
            return
        original_text = btn.text()
        btn.setText("...")
        btn.setEnabled(False)
        try:
            headers = {"User-Agent": "MarcelLocationSimulator/1.0"}
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
            r = requests.get(url, headers=headers, timeout=6)
            r.raise_for_status()
            data = r.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display_name = data[0].get("display_name", query)
                logger.info(f"Search result: {display_name} ({lat}, {lon})")
                if is_dest:
                    self.set_end_location(lat, lon)
                    self.set_destination_requested.emit(lat, lon)
                else:
                    self.set_coordinates(lat, lon)
                    self.set_location_requested.emit(lat, lon)
            else:
                QMessageBox.warning(self, "找不到位置", f"找不到：{query}")
        except Exception as e:
            logger.error(f"Search API error: {e}")
            QMessageBox.warning(self, "搜尋錯誤", str(e))
        finally:
            btn.setText(original_text)
            btn.setEnabled(True)

    def _on_mode_changed(self, index: int):
        if index == 0:
            return
        # Read speed presets from config or use defaults
        if self._config:
            presets = self._config.get("route.speed_presets", {})
            keys = ["walking", "cycling", "driving", "highway"]
            config_list = [tuple(presets.get(k, [10, 500, 350])[1:]) for k in keys]
        else:
            config_list = [(80, 50), (300, 150), (500, 350), (900, 800)]
        cfg_idx = index - 1
        if 0 <= cfg_idx < len(config_list):
            max_val, default_val = config_list[cfg_idx]
            self.speed_slider.blockSignals(True)
            self.speed_slider.setRange(10, max_val)
            self.speed_slider.setValue(default_val)
            self.speed_slider.blockSignals(False)
            self._update_speed_label(default_val)

    def _get_transport_mode(self) -> str:
        modes = ['walking', 'cycling', 'driving', 'highway']
        idx = self.preset_combo.currentIndex() - 1
        return modes[idx] if 0 <= idx < len(modes) else 'driving'

    def _update_speed_label(self, value: int):
        speed = value / 10.0
        self.speed_value_label.setText(f"{speed:.1f} km/h")
        if self.preset_combo.currentIndex() != 0:
            expected_values = {1: 50, 2: 150, 3: 350, 4: 800}
            expected = expected_values.get(self.preset_combo.currentIndex())
            if expected is not None and value != expected:
                self.preset_combo.setCurrentIndex(0)

    def _on_set_location(self):
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        self.set_location_requested.emit(lat, lon)

    def _on_walk_simulation(self):
        start_lat = self.lat_input.value()
        start_lon = self.lon_input.value()
        end_lat = self.end_lat_input.value()
        end_lon = self.end_lon_input.value()
        mode_idx = self.preset_combo.currentIndex()
        if mode_idx == 0:
            dist_m = CoordinateUtils.calculate_distance(start_lat, start_lon, end_lat, end_lon)
            if dist_m < 2500:
                transport_mode = 'walking'
                speed = 6.0
                simulate_stops = False
                self.preset_combo.setCurrentIndex(1)
            else:
                transport_mode = 'driving'
                speed = 50.0
                simulate_stops = True
                self.preset_combo.setCurrentIndex(3)
                self.stops_checkbox.setChecked(True)
        else:
            transport_mode = self._get_transport_mode()
            speed = self.speed_slider.value() / 10.0
            simulate_stops = self.stops_checkbox.isChecked()
        interval = self.interval_input.value()
        self.walk_simulation_requested.emit(
            start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops, transport_mode
        )

    def _on_stop(self):
        self.stop_requested.emit()

    def _on_clear(self):
        self.clear_requested.emit()

    def _on_freeze(self):
        self.freeze_requested.emit()

    def _on_radius_changed(self, value):
        if value >= 1000:
            self.radius_label.setText(f"{value/1000:.1f} km")
        else:
            self.radius_label.setText(f"{value} m")
        self.roam_radius_changed.emit(self.lat_input.value(), self.lon_input.value(), float(value))

    def _on_start_roaming(self):
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        radius = float(self.radius_slider.value())
        duration = self.duration_input.value()
        idx = self.roam_speed_combo.currentIndex()
        # Read speeds from config or use defaults
        if self._config:
            s = self._config.get("roam", {})
            speeds = {
                0: ('walking', s.get("walking_speed", 5.0)),
                1: ('cycling', s.get("cycling_speed", 15.0)),
                2: ('driving', s.get("default_speed", 35.0)),
                3: ('highway', s.get("highway_speed", 80.0)),
            }
        else:
            speeds = {0: ('walking', 5.0), 1: ('cycling', 15.0), 2: ('driving', 35.0), 3: ('highway', 80.0)}
        mode, speed = speeds.get(idx, ('driving', 35.0))
        self.roam_requested.emit(lat, lon, radius, duration, speed, mode)

    def _on_copy_location(self):
        from PyQt6.QtWidgets import QApplication
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{lat:.6f}, {lon:.6f}")
        logger.info(f"Copied to clipboard: {lat:.6f}, {lon:.6f}")

    def set_collapsed(self, collapsed: bool):
        """Collapse sidebar to icon-only or expand to full."""
        self._collapsed = collapsed
        if collapsed:
            self._nav_frame.setFixedWidth(64)
            self._nav_frame.setMinimumWidth(64)
            self._nav_title.hide()
            self._ver_label.hide()
            self.stack.hide()
            for btn in self._nav_buttons.values():
                btn.set_collapsed(True)
        else:
            self._nav_frame.setFixedWidth(132)
            self._nav_frame.setMinimumWidth(132)
            self._nav_title.show()
            self._ver_label.show()
            self.stack.show()
            for btn in self._nav_buttons.values():
                btn.set_collapsed(False)

    def set_coordinates(self, latitude: float, longitude: float):
        self.lat_input.setValue(latitude)
        self.lon_input.setValue(longitude)

    def set_end_location(self, latitude: float, longitude: float):
        self.end_lat_input.setValue(latitude)
        self.end_lon_input.setValue(longitude)

    def set_freeze_state(self, is_frozen: bool, can_unfreeze: bool = False):
        if is_frozen:
            if can_unfreeze:
                self.freeze_btn.setText("解除 GPS 凍結")
                self.freeze_btn.setEnabled(True)
                self.freeze_btn.setStyleSheet("background-color: rgba(16, 185, 129, 0.9);")
            else:
                self.freeze_btn.setText("位置已凍結")
                self.freeze_btn.setEnabled(False)
                self.freeze_btn.setStyleSheet("background-color: rgba(99, 102, 241, 0.5);")
        else:
            self.freeze_btn.setText("凍結位置")
            self.freeze_btn.setEnabled(True)
            self.freeze_btn.setStyleSheet("")

    def set_enabled(self, enabled: bool):
        widgets = [
            self.set_location_btn, self.walk_btn, self.stop_btn, self.clear_btn,
            self.freeze_btn, self.search_btn, self.dest_search_btn, self.copy_loc_btn,
            self.pick_start_btn, self.pick_dest_btn, self.pick_roam_center_btn, self.clear_map_btn, self.clear_roam_map_btn,
            self.btn_up, self.btn_down, self.btn_left, self.btn_right,
            self.stops_checkbox, self.start_roam_btn,
            self.radius_slider, self.duration_input, self.roam_speed_combo,
        ]
        for w in widgets:
            w.setEnabled(enabled)
