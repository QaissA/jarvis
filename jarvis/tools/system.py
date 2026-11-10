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


@tool()
def system_info() -> str:
    """Return battery level, CPU load and free disk space of this computer."""
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    pct = re.search(r"(\d+)%", batt)
    load = os.getloadavg()[0] / os.cpu_count() * 100
    free = shutil.disk_usage("/").free / 1e9
    return f"Battery {pct.group(1) if pct else 'unknown'}%, CPU load {load:.0f}%, {free:.0f} GB disk free"
