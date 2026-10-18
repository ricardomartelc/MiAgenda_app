"""Punto de composición de la interfaz principal de Mi Agenda."""
import os
import queue
import threading
import customtkinter as ctk
from datetime import date, datetime
from tkinter import messagebox

try:
    import pystray
except Exception:
    pystray = None

from src.config import ACCENTS, BACKUP_DIR, CARD, MUTED, ROW, SURFACE, TEXT
from src.database import DB
from src.utils import load_cfg, make_tray_image, mix, play_melody, save_cfg, toast

from src.ui.window_shell import WindowShellMixin
from src.ui.activity_pages import ActivityPagesMixin
from src.ui.customization_pages import CustomizationPagesMixin
from src.ui.schedule_pages import SchedulePagesMixin
from src.ui.productivity_pages import ProductivityPagesMixin
from src.ui.management_pages import ManagementPagesMixin
from src.ui.widget import WidgetMixin


class App(
    WindowShellMixin,
    ActivityPagesMixin,
    ProductivityPagesMixin,
    ManagementPagesMixin,
    SchedulePagesMixin,
    CustomizationPagesMixin,
    WidgetMixin,
    ctk.CTk,
):
    def __init__(self, sock=None, hidden=False):
        super().__init__()
        self.withdraw()
        self.cfg = load_cfg()
        self.db = DB()
        self.cfg["modo"] = "light"
        ctk.set_appearance_mode("light")
        self.title("Mi Agenda")
        self.geometry("1240x780")
        self.minsize(1020, 700)
        self.attributes("-alpha", 0.0)
        self.configure(fg_color=SURFACE)

        self.q = queue.Queue()
        self.today = date.today()
        self.cal_y, self.cal_m, self.sel_day = self.today.year, self.today.month, self.today
        self.gas_y, self.gas_m = self.today.year, self.today.month
        self.diario_date = self.today
        self.current = "inicio"
        self.note_id = None
        self.hab_sel = None
        self.search_q = ""
        self.filt = {"cat": "Todas", "estado": "Pendientes"}
        self.cats = {}
        self.focus_task = False
        self.bg_src = self.bg_img = None
        self.page_bg_labels = {}
        self.page_bg_images = {}
        self.page_background_luminance = {}
        self._splash = None
        self.nav_order = self._configured_nav_order()
        self._nav_drag_key = None
        self._nav_drag_moved = False
        self._page_bg_bound = set()
        self._note_job = self._resize_job = self._refresh_job = None
        self.widget = self.w_pomo = self.tray = None
        self.pomo_canvas = self.pomo_btn = None
        self._last_w_pomo = ""
        d = self.cfg["pomo"]
        self.pomo = {"modo": "Trabajo", "corriendo": False, "fin": 0.0,
                     "total": d["Trabajo"] * 60, "restante": d["Trabajo"] * 60}

        self.auto_backup()
        self.bg_label = ctk.CTkLabel(self, text="")
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._on_resize)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_shell()
        self.load_bg()
        self.show("inicio")
        self.bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if sock:
            threading.Thread(target=self._listen, args=(sock,), daemon=True).start()
        if self.cfg["bandeja"]:
            self.start_tray()
        if self.cfg["widget"]:
            self.after(600, self.open_widget)
        if hidden and self.tray:
            self.withdraw()
        elif hidden:
            self.after(0, self._show_fallback_startup)
        else:
            self.after(0, self.show_splash)
        self.after(100, self.tick)
        self.after(2000, self.minute_loop)
        self.after(2500, self.notify_today)

    @property
    def accent(self):
        return ACCENTS.get(self.cfg["acento"], "#7c3aed")

    @property
    def hover(self):
        return mix(self.accent, "#ffffff", 0.18)

    def is_dark(self):
        return ctk.get_appearance_mode() == "Dark"

    def col(self, light, dark):
        return dark if self.is_dark() else light

    def btn(self, parent, text, command, width=0, kind="accent", **kw):
        if kind == "accent":
            fg, hv, tc = self.accent, self.hover, "white"
        elif kind == "danger":
            fg, hv, tc = "#ef4444", "#dc2626", "white"
        else:
            fg, hv, tc = ROW, ("#cbd5e1", "#3a3a55"), TEXT
        a = dict(text=text, command=command, height=38, corner_radius=12,
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 fg_color=fg, hover_color=hv, text_color=tc)
        if width:
            a["width"] = width
        a.update(kw)
        return ctk.CTkButton(parent, **a)

    def optmenu(self, parent, values, current, command, width=130):
        m = ctk.CTkOptionMenu(parent, values=values, command=command, width=width, height=34,
                              corner_radius=10, fg_color=self.accent, button_color=self.accent,
                              button_hover_color=self.hover)
        m.set(current)
        return m

    def switch(self, parent, text, value, command):
        sw = ctk.CTkSwitch(parent, text=text, progress_color=self.accent,
                           command=lambda: command(bool(sw.get())))
        if value:
            sw.select()
        return sw

    def title_label(self, parent, text, sub=None):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        if sub:
            ctk.CTkLabel(parent, text=sub, text_color=MUTED).pack(anchor="w", pady=(0, 12))

    def persist_config(self):
        try:
            save_cfg(self.cfg)
        except (OSError, TypeError) as error:
            messagebox.showerror("No se pudo guardar la configuración", str(error), parent=self)
            return False
        return True

    def load_cats(self):
        self.cats = {r["nombre"]: r["color"] for r in self.db.all("SELECT * FROM categorias ORDER BY id")}

    def refresh(self):
        """Redibuja la página actual (diferido para no destruir el botón que se está pulsando)."""
        if self._refresh_job:
            return

        def go():
            self._refresh_job = None
            self.show(self.current)
        self._refresh_job = self.after(10, go)

    def do_search(self, _=None):
        if self.search_entry.get().strip():
            self.search_q = self.search_entry.get()
            self.show("buscar")

    def tick(self):
        try:
            self.process_queue()
            self.pomo_tick()
        except Exception:
            pass
        self.after(100, self.tick)

    def minute_loop(self):
        try:
            if date.today() != self.today:
                self.today = date.today()
                self.refresh()
            self.check_reminders()
            self.widget_refresh()
        except Exception:
            pass
        self.after(15000, self.minute_loop)

    def check_reminders(self):
        now = datetime.now()
        iso, hm = now.date().isoformat(), now.strftime("%H:%M")
        rows = self.db.all(
            "SELECT * FROM tareas WHERE hecha=0 AND avisada=0 AND hora IS NOT NULL AND hora!='' "
            "AND (fecha<? OR (fecha=? AND hora<=?))", (iso, iso, hm))
        if not rows:
            return
        for r in rows:
            self.db.run("UPDATE tareas SET avisada=1 WHERE id=?", (r["id"],))
        if len(rows) <= 3:
            for r in rows:
                toast(f"⏰ {r['hora']}  {r['titulo']}", "Recordatorio de tu agenda")
        else:
            toast(f"⏰ Tienes {len(rows)} recordatorios", "\n".join(r["titulo"] for r in rows[:3]))
        if self.cfg["sonido"]:
            play_melody("alarm")

    def notify_today(self):
        iso = date.today().isoformat()
        rows = self.db.all("SELECT titulo FROM tareas WHERE hecha=0 AND fecha<=?", (iso,))
        if rows:
            toast(f"📅 Tienes {len(rows)} tarea(s) para hoy o vencidas",
                  "\n".join(r["titulo"] for r in rows[:3]))

    def process_queue(self):
        while True:
            try:
                cmd = self.q.get_nowait()
            except queue.Empty:
                return
            if cmd == "mostrar":
                self.show_window()
            elif cmd == "widget":
                self.toggle_widget()
            elif cmd == "salir":
                self.quit_app()

    def _listen(self, sock):
        while True:
            try:
                c, _ = sock.accept()
                c.close()
                self.q.put("mostrar")
            except OSError:
                return

    def show_window(self):
        self.deiconify()
        self.attributes("-alpha", 1.0)
        self.lift()
        self.focus_force()

    def _show_fallback_startup(self):
        self.deiconify()
        self.fade_in()

    def start_tray(self):
        if not pystray or self.tray:
            return
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Abrir Mi Agenda", lambda i, it: self.q.put("mostrar"), default=True),
                pystray.MenuItem("Widget flotante", lambda i, it: self.q.put("widget")),
                pystray.MenuItem("Salir", lambda i, it: self.q.put("salir")))
            self.tray = pystray.Icon("MiAgenda", make_tray_image(self.accent), "Mi Agenda", menu)
            self.tray.run_detached()
        except Exception:
            self.tray = None

    def stop_tray(self):
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None

    def on_close(self):
        if self.tray and self.cfg["bandeja"]:
            self.withdraw()
        else:
            self.quit_app()

    def quit_app(self):
        self.stop_tray()
        self.persist_config()
        self.db.con.close()
        try:
            self.destroy()
        except Exception:
            pass

    def bind_keys(self):
        b = self.bind_all
        b("<Control-n>", lambda e: self.go_new_task())
        b("<Control-f>", lambda e: self.search_entry.focus_set())
        b("<Control-p>", lambda e: self.pomo_toggle())
        shortcuts = ("inicio", "tareas", "calendario", "notas", "pomodoro",
                     "habitos", "metas", "diario", "gastos")
        for i, k in enumerate(shortcuts):
            b(f"<Control-Key-{i + 1}>", lambda e, k=k: self.show(k))
        b("<Control-Key-0>", lambda e: self.show("ajustes"))
        b("<F6>", lambda e: self.toggle_widget())
        b("<F7>", lambda e: self.toggle_mode())
        b("<F8>", lambda e: self.quick_backup())

    def go_new_task(self):
        self.focus_task = True
        self.show("tareas")

    def toggle_mode(self):
        self.cfg["modo"] = "light" if self.is_dark() else "dark"
        ctk.set_appearance_mode(self.cfg["modo"])
        self.persist_config()
        self.after(100, lambda: (self.render_bg(), self.refresh()))

    def auto_backup(self):
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            dst = os.path.join(BACKUP_DIR, f"agenda_{date.today().isoformat()}.db")
            if not os.path.exists(dst):
                self.db.backup_to(dst)
            files = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".db"))
            for old in files[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old))
        except Exception:
            pass

    def quick_backup(self):
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            dst = os.path.join(BACKUP_DIR, f"manual_{datetime.now():%Y%m%d_%H%M%S}.db")
            self.db.backup_to(dst)
            toast("💾 Copia de seguridad creada", dst)
        except Exception as e:
            messagebox.showerror("Copia", str(e))

    def stat_cards(self, parent, items, big=34):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", pady=(0, 10))
        for i, (n, t, c) in enumerate(items):
            fr.grid_columnconfigure(i, weight=1, uniform="s")
            card = ctk.CTkFrame(
                fr,
                corner_radius=18,
                fg_color=ROW,
                border_width=1,
                border_color="#e5e5ea",
            )
            card.grid(row=0, column=i, padx=5, sticky="ew")
            ctk.CTkLabel(card, text=str(n),
                         font=ctk.CTkFont(family="Segoe UI", size=big, weight="bold"), text_color=c
                         ).pack(pady=(10, 0))
            ctk.CTkLabel(card, text=t, text_color=MUTED).pack(pady=(0, 10))