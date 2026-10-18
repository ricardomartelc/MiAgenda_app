"""Floating task widget and its Pomodoro indicator."""
import math
import tkinter as tk
from datetime import date

import customtkinter as ctk

from src.config import CARD, MUTED, TEXT

TRANSP = "#010203"


class WidgetMixin:
    def widget_alive(self):
        try:
            return bool(self.widget and self.widget.winfo_exists())
        except tk.TclError:
            return False

    def toggle_widget(self):
        self.close_widget() if self.widget_alive() else self.open_widget()

    def open_widget(self):
        if self.widget_alive():
            return
        window = tk.Toplevel(self)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.attributes("-alpha", 0.96)
        window.configure(bg=TRANSP)
        try:
            window.attributes("-transparentcolor", TRANSP)
        except tk.TclError:
            pass
        x, y = self.cfg["widget_pos"]
        window.geometry(f"320x200+{x}+{y}")
        self.widget = window
        self.cfg["widget"] = True
        self.persist_config()
        self.widget_refresh()

    def close_widget(self):
        if self.widget_alive():
            self.widget.destroy()
        self.widget = self.w_pomo = None
        self.cfg["widget"] = False
        self.persist_config()
        if self.current == "ajustes":
            self.refresh()

    def widget_refresh(self):
        if not self.widget_alive():
            return
        window = self.widget
        for child in window.winfo_children():
            child.destroy()
        box = ctk.CTkFrame(
            window,
            corner_radius=18,
            fg_color=CARD,
            bg_color=TRANSP,
            border_width=2,
            border_color=self.accent,
        )
        box.pack(fill="both", expand=True)
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 2))
        label = ctk.CTkLabel(head, text="📅 Hoy", font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(side="left")
        ctk.CTkButton(
            head,
            text="✕",
            width=26,
            height=24,
            fg_color="transparent",
            hover_color="#ef4444",
            text_color=TEXT,
            command=lambda: self.after(10, self.close_widget),
        ).pack(side="right")
        self.w_pomo = ctk.CTkLabel(head, text="", text_color=MUTED)
        self.w_pomo.pack(side="right", padx=6)
        self._last_w_pomo = ""

        offset = {}

        def press(event):
            offset["x"] = event.x_root - window.winfo_x()
            offset["y"] = event.y_root - window.winfo_y()

        def drag(event):
            window.geometry(f"+{event.x_root - offset['x']}+{event.y_root - offset['y']}")

        def release(_event):
            self.cfg["widget_pos"] = [window.winfo_x(), window.winfo_y()]
            self.persist_config()

        for item in (head, label):
            item.bind("<ButtonPress-1>", press)
            item.bind("<B1-Motion>", drag)
            item.bind("<ButtonRelease-1>", release)

        today = date.today().isoformat()
        rows = self.db.all(
            "SELECT * FROM tareas WHERE hecha=0 AND fecha<=? ORDER BY fecha, hora IS NULL, hora",
            (today,),
        )
        if not rows:
            ctk.CTkLabel(box, text="Nada pendiente hoy 🎉", text_color=MUTED).pack(pady=8)
        for task in rows[:6]:
            variable = ctk.BooleanVar(value=False)
            text = (f"{task['hora']}  " if task["hora"] else "") + task["titulo"]
            ctk.CTkCheckBox(
                box,
                text=text[:34],
                variable=variable,
                fg_color=self.accent,
                hover_color=self.accent,
                corner_radius=8,
                command=lambda task=task: self.after(150, lambda: self.toggle_task(task, True)),
            ).pack(anchor="w", padx=14, pady=3)
        if len(rows) > 6:
            ctk.CTkLabel(
                box,
                text=f"+{len(rows) - 6} más…",
                text_color=MUTED,
            ).pack(anchor="w", padx=16)
        entry = ctk.CTkEntry(box, placeholder_text="＋ Añadir rápido…", height=30, corner_radius=10)
        entry.pack(fill="x", padx=12, pady=(6, 12))
        try:
            entry._entry.bind("<Button-1>", lambda _event: entry._entry.focus_force())
        except tk.TclError:
            pass

        def add_quick_task(_event=None):
            if entry.get().strip():
                self.add_task(entry.get(), "hoy")
                self.refresh()

        entry.bind("<Return>", add_quick_task)
        window.update_idletasks()
        window.geometry(f"320x{box.winfo_reqheight()}+{window.winfo_x()}+{window.winfo_y()}")
        self.widget_pomo_update(force=True)

    def widget_pomo_update(self, force=False):
        if not self.w_pomo:
            return
        pomo = self.pomo
        text = ""
        if pomo["corriendo"] or pomo["restante"] < pomo["total"]:
            minutes, seconds = divmod(int(math.ceil(pomo["restante"])), 60)
            text = f"🍅 {minutes:02d}:{seconds:02d}"
        if text != self._last_w_pomo or force:
            self._last_w_pomo = text
            try:
                self.w_pomo.configure(text=text)
            except tk.TclError:
                self.w_pomo = None
