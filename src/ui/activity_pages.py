"""UI behavior for the corresponding Mi Agenda pages."""
import calendar
import customtkinter as ctk
from datetime import date, datetime
from src.config import DIAS, MESES, MOODS, MUTED, PRIO, ROW, TEXT
from src.utils import add_months, fmt_d, money, next_date, parse_date, parse_time


class ActivityPagesMixin:
    def add_task(self, titulo, fecha_txt="", hora_txt="", prio="Media", cat="", rec=""):
        titulo = titulo.strip()
        if not titulo:
            return "Escribe un título"
        try:
            f = parse_date(fecha_txt) if fecha_txt.strip() else None
        except ValueError:
            return "Fecha no válida (dd/mm/aaaa, 'hoy' o 'mañana')"
        try:
            h = parse_time(hora_txt)
        except ValueError:
            return "Hora no válida (HH:MM)"
        if (h or rec) and not f:
            f = date.today()
        if cat in ("Sin categoría", None):
            cat = ""
        if rec == "No repetir":
            rec = ""
        self.db.run("INSERT INTO tareas(titulo,fecha,hora,prioridad,categoria,recurrencia) VALUES(?,?,?,?,?,?)",
                    (titulo, f.isoformat() if f else None, h, prio, cat, rec))
        return None

    def toggle_task(self, t, done):
        hoy = date.today()
        self.db.run("UPDATE tareas SET hecha=?, hecha_en=? WHERE id=?",
                    (int(done), hoy.isoformat() if done else None, t["id"]))
        if done and t["recurrencia"] and not t["generada"]:
            try:
                base = datetime.strptime(t["fecha"], "%Y-%m-%d").date() if t["fecha"] else hoy
            except Exception:
                base = hoy
            if t["recurrencia"] == "Mensual":  # se calcula desde el día original (31 -> 28 -> 31...)
                k = 1
                while add_months(base, k) <= hoy:
                    k += 1
                nueva = add_months(base, k)
            else:
                nueva = next_date(base, t["recurrencia"])
                while nueva <= hoy:
                    nueva = next_date(nueva, t["recurrencia"])
            self.db.run("INSERT INTO tareas(titulo,fecha,hora,prioridad,categoria,recurrencia) VALUES(?,?,?,?,?,?)",
                        (t["titulo"], nueva.isoformat(), t["hora"], t["prioridad"], t["categoria"], t["recurrencia"]))
            self.db.run("UPDATE tareas SET generada=1 WHERE id=?", (t["id"],))
        self.refresh()

    def delete_task(self, tid):
        self.db.run("DELETE FROM tareas WHERE id=?", (tid,))
        self.refresh()

    def task_row(self, parent, t):
        row = ctk.CTkFrame(parent, corner_radius=18, fg_color=ROW)
        row.pack(fill="x", pady=3, padx=2)
        ctk.CTkFrame(row, width=6, height=8, corner_radius=3, fg_color=PRIO.get(t["prioridad"], "#888")
                     ).pack(side="left", fill="y", padx=(10, 8), pady=10)
        var = ctk.BooleanVar(value=bool(t["hecha"]))
        ctk.CTkCheckBox(row, text=t["titulo"], variable=var, font=ctk.CTkFont(size=15, overstrike=bool(t["hecha"])),
                        command=lambda: self.toggle_task(t, var.get()), fg_color=self.accent,
                        hover_color=self.accent, corner_radius=8).pack(side="left", pady=11)
        ctk.CTkButton(row, text="🗑", width=34, height=30, fg_color="transparent", hover_color="#ef4444",
                      text_color=TEXT, command=lambda: self.delete_task(t["id"])).pack(side="right", padx=6)
        if t["fecha"]:
            vencida = (not t["hecha"]) and t["fecha"] < date.today().isoformat()
            ctk.CTkLabel(row, text=f"📆 {fmt_d(t['fecha'])}", text_color="#ef4444" if vencida else MUTED
                         ).pack(side="right", padx=4)
        if t["hora"]:
            ctk.CTkLabel(row, text=f"⏰ {t['hora']}", text_color=MUTED).pack(side="right", padx=4)
        if t["recurrencia"]:
            ctk.CTkLabel(row, text=f"🔁 {t['recurrencia']}", text_color=MUTED).pack(side="right", padx=4)
        if t["categoria"]:
            color = self.cats.get(t["categoria"], "#64748b")
            ctk.CTkLabel(row, text=f"  {t['categoria']}  ", fg_color=color, text_color="white", corner_radius=8,
                         font=ctk.CTkFont(size=11)).pack(side="right", padx=6)

    def page_inicio(self, p):
        h = datetime.now().hour
        saludo = "Buenos días" if h < 13 else "Buenas tardes" if h < 21 else "Buenas noches"
        t0 = self.today
        self.title_label(
            p,
            f"{saludo}  👋",
            f"{DIAS[t0.weekday()]} {t0.day} de {MESES[t0.month - 1]} de {t0.year}",
        )
        quick_actions = ctk.CTkFrame(p, fg_color="transparent")
        quick_actions.pack(fill="x", pady=(0, 8))
        self.btn(quick_actions, "＋  Nueva tarea", self.go_new_task, width=150).pack(side="left", padx=(4, 6))
        self.btn(quick_actions, "🍅  Pomodoro", lambda: self.show("pomodoro"),
                 width=140, kind="soft").pack(side="left", padx=6)
        iso = t0.isoformat()
        total = self.db.one("SELECT COUNT(*) FROM tareas")
        hechas = self.db.one("SELECT COUNT(*) FROM tareas WHERE hecha=1")
        self.stat_cards(p, [
            (total - hechas, "Pendientes", self.accent),
            (self.db.one("SELECT COUNT(*) FROM tareas WHERE hecha=0 AND fecha=?", (iso,)), "Para hoy", "#f59e0b"),
            (self.db.one("SELECT COUNT(*) FROM tareas WHERE hecha=0 AND fecha<?", (iso,)), "Vencidas", "#ef4444"),
            (hechas, "Completadas", "#22c55e")])

        nh = self.db.one("SELECT COUNT(*) FROM habitos")
        hh = self.db.one("SELECT COUNT(*) FROM habito_log WHERE fecha=?", (iso,))
        pom = self.db.one("SELECT COUNT(*) FROM pomodoros WHERE fecha=?", (iso,))
        pref = f"{t0.year:04d}-{t0.month:02d}-%"
        bal = self.db.one("SELECT SUM(CASE WHEN tipo='Ingreso' THEN cantidad ELSE -cantidad END) "
                          "FROM gastos WHERE fecha LIKE ?", (pref,))
        am = self.db.all("SELECT valor FROM animo WHERE fecha=?", (iso,))
        emoji = dict(MOODS).get(am[0]["valor"], "—") if am else "—"
        self.stat_cards(p, [(f"{hh}/{nh}", "Hábitos hoy", "#f97316"), (f"🍅 {pom}", "Pomodoros hoy", "#ef4444"),
                            (money(bal), "Balance del mes", "#22c55e" if bal >= 0 else "#ef4444"),
                            (emoji, "Ánimo hoy", self.accent)], big=26)

        bar = ctk.CTkProgressBar(p, height=12, progress_color=self.accent)
        bar.pack(fill="x", pady=(2, 12))
        bar.set(0)
        self.animate_bar(bar, hechas / total if total else 0)
        ctk.CTkLabel(p, text="Próximas tareas", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        rows = self.db.all("SELECT * FROM tareas WHERE hecha=0 ORDER BY fecha IS NULL, fecha, hora IS NULL, hora LIMIT 8")
        if not rows:
            ctk.CTkLabel(sc, text="Todo al día 🎉", text_color=MUTED).pack(pady=20)
        for t in rows:
            self.task_row(sc, t)

    def animate_bar(self, bar, target, cur=0.0):
        cur = min(cur + max(target / 25, 0.01), target)
        try:
            bar.set(cur)
            if cur < target:
                self.after(16, lambda: self.animate_bar(bar, target, cur))
        except Exception:
            pass

    def page_tareas(self, p):
        self.title_label(p, "Tareas")
        cats = ["Sin categoría"] + list(self.cats)
        f1 = ctk.CTkFrame(p, fg_color="transparent")
        f1.pack(fill="x", pady=(0, 6))
        e_t = ctk.CTkEntry(f1, placeholder_text="Nueva tarea…", height=40, corner_radius=12)
        e_t.pack(side="left", fill="x", expand=True, padx=(0, 8))
        f2 = ctk.CTkFrame(p, fg_color="transparent")
        f2.pack(fill="x", pady=(0, 4))
        e_f = ctk.CTkEntry(f2, placeholder_text="Fecha dd/mm/aaaa", width=130, height=34, corner_radius=10)
        e_f.pack(side="left", padx=(0, 6))
        e_h = ctk.CTkEntry(f2, placeholder_text="Hora HH:MM", width=100, height=34, corner_radius=10)
        e_h.pack(side="left", padx=(0, 6))
        prio = ctk.CTkSegmentedButton(f2, values=list(PRIO), selected_color=self.accent,
                                      selected_hover_color=self.accent)
        prio.set("Media")
        prio.pack(side="left", padx=(0, 6))
        cat = self.optmenu(f2, cats, "Sin categoría", None, 140)
        cat.pack(side="left", padx=(0, 6))
        rec = self.optmenu(f2, ["No repetir", "Diaria", "Semanal", "Mensual"], "No repetir", None, 120)
        rec.pack(side="left")
        err = ctk.CTkLabel(p, text="", text_color="#ef4444", height=18)
        err.pack(anchor="w")

        def anadir(_=None):
            msg = self.add_task(e_t.get(), e_f.get(), e_h.get(), prio.get(), cat.get(), rec.get())
            if msg:
                err.configure(text=msg)
            else:
                self.refresh()

        self.btn(f1, "Añadir", anadir, width=90, height=40).pack(side="left")
        e_t.bind("<Return>", anadir)
        e_f.bind("<Return>", anadir)
        e_h.bind("<Return>", anadir)
        e_t.focus()
        self.focus_task = False

        f3 = ctk.CTkFrame(p, fg_color="transparent")
        f3.pack(fill="x", pady=(2, 6))
        ctk.CTkLabel(f3, text="Filtrar:", text_color=MUTED).pack(side="left", padx=(2, 6))

        def set_f(k):
            def fn(v):
                self.filt[k] = v
                self.refresh()
            return fn

        self.optmenu(f3, ["Todas"] + cats, self.filt["cat"] if self.filt["cat"] in ["Todas"] + cats else "Todas",
                     set_f("cat"), 150).pack(side="left", padx=(0, 8))
        seg = ctk.CTkSegmentedButton(f3, values=["Pendientes", "Todas", "Hechas"], command=set_f("estado"),
                                     selected_color=self.accent, selected_hover_color=self.accent)
        seg.set(self.filt["estado"])
        seg.pack(side="left")

        sql, args = "SELECT * FROM tareas WHERE 1=1", []
        if self.filt["estado"] == "Pendientes":
            sql += " AND hecha=0"
        elif self.filt["estado"] == "Hechas":
            sql += " AND hecha=1"
        if self.filt["cat"] != "Todas":
            sql += " AND categoria=?"
            args.append("" if self.filt["cat"] == "Sin categoría" else self.filt["cat"])
        sql += " ORDER BY hecha, fecha IS NULL, fecha, hora IS NULL, hora"
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        rows = self.db.all(sql, args)
        if not rows:
            ctk.CTkLabel(sc, text="No hay tareas con este filtro", text_color=MUTED).pack(pady=20)
        for t in rows:
            self.task_row(sc, t)

    def page_calendario(self, p):
        self.title_label(p, "Calendario")
        left = ctk.CTkFrame(p, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        right = ctk.CTkFrame(p, fg_color=ROW, corner_radius=18, width=360)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(fill="x", pady=(0, 8))

        def mover(d):
            self.cal_m += d
            if self.cal_m == 0:
                self.cal_m, self.cal_y = 12, self.cal_y - 1
            elif self.cal_m == 13:
                self.cal_m, self.cal_y = 1, self.cal_y + 1
            self.refresh()

        self.btn(nav, "◀", lambda: mover(-1), width=40).pack(side="left")
        ctk.CTkLabel(nav, text=f"{MESES[self.cal_m - 1]} {self.cal_y}",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", expand=True)
        self.btn(nav, "▶", lambda: mover(1), width=40).pack(side="right")

        grid = ctk.CTkFrame(left, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for c in range(7):
            grid.grid_columnconfigure(c, weight=1, uniform="d")
            ctk.CTkLabel(grid, text=DIAS[c], text_color=MUTED).grid(row=0, column=c, pady=4)
        pref = f"{self.cal_y:04d}-{self.cal_m:02d}-"
        con = {r["fecha"] for r in self.db.all(
            "SELECT DISTINCT fecha FROM tareas WHERE hecha=0 AND fecha LIKE ?", (pref + "%",))}
        for r, semana in enumerate(calendar.monthcalendar(self.cal_y, self.cal_m), start=1):
            grid.grid_rowconfigure(r, weight=1)
            for c, d in enumerate(semana):
                if d == 0:
                    continue
                dt = date(self.cal_y, self.cal_m, d)
                sel, hoy = dt == self.sel_day, dt == self.today
                ctk.CTkButton(grid, text=f"{d}" + (" •" if dt.isoformat() in con else ""), corner_radius=12,
                              fg_color=self.accent if sel else ("#e2e8f0", "#2e2e45"), hover_color=self.hover,
                              text_color="white" if sel else TEXT, border_width=2 if hoy else 0,
                              border_color=self.accent, command=lambda x=dt: self.pick_day(x)
                              ).grid(row=r, column=c, padx=3, pady=3, sticky="nsew")

        ctk.CTkLabel(right, text=f"{self.sel_day.day} de {MESES[self.sel_day.month - 1]}",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(14, 6))
        fr = ctk.CTkFrame(right, fg_color="transparent")
        fr.pack(fill="x", padx=12)
        e = ctk.CTkEntry(fr, placeholder_text="Nueva tarea…", height=36, corner_radius=10)
        e.pack(side="left", fill="x", expand=True, padx=(0, 6))
        eh = ctk.CTkEntry(fr, placeholder_text="HH:MM", width=64, height=36, corner_radius=10)
        eh.pack(side="left")

        def anadir(_=None):
            if not self.add_task(e.get(), self.sel_day.strftime("%d/%m/%Y"), eh.get()):
                self.refresh()
            else:
                eh.configure(border_color="#ef4444")

        e.bind("<Return>", anadir)
        eh.bind("<Return>", anadir)
        sc = ctk.CTkScrollableFrame(right, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=6, pady=10)
        for t in self.db.all("SELECT * FROM tareas WHERE fecha=? ORDER BY hecha, hora IS NULL, hora",
                             (self.sel_day.isoformat(),)):
            self.task_row(sc, t)

    def pick_day(self, d):
        self.sel_day = d
        self.refresh()

    def page_notas(self, p):
        self.title_label(p, "Notas", "Se guardan solas mientras escribes")
        left = ctk.CTkFrame(p, fg_color="transparent", width=240)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)
        right = ctk.CTkFrame(p, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        def nueva():
            self.note_id = self.db.run("INSERT INTO notas(titulo,texto) VALUES('Nueva nota','')").lastrowid
            self.refresh()

        self.btn(left, "＋ Nueva nota", nueva).pack(fill="x", pady=(0, 8))
        sc = ctk.CTkScrollableFrame(left, fg_color="transparent")
        sc.pack(fill="both", expand=True)

        def abrir(i):
            self.note_id = i
            self.refresh()

        for n in self.db.all("SELECT * FROM notas ORDER BY id DESC"):
            on = n["id"] == self.note_id
            ctk.CTkButton(sc, text=(n["titulo"] or "Sin título")[:26], anchor="w", height=36, corner_radius=10,
                          fg_color=self.accent if on else ROW, hover_color=self.hover,
                          text_color="white" if on else TEXT, command=lambda i=n["id"]: abrir(i)
                          ).pack(fill="x", pady=2)
        row = self.db.all("SELECT * FROM notas WHERE id=?", (self.note_id,)) if self.note_id else []
        if not row:
            ctk.CTkLabel(right, text="Selecciona o crea una nota", text_color=MUTED).pack(expand=True)
            return
        n = row[0]
        e_t = ctk.CTkEntry(right, height=40, corner_radius=12, font=ctk.CTkFont(size=18, weight="bold"))
        e_t.insert(0, n["titulo"] or "")
        e_t.pack(fill="x", pady=(0, 8))
        tb = ctk.CTkTextbox(right, corner_radius=12, font=ctk.CTkFont(size=15), fg_color=ROW)
        tb.insert("1.0", n["texto"] or "")
        tb.pack(fill="both", expand=True)
        nid = self.note_id

        def guardar():
            self.db.run("UPDATE notas SET titulo=?, texto=? WHERE id=?", (e_t.get(), tb.get("1.0", "end-1c"), nid))

        def programar(_=None):
            if self._note_job:
                self.after_cancel(self._note_job)
            self._note_job = self.after(600, guardar)

        e_t.bind("<KeyRelease>", programar)
        tb.bind("<KeyRelease>", programar)

        def borrar():
            self.db.run("DELETE FROM notas WHERE id=?", (nid,))
            self.note_id = None
            self.refresh()

        self.btn(right, "Eliminar nota", borrar, kind="danger").pack(anchor="e", pady=(8, 0))

    def page_buscar(self, p):
        q = self.search_q.strip()
        like = f"%{q}%"
        self.title_label(p, "Resultados de búsqueda", f"“{q}”")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        found = 0

        def section(title, n):
            ctk.CTkLabel(sc, text=f"{title} ({n})", font=ctk.CTkFont(size=16, weight="bold")
                         ).pack(anchor="w", pady=(10, 4))

        def info(text):
            ctk.CTkLabel(sc, text=text, anchor="w", justify="left", fg_color=ROW, corner_radius=10,
                         wraplength=700).pack(fill="x", pady=2, ipady=6, ipadx=8)

        tareas = self.db.all("SELECT * FROM tareas WHERE titulo LIKE ? OR categoria LIKE ? ORDER BY hecha, fecha",
                             (like, like))
        if tareas:
            section("✅ Tareas", len(tareas))
            for t in tareas:
                self.task_row(sc, t)
        notas = self.db.all("SELECT * FROM notas WHERE titulo LIKE ? OR texto LIKE ?", (like, like))
        if notas:
            section("📝 Notas", len(notas))
            for n in notas:
                def go(i=n["id"]):
                    self.note_id = i
                    self.show("notas")
                self.btn(sc, f"{n['titulo'] or 'Sin título'}  —  {(n['texto'] or '')[:70].replace(chr(10), ' ')}",
                         go, kind="soft", anchor="w").pack(fill="x", pady=2)
        metas = self.db.all("SELECT * FROM metas WHERE titulo LIKE ?", (like,))
        subs = self.db.all("SELECT s.titulo, m.titulo meta FROM subtareas s JOIN metas m ON m.id=s.meta_id "
                           "WHERE s.titulo LIKE ?", (like,))
        if metas or subs:
            section("🎯 Metas", len(metas) + len(subs))
            for m in metas:
                info(f"Meta: {m['titulo']}")
            for s in subs:
                info(f"Subtarea: {s['titulo']}  (meta: {s['meta']})")
        habs = self.db.all("SELECT * FROM habitos WHERE nombre LIKE ?", (like,))
        if habs:
            section("🔥 Hábitos", len(habs))
            for h in habs:
                info(f"{h['emoji']} {h['nombre']}")
        gas = self.db.all("SELECT * FROM gastos WHERE concepto LIKE ? OR categoria LIKE ? ORDER BY fecha DESC",
                          (like, like))
        if gas:
            section("💶 Gastos", len(gas))
            for g in gas:
                info(f"{fmt_d(g['fecha'])}  {g['concepto']}  ·  {g['tipo']}  ·  {money(g['cantidad'])}")
        dia = self.db.all("SELECT * FROM animo WHERE nota LIKE ? ORDER BY fecha DESC", (like,))
        if dia:
            section("😊 Diario", len(dia))
            for d in dia:
                info(f"{fmt_d(d['fecha'])} {dict(MOODS).get(d['valor'], '')}  {d['nota']}")
        found = len(tareas) + len(notas) + len(metas) + len(subs) + len(habs) + len(gas) + len(dia)
        if not found:
            ctk.CTkLabel(sc, text="No se encontró nada 🤷", text_color=MUTED).pack(pady=30)
