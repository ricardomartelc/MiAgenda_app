"""Utilidades de formato, fechas, configuración y servicios de escritorio."""
import calendar
import copy
import json
import os
import sys
import threading
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw

from src.config import CFG_PATH, DEFAULT_CFG, NAV

try:
    from winotify import Notification
except Exception:
    Notification = None
try:
    import winsound
except Exception:
    winsound = None
try:
    import winreg
except Exception:
    winreg = None


def load_cfg():
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = {**copy.deepcopy(DEFAULT_CFG), **json.load(f)}
    except Exception:
        cfg = copy.deepcopy(DEFAULT_CFG)
    pomo = cfg.get("pomo")
    cfg["pomo"] = {**DEFAULT_CFG["pomo"], **(pomo if isinstance(pomo, dict) else {})}
    page_backgrounds = cfg.get("page_backgrounds")
    nav_keys = [key for key, _, _ in NAV]
    valid_keys = set(nav_keys)
    cfg["page_backgrounds"] = {
        key: value
        for key, value in (page_backgrounds.items() if isinstance(page_backgrounds, dict) else ())
        if key in valid_keys
        and isinstance(value, dict)
        and value.get("type") in {"image", "color"}
        and isinstance(value.get("value"), str)
    }
    configured_order = cfg.get("nav_order", [])
    if not isinstance(configured_order, list):
        configured_order = []
    ordered = []
    for key in configured_order:
        if isinstance(key, str) and key in valid_keys and key != "inicio" and key not in ordered:
            ordered.append(key)
    cfg["nav_order"] = ["inicio"] + ordered
    cfg["nav_order"] += [key for key in nav_keys if key not in cfg["nav_order"]]
    return cfg


def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def next_date(d, rec):
    if rec == "Diaria":
        return d + timedelta(days=1)
    if rec == "Semanal":
        return d + timedelta(days=7)
    if rec == "Mensual":
        return add_months(d, 1)
    return d


def parse_date(txt):
    t = txt.strip().lower()
    if t == "hoy":
        return date.today()
    if t in ("mañana", "manana"):
        return date.today() + timedelta(days=1)
    return datetime.strptime(t, "%d/%m/%Y").date()


def parse_time(txt):
    txt = txt.strip()
    if not txt:
        return None
    return datetime.strptime(txt.replace(".", ":"), "%H:%M").strftime("%H:%M")


def fmt_d(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return iso or ""


def money(x):
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def cover(img, w, h):
    """Escala y recorta la imagen para cubrir w x h sin deformarla."""
    r = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * r) + 1, int(img.height * r) + 1))
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def play_melody(kind="alarm"):
    def run():
        try:
            if winsound:
                seq = [(880, 140), (1175, 140), (1568, 280)] if kind == "alarm" \
                    else [(660, 180), (880, 180), (660, 180), (880, 380)]
                for f, ms in seq:
                    winsound.Beep(f, ms)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def toast(title, msg):
    def run():
        try:
            if Notification:
                Notification(app_id="Mi Agenda", title=title, msg=msg).show()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def make_tray_image(color):
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 8, 60, 60), radius=12, fill=color)
    d.rectangle((16, 2, 22, 14), fill="white")
    d.rectangle((42, 2, 48, 14), fill="white")
    d.rectangle((4, 20, 60, 24), fill="white")
    for r in range(2):
        for c in range(3):
            x, y = 14 + c * 14, 30 + r * 14
            d.rectangle((x, y, x + 8, y + 8), fill="white")
    return im

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimizado'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exe}" "{os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))}" --minimizado'


def autostart_enabled():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "MiAgenda")
            return True
    except OSError:
        return False


def set_autostart(on):
    if not winreg:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "MiAgenda", 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, "MiAgenda")
                except OSError:
                    pass
    except OSError:
        pass
