"""GPX file generation for iGPS location simulation."""

import tempfile
from datetime import datetime, timedelta
from typing import List, Tuple


def create_single_point_gpx(latitude: float, longitude: float) -> str:
    """Generate a long-duration single-location GPX file."""
    t1 = datetime.utcnow()
    t2 = t1 + timedelta(hours=24)
    gpx = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="iGPS"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <trk>
    <name>Location</name>
    <trkseg>
      <trkpt lat="{latitude}" lon="{longitude}">
        <time>{t1.isoformat()}Z</time>
      </trkpt>
      <trkpt lat="{latitude}" lon="{longitude}">
        <time>{t2.isoformat()}Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".gpx", delete=False) as f:
        f.write(gpx)
        return f.name


def densify_waypoints(
    waypoints: List[Tuple[float, float, float]], max_gap_sec: float = 1.0
) -> List[Tuple[float, float, float]]:
    """Interpolate waypoints so no gap exceeds max_gap_sec."""
    if not waypoints:
        return []
    densified = [waypoints[0]]
    for i in range(1, len(waypoints)):
        prev, curr = waypoints[i - 1], waypoints[i]
        time_gap = curr[2] - prev[2]
        if time_gap > max_gap_sec:
            num = int(time_gap // max_gap_sec)
            for j in range(1, num + 1):
                frac = j / (num + 1)
                densified.append((
                    prev[0] + (curr[0] - prev[0]) * frac,
                    prev[1] + (curr[1] - prev[1]) * frac,
                    prev[2] + time_gap * frac,
                ))
        densified.append(curr)
    return densified


def create_route_gpx(waypoints: List[Tuple[float, float, float]]) -> str:
    """Generate a multi-point route GPX file."""
    gpx = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="iGPS"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <trk>
    <name>Route</name>
    <trkseg>
"""
    start = datetime.utcnow()
    for lat, lon, offset in waypoints:
        t = start + timedelta(seconds=offset)
        gpx += '      <trkpt lat="{}" lon="{}">\n'.format(lat, lon)
        gpx += '        <time>{}Z</time>\n'.format(t.isoformat())
        gpx += '      </trkpt>\n'
    gpx += """    </trkseg>
  </trk>
</gpx>"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".gpx", delete=False) as f:
        f.write(gpx)
        return f.name
