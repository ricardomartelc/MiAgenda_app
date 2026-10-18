"""UI behavior for the corresponding Mi Agenda pages."""
import csv
import json
import os
import customtkinter as ctk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox

try:
    import pystray
except Exception:
    pystray = None
try:
    import winreg
except Exception:
    winreg = None

from src.config import ACCENTS, APP_DIR, CAT_COLORS, GASTO_CATS, MESES, MUTED, ROW, TEXT
from src.utils import add_months, autostart_enabled, fmt_d, money, parse_date, set_autostart


class ManagementPagesMixin:
    def page_gastos(self, p):
        self.title_label(p, "Gastos e ingresos")
        nav = ctk.CTkFrame(p, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 8))

        def mover(n):
            self.gas_m += n
            if self.gas_m == 0:
                self.gas_m, self.gas_y = 12, self.gas_y - 1
            elif self.gas_m == 13:
                self.gas_m, self.gas_y = 1, self.gas_y + 1
            self.refresh()

        self.btn(nav, "◀", lambda: mover(-1), width=40).pack(side="left")
        ctk.CTkLabel(nav, text=f"{MESES[self.gas_m - 1]} {self.gas_y}",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=14)
        self.btn(nav, "▶", lambda: mover(1), width=40).pack(side="left")

        rows = self.db.all("SELECT * FROM gastos WHERE fecha LIKE ? ORDER BY fecha DESC, id DESC",
                           (f"{self.gas_y:04d}-{self.gas_m:02d}-%",))
        ing = sum(r["cantidad"] for r in rows if r["tipo"] == "Ingreso")
        gas = sum(r["cantidad"] for r in rows if r["tipo"] == "Gasto")
        self.stat_cards(p, [(money(ing), "Ingresos", "#22c55e"), (money(gas), "Gastos", "#ef4444"),
                            (money(ing - gas), "Balance", "#22c55e" if ing >= gas else "#ef4444")], big=24)

        body = ctk.CTkFrame(p, fg_color="transparent")
        body.pack(fill="both", expand=True)
        right = ctk.CTkFrame(body, fg_color=ROW, corner_radius=18, width=300)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        f1 = ctk.CTkFrame(left, fg_color="transparent")
        f1.pack(fill="x", pady=(0, 6))
        e_c = ctk.CTkEntry(f1, placeholder_text="Concepto…", height=36)
        e_c.pack(side="left", fill="x", expand=True, padx=(0, 6))
        e_q = ctk.CTkEntry(f1, placeholder_text="Cantidad €", width=100, height=36)
        e_q.pack(side="left")
        f2 = ctk.CTkFrame(left, fg_color="transparent")
        f2.pack(fill="x", pady=(0, 4))
        tipo = ctk.CTkSegmentedButton(f2, values=["Gasto", "Ingreso"], selected_color=self.accent,
                                      selected_hover_color=self.accent)
        tipo.set("Gasto")
        tipo.pack(side="left", padx=(0, 6))
        cat = self.optmenu(f2, GASTO_CATS, "Comida", None, 120)
        cat.pack(side="left", padx=(0, 6))
        e_f = ctk.CTkEntry(f2, placeholder_text="dd/mm/aaaa", width=100, height=34)
        e_f.pack(side="left", padx=(0, 6))
        err = ctk.CTkLabel(left, text="", text_color="#ef4444", height=16)

        def anadir(_=None):
            try:
                q = float(e_q.get().replace(",", "."))
                if q <= 0 or not e_c.get().strip():
                    raise ValueError
            except ValueError:
                err.configure(text="Escribe concepto y una cantidad válida")
                return
            try:
                f = parse_date(e_f.get()) if e_f.get().strip() else date.today()
            except ValueError:
                err.configure(text="Fecha no válida")
                return
            self.db.run("INSERT INTO gastos(fecha,concepto,cantidad,tipo,categoria) VALUES(?,?,?,?,?)",
                        (f.isoformat(), e_c.get().strip(), q, tipo.get(),
                         "Ingreso" if tipo.get() == "Ingreso" else cat.get()))
            self.gas_y, self.gas_m = f.year, f.month
            self.refresh()

        self.btn(f2, "Añadir", anadir, width=80, height=34).pack(side="left")
        e_c.bind("<Return>", anadir)
        e_q.bind("<Return>", anadir)
        err.pack(anchor="w")

        sc = ctk.CTkScrollableFrame(left, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        if not rows:
            ctk.CTkLabel(sc, text="Sin movimientos este mes", text_color=MUTED).pack(pady=20)
        for r in rows:
            fr = ctk.CTkFrame(sc, corner_radius=10, fg_color=ROW)
            fr.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(fr, text=fmt_d(r["fecha"])[:5], text_color=MUTED, width=46).pack(side="left", padx=(8, 4), pady=8)
            ctk.CTkLabel(fr, text=f"{r['concepto']}  ·  {r['categoria']}").pack(side="left")
            ctk.CTkButton(fr, text="🗑", width=30, height=26, fg_color="transparent", hover_color="#ef4444",
                          text_color=TEXT, command=lambda i=r["id"]: self.del_gasto(i)).pack(side="right", padx=4)
            es_ing = r["tipo"] == "Ingreso"
            ctk.CTkLabel(fr, text=("+" if es_ing else "-") + money(r["cantidad"]),
                         text_color="#22c55e" if es_ing else "#ef4444",
                         font=ctk.CTkFont(weight="bold")).pack(side="right", padx=6)

        ctk.CTkLabel(right, text="Gastos por categoría", font=ctk.CTkFont(size=15, weight="bold")
                     ).pack(pady=(14, 8))
        por = {}
        for r in rows:
            if r["tipo"] == "Gasto":
                por[r["categoria"]] = por.get(r["categoria"], 0) + r["cantidad"]
        if not por:
            ctk.CTkLabel(right, text="Sin gastos", text_color=MUTED).pack(pady=10)
        for k, v in sorted(por.items(), key=lambda x: -x[1]):
            fr = ctk.CTkFrame(right, fg_color="transparent")
            fr.pack(fill="x", padx=14, pady=4)
            ctk.CTkLabel(fr, text=k).pack(side="left")
            ctk.CTkLabel(fr, text=money(v), text_color=MUTED).pack(side="right")
            b = ctk.CTkProgressBar(right, height=8, progress_color=self.accent)
            b.pack(fill="x", padx=14)
            b.set(v / gas if gas else 0)

    def del_gasto(self, i):
        self.db.run("DELETE FROM gastos WHERE id=?", (i,))
        self.refresh()

    def page_stats(self, p):
        self.title_label(p, "Estadísticas", "Tu actividad de un vistazo")
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception:
            ctk.CTkLabel(p, text="Falta matplotlib. Ejecuta en la terminal:\n\npip install matplotlib",
                         font=ctk.CTkFont(size=16)).pack(expand=True)
            return
        bg, fg = self.col("#ffffff", "#1c1c2b"), self.col("#334155", "#cbd5e1")
        grid = self.col("#e2e8f0", "#2e2e45")
        fig = Figure(figsize=(9, 6), dpi=100, facecolor=bg)
        axs = fig.subplots(2, 2)
        for ax in axs.flat:
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=8)
            for s in ax.spines.values():
                s.set_color(grid)
            ax.grid(axis="y", color=grid, linewidth=0.6)
            ax.set_axisbelow(True)

        def vacio(ax):
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.text(0.5, 0.5, "Sin datos todavía", ha="center", va="center", color=fg, transform=ax.transAxes)

        today = date.today()
        # 1) tareas completadas por semana
        ax = axs[0][0]
        lun = today - timedelta(days=today.weekday())
        labs, vals = [], []
        for i in range(7, -1, -1):
            a = lun - timedelta(weeks=i)
            b = a + timedelta(days=6)
            labs.append(a.strftime("%d/%m"))
            vals.append(self.db.one("SELECT COUNT(*) FROM tareas WHERE hecha=1 AND COALESCE(hecha_en,fecha) BETWEEN ? AND ?",
                                    (a.isoformat(), b.isoformat())))
        ax.bar(labs, vals, color=self.accent)
        ax.set_title("Tareas completadas por semana", color=fg, fontsize=10)
        ax.yaxis.get_major_locator().set_params(integer=True)
        if not any(vals):
            vacio(ax)
        # 2) tareas por categoría
        ax = axs[0][1]
        rows = self.db.all("SELECT COALESCE(NULLIF(categoria,''),'Sin categoría') c, SUM(hecha) h, "
                           "COUNT(*)-SUM(hecha) p FROM tareas GROUP BY c ORDER BY COUNT(*) DESC LIMIT 7")
        if rows:
            names = [r["c"] for r in rows]
            hh = [r["h"] or 0 for r in rows]
            pp = [r["p"] or 0 for r in rows]
            ax.barh(names, hh, color="#22c55e", label="Hechas")
            ax.barh(names, pp, left=hh, color=self.accent, label="Pendientes")
            ax.invert_yaxis()
            leg = ax.legend(fontsize=8, facecolor=bg, edgecolor=grid)
            for t in leg.get_texts():
                t.set_color(fg)
        else:
            vacio(ax)
        ax.set_title("Tareas por categoría", color=fg, fontsize=10)
        # 3) minutos de pomodoro por día
        ax = axs[1][0]
        labs, vals = [], []
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            labs.append(d.strftime("%d"))
            vals.append(self.db.one("SELECT SUM(minutos) FROM pomodoros WHERE fecha=?", (d.isoformat(),)))
        ax.bar(labs, vals, color="#ef4444")
        ax.set_title("Minutos de concentración (14 días)", color=fg, fontsize=10)
        if not any(vals):
            vacio(ax)
        # 4) ingresos vs gastos por mes
        ax = axs[1][1]
        labs, ing, gas = [], [], []
        for i in range(5, -1, -1):
            m = add_months(today.replace(day=1), -i)
            pref = f"{m.year:04d}-{m.month:02d}-%"
            labs.append(MESES[m.month - 1][:3])
            ing.append(self.db.one("SELECT SUM(cantidad) FROM gastos WHERE tipo='Ingreso' AND fecha LIKE ?", (pref,)))
            gas.append(self.db.one("SELECT SUM(cantidad) FROM gastos WHERE tipo='Gasto' AND fecha LIKE ?", (pref,)))
        xs = range(len(labs))
        ax.bar([x - 0.2 for x in xs], ing, width=0.4, color="#22c55e", label="Ingresos")
        ax.bar([x + 0.2 for x in xs], gas, width=0.4, color="#ef4444", label="Gastos")
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labs)
        ax.set_title("Ingresos vs gastos (€)", color=fg, fontsize=10)
        if any(ing) or any(gas):
            leg = ax.legend(fontsize=8, facecolor=bg, edgecolor=grid)
            for t in leg.get_texts():
                t.set_color(fg)
        else:
            vacio(ax)
        fig.tight_layout(pad=2.0)
        cv = FigureCanvasTkAgg(fig, master=p)
        cv.get_tk_widget().configure(bg=bg, highlightthickness=0)
        cv.get_tk_widget().pack(fill="both", expand=True)
        cv.draw()

    def page_ajustes(self, p):
        self.title_label(p, "Ajustes", "Personaliza y gestiona tus datos")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)

        def sec(txt):
            ctk.CTkLabel(sc, text=txt, font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", pady=(16, 6))

        # --- apariencia
        sec("🎨 Apariencia")
        self.switch(sc, "Modo oscuro  (F7)", self.is_dark(), lambda v: self.toggle_mode()).pack(anchor="w", pady=4)
        fila = ctk.CTkFrame(sc, fg_color="transparent")
        fila.pack(anchor="w", pady=4)
        ctk.CTkLabel(fila, text="Color de acento:").pack(side="left", padx=(0, 8))

        def acento(n):
            self.cfg["acento"] = n
            self.persist_config()
            self.render_bg()
            if self.tray:
                self.stop_tray()
                self.start_tray()
            self.refresh()

        for n, c in ACCENTS.items():
            ctk.CTkButton(fila, text="", width=32, height=32, corner_radius=16, fg_color=c, hover_color=c,
                          border_width=3 if n == self.cfg["acento"] else 0, border_color="white",
                          command=lambda x=n: acento(x)).pack(side="left", padx=3)
        fb = ctk.CTkFrame(sc, fg_color="transparent")
        fb.pack(anchor="w", pady=6)

        def elegir():
            f = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp")])
            if f:
                self.cfg["fondo"] = f
                self.persist_config()
                self.load_bg()

        def quitar():
            self.cfg["fondo"] = ""
            self.persist_config()
            self.load_bg()

        self.btn(fb, "🖼 Elegir fondo…", elegir, width=150).pack(side="left", padx=(0, 8))
        self.btn(fb, "Quitar fondo", quitar, width=120, kind="soft").pack(side="left")

        # --- sistema
        sec("🖥 Sistema")
        self.switch(sc, "Seguir en segundo plano al cerrar (icono junto al reloj)", self.cfg["bandeja"],
                    self.set_bandeja).pack(anchor="w", pady=4)
        if winreg:
            self.switch(sc, "Iniciar con Windows (oculta en la bandeja)", autostart_enabled(),
                        lambda v: set_autostart(v)).pack(anchor="w", pady=4)
        self.switch(sc, "Widget flotante de tareas de hoy  (F6)", bool(self.widget and self.widget.winfo_exists()),
                    lambda v: self.open_widget() if v else self.close_widget()).pack(anchor="w", pady=4)
        self.switch(sc, "Sonidos en avisos y pomodoro", self.cfg["sonido"], self.set_sonido).pack(anchor="w", pady=4)
        if not pystray:
            ctk.CTkLabel(sc, text="(Para el icono de bandeja instala: pip install pystray)",
                         text_color=MUTED).pack(anchor="w")

        # --- categorías
        sec("🏷 Categorías de tareas")
        for nombre, color in self.cats.items():
            fr = ctk.CTkFrame(sc, fg_color=ROW, corner_radius=10)
            fr.pack(fill="x", pady=2)
            ctk.CTkFrame(fr, width=16, height=16, corner_radius=8, fg_color=color).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(fr, text=nombre).pack(side="left")
            ctk.CTkButton(fr, text="🗑", width=30, height=26, fg_color="transparent", hover_color="#ef4444",
                          text_color=TEXT, command=lambda n=nombre: self.del_cat(n)).pack(side="right", padx=6)
        fr = ctk.CTkFrame(sc, fg_color="transparent")
        fr.pack(fill="x", pady=6)
        e_c = ctk.CTkEntry(fr, placeholder_text="Nueva categoría…", width=220, height=34)
        e_c.pack(side="left", padx=(0, 6))
        col = self.optmenu(fr, list(CAT_COLORS), "Azul", None, 110)
        col.pack(side="left", padx=(0, 6))

        def add_cat(_=None):
            n = e_c.get().strip()
            if n:
                self.db.run("INSERT OR IGNORE INTO categorias(nombre,color) VALUES(?,?)", (n, CAT_COLORS[col.get()]))
                self.refresh()

        self.btn(fr, "Añadir", add_cat, width=80, height=34).pack(side="left")
        e_c.bind("<Return>", add_cat)

        # --- datos
        sec("💾 Datos y copias de seguridad")
        ctk.CTkLabel(sc, text=f"Carpeta de datos: {APP_DIR}\nCopia automática diaria en la subcarpeta 'backups' (últimas 10).",
                     text_color=MUTED, justify="left").pack(anchor="w", pady=(0, 6))
        fd = ctk.CTkFrame(sc, fg_color="transparent")
        fd.pack(anchor="w")
        self.btn(fd, "Exportar todo (JSON)", self.export_json, width=170).pack(side="left", padx=(0, 8), pady=3)
        self.btn(fd, "Importar copia (JSON)", self.import_json, width=170, kind="soft").pack(side="left", padx=(0, 8), pady=3)
        self.btn(fd, "Tareas a CSV", self.export_csv, width=130, kind="soft").pack(side="left", padx=(0, 8), pady=3)
        self.btn(fd, "Abrir carpeta", lambda: os.startfile(APP_DIR) if hasattr(os, "startfile") else None,
                 width=130, kind="soft").pack(side="left", pady=3)

        # --- atajos
        sec("⌨ Atajos de teclado")
        atajos = ("Ctrl+N  nueva tarea        Ctrl+F  buscar        Ctrl+P  iniciar/pausar pomodoro\n"
                  "Ctrl+1…9  ir a cada sección        Ctrl+0  ajustes\n"
                  "F6  widget flotante        F7  modo oscuro/claro        F8  copia de seguridad rápida")
        ctk.CTkLabel(sc, text=atajos, justify="left", text_color=MUTED).pack(anchor="w", pady=(0, 20))

    def set_bandeja(self, v):
        self.cfg["bandeja"] = v
        self.persist_config()
        self.start_tray() if v else self.stop_tray()

    def set_sonido(self, v):
        self.cfg["sonido"] = v
        self.persist_config()

    def del_cat(self, n):
        self.db.run("DELETE FROM categorias WHERE nombre=?", (n,))
        self.refresh()

    def export_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")],
                                         initialfile=f"agenda_{date.today().isoformat()}.json")
        if not f:
            return
        with open(f, "w", encoding="utf-8") as fh:
            json.dump({"version": 2, "exportado": datetime.now().isoformat(), "datos": self.db.export_all()},
                      fh, ensure_ascii=False, indent=1)
        messagebox.showinfo("Exportado", f"Copia guardada en:\n{f}")

    def import_json(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not f:
            return
        if not messagebox.askyesno("Importar", "Esto REEMPLAZARÁ todos tus datos actuales por los de la copia.\n"
                                               "(Se hará antes una copia automática.)\n\n¿Continuar?"):
            return
        try:
            self.quick_backup()
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            self.db.import_all(data.get("datos", data))
            self.note_id = self.hab_sel = None
            messagebox.showinfo("Importado", "Datos importados correctamente.")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error al importar", str(e))

    def export_csv(self):
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                         initialfile="tareas.csv")
        if not f:
            return
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Título", "Fecha", "Hora", "Prioridad", "Categoría", "Repetición", "Hecha"])
            for t in self.db.all("SELECT * FROM tareas ORDER BY fecha"):
                w.writerow([t["titulo"], fmt_d(t["fecha"]), t["hora"] or "", t["prioridad"],
                            t["categoria"] or "", t["recurrencia"] or "", "Sí" if t["hecha"] else "No"])
        messagebox.showinfo("Exportado", f"Tareas guardadas en:\n{f}")
