"""Smoke test: verify all modules import and basic UI can be created."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def test_import_core():
    from core.coordinate_utils import CoordinateUtils
    from core.device_manager import DeviceManager
    from core.location_controller import LocationController
    assert CoordinateUtils is not None
    assert DeviceManager is not None
    assert LocationController is not None

def test_import_utils():
    from utils.config_manager import ConfigManager
    from utils.logger import setup_logger
    from utils.gpx_handler import GPXHandler
    assert ConfigManager is not None
    assert setup_logger is not None
    assert GPXHandler is not None

def test_control_panel_create():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.control_panel import ControlPanel
    cp = ControlPanel()
    assert cp is not None
    assert cp.stack.count() == 4
    app.quit()

def test_coordinate_utils():
    from core.coordinate_utils import CoordinateUtils
    dist = CoordinateUtils.calculate_distance(22.7826, 120.4038, 22.7926, 120.4138)
    assert dist > 0
    assert dist < 5000

def test_gpx_generation():
    from core.location_controller import LocationController
    from core.device_manager import DeviceManager
    dm = DeviceManager()
    lc = LocationController(dm)
    gpx = lc._create_gpx_file(22.7826, 120.4038)
    content = Path(gpx).read_text()
    assert "22.7826" in content
    assert "120.4038" in content
    Path(gpx).unlink(missing_ok=True)

if __name__ == "__main__":
    tests = [
        test_import_core, test_import_utils, test_control_panel_create,
        test_coordinate_utils, test_gpx_generation
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
