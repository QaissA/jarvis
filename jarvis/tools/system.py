import os
import re
import shutil
import subprocess
from datetime import datetime

from .registry import tool


@tool()
def get_time() -> str:
    """Return the current local time."""
    return datetime.now().strftime("%H:%M")


@tool()
def get_date() -> str:
    """Return today's date and weekday."""
    return datetime.now().strftime("%A, %d %B %Y")


def stats() -> dict:
    """Live numbers, shared by the system_info tool and the dashboard."""
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    pct = re.search(r"(\d+)%", batt)
    disk = shutil.disk_usage("/")
    return {"battery": int(pct.group(1)) if pct else None,
            "cpu": min(100, round(os.getloadavg()[0] / os.cpu_count() * 100)),
            "disk_free_gb": round(disk.free / 1e9), "disk_used": round(disk.used / disk.total * 100)}


@tool()
def system_info() -> str:
    """Return battery level, CPU load and free disk space of this computer."""
    s = stats()
    battery = "unknown" if s["battery"] is None else f"{s['battery']}%"
    return f"Battery {battery}, CPU load {s['cpu']}%, {s['disk_free_gb']} GB disk free"
