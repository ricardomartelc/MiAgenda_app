"""Configuración y constantes de Mi Agenda."""
import os
from pathlib import Path

# ------------------------------------------------------------ constantes
APP_DIR = os.path.join(os.path.expanduser("~"), "MiAgenda")
BACKUP_DIR = os.path.join(APP_DIR, "backups")
os.makedirs(APP_DIR, exist_ok=True)
DB_PATH = os.path.join(APP_DIR, "agenda.db")
CFG_PATH = os.path.join(APP_DIR, "config.json")
ASSETS_DIR = str(Path(__file__).resolve().parent.parent / "assets" / "backgrounds")
PORT = 47653  # para detectar una segunda instancia

PRIO = {"Alta": "#ef4444", "Media": "#f59e0b", "Baja": "#22c55e"}
ACCENTS = {"Violeta": "#7c3aed", "Azul": "#2563eb", "Verde": "#16a34a",
           "Rosa": "#db2777", "Naranja": "#ea580c"}
CAT_COLORS = {"Rojo": "#ef4444", "Naranja": "#f97316", "Amarillo": "#ca8a04", "Verde": "#16a34a",
              "Turquesa": "#0d9488", "Azul": "#2563eb", "Violeta": "#7c3aed", "Rosa": "#db2777",
              "Gris": "#64748b"}
DEFAULT_CATS = [("Trabajo", "#2563eb"), ("Estudios", "#7c3aed"), ("Casa", "#16a34a"),
                ("Personal", "#db2777"), ("Salud", "#ef4444")]
GASTO_CATS = ["Comida", "Transporte", "Ocio", "Hogar", "Salud", "Compras", "Otros"]
MOODS = [(1, "😞"), (2, "🙁"), (3, "😐"), (4, "🙂"), (5, "😄")]
MOOD_COLORS = {1: "#ef4444", 2: "#f97316", 3: "#eab308", 4: "#84cc16", 5: "#22c55e"}
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
NAV = [("inicio", "🏠", "Inicio"), ("tareas", "✅", "Tareas"), ("calendario", "🗓", "Calendario"),
       ("notas", "📝", "Notas"), ("pomodoro", "🍅", "Pomodoro"), ("habitos", "🔥", "Hábitos"),
       ("horario", "▦", "Horario semanal"), ("metas", "🎯", "Metas"), ("diario", "😊", "Diario"),
       ("gastos", "💶", "Gastos"), ("stats", "📊", "Estadísticas"),
       ("fondos", "◐", "Fondos y colores"), ("ajustes", "⚙", "Ajustes")]

SURFACE = "#ffffff"
CARD = ("#ffffff", "#ffffff")
ROW = ("#f5f5f7", "#f5f5f7")
MUTED = ("#6e6e73", "#6e6e73")
TEXT = ("#1d1d1f", "#1d1d1f")

DEFAULT_CFG = {"modo": "light", "acento": "Violeta", "fondo": "", "bandeja": True, "widget": False,
               "widget_pos": [80, 80], "sonido": True,
               "pomo": {"Trabajo": 25, "Descanso": 5, "Largo": 15},
               "nav_order": [key for key, _, _ in NAV],
               "page_backgrounds": {}}
