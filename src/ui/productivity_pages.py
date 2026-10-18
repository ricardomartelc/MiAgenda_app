"""UI behavior for the corresponding Mi Agenda pages."""
import math
import time
import tkinter as tk
import customtkinter as ctk
from datetime import date, timedelta
from src.config import DIAS, MESES, MOODS, MOOD_COLORS, MUTED, ROW, TEXT
from src.utils import fmt_d, mix, parse_date, play_melody, toast


class ProductivityPagesMixin:
    def pomo_color(self):
        return {"Trabajo": self.accent, "Descanso": "#22c55e", "Largo": "#38bdf8"}[self.pomo["modo"]]

    def pomo_set_mode(self, m):
        mins = self.cfg["pomo"][m]
        self.pomo.update(modo=m, corriendo=False, total=mins * 60, restante=mins * 60)
        self.refresh()

    def pomo_toggle(self):
        P = self.pomo
        if P["corriendo"]:
            P["restante"] = max(0, P["fin"] - time.monotonic())
            P["corriendo"] = False
        else:
            if P["restante"] <= 0:
                P["restante"] = P["total"]
            P["fin"] = time.monotonic() + P["restante"]
            P["corriendo"] = True
        self.pomo_draw()

    def pomo_reset(self):
        self.pomo.update(corriendo=False, restante=self.pomo["total"])
        self.pomo_draw()

    def pomo_tick(self):
        P = self.pomo
        if P["corriendo"]:
            rem = P["fin"] - time.monotonic()
            if rem <= 0:
                self.pomo_finish()
            else:
                P["restante"] = rem
                self.pomo_draw()
        self.widget_pomo_update()

    def pomo_finish(self):
        P = self.pomo
        P.update(corriendo=False, restante=0)
        if P["modo"] == "Trabajo":
            self.db.run("INSERT INTO pomodoros(fecha,minutos) VALUES(?,?)",
                        (date.today().isoformat(), self.cfg["pomo"]["Trabajo"]))
            n = self.db.one("SELECT COUNT(*) FROM pomodoros WHERE fecha=?", (date.today().isoformat(),))
            nxt = "Largo" if n % 4 == 0 else "Descanso"
            toast("🍅 ¡Pomodoro completado!", f"Llevas {n} hoy. Toca un descanso.")
        else:
            nxt = "Trabajo"
            toast("⏰ ¡Descanso terminado!", "¿Empezamos otro pomodoro?")
        if self.cfg["sonido"]:
            play_melody("pomo")
        mins = self.cfg["pomo"][nxt]
        P.update(modo=nxt, total=mins * 60, restante=mins * 60)
        if self.current == "pomodoro":
            self.refresh()
        elif self.current == "inicio":
            self.refresh()

    def pomo_draw(self):
        P = self.pomo
        if self.pomo_btn is not None:
            try:
                self.pomo_btn.configure(text="⏸ Pausar" if P["corriendo"] else "▶ Iniciar")
            except tk.TclError:
                pass
        c = self.pomo_canvas
        if c is None:
            return
        try:
            if not c.winfo_exists():
                return
            c.delete("all")
        except tk.TclError:
            return
        size, pad, w = 300, 24, 16
        c.create_oval(pad, pad, size - pad, size - pad, outline=self.col("#e2e8f0", "#2e2e45"), width=w)
        frac = P["restante"] / P["total"] if P["total"] else 0
        if frac > 0:
            c.create_arc(pad, pad, size - pad, size - pad, start=90, extent=-359.9 * frac,
                         style="arc", outline=self.pomo_color(), width=w)
        mm, ss = divmod(int(math.ceil(P["restante"])), 60)
        c.create_text(size / 2, size / 2 - 8, text=f"{mm:02d}:{ss:02d}", font=("Segoe UI", 44, "bold"),
                      fill=self.col("#0f172a", "#f1f5f9"))
        c.create_text(size / 2, size / 2 + 44, text=P["modo"], font=("Segoe UI", 14),
                      fill=self.col("#64748b", "#94a3b8"))

    def page_pomodoro(self, p):
        self.title_label(p, "Pomodoro", "Bloques de concentración con descansos")
        P = self.pomo
        wrap = ctk.CTkFrame(p, fg_color="transparent")
        wrap.pack(expand=True)
        seg = ctk.CTkSegmentedButton(wrap, values=["Trabajo", "Descanso", "Largo"], command=self.pomo_set_mode,
                                     selected_color=self.accent, selected_hover_color=self.accent)
        seg.set(P["modo"])
        seg.pack(pady=(0, 10))
        self.pomo_canvas = tk.Canvas(wrap, width=300, height=300, highlightthickness=0,
                                     bg=self.col("#ffffff", "#1c1c2b"))
        self.pomo_canvas.pack()
        row = ctk.CTkFrame(wrap, fg_color="transparent")
        row.pack(pady=12)
        self.pomo_btn = self.btn(row, "▶ Iniciar", self.pomo_toggle, width=140)
        self.pomo_btn.pack(side="left", padx=6)
        self.btn(row, "↺ Reiniciar", self.pomo_reset, width=140, kind="soft").pack(side="left", padx=6)
        iso = date.today().isoformat()
        n = self.db.one("SELECT COUNT(*) FROM pomodoros WHERE fecha=?", (iso,))
        mins = self.db.one("SELECT SUM(minutos) FROM pomodoros WHERE fecha=?", (iso,))
        ctk.CTkLabel(wrap, text=f"🍅 {n} pomodoros hoy  ·  {mins} min de concentración",
                     font=ctk.CTkFont(size=15)).pack(pady=(0, 10))
        cfg = ctk.CTkFrame(wrap, fg_color="transparent")
        cfg.pack()
        entries = {}
        for k in ("Trabajo", "Descanso", "Largo"):
            ctk.CTkLabel(cfg, text=f"{k} (min)", text_color=MUTED).pack(side="left", padx=(8, 4))
            e = ctk.CTkEntry(cfg, width=52, height=32, justify="center")
            e.insert(0, str(self.cfg["pomo"][k]))
            e.pack(side="left")
            entries[k] = e

        def guardar():
            for k, e in entries.items():
                try:
                    self.cfg["pomo"][k] = max(1, min(180, int(e.get())))
                except ValueError:
                    pass
            self.persist_config()
            if not P["corriendo"]:
                self.pomo_set_mode(P["modo"])

        self.btn(cfg, "Guardar", guardar, width=80, height=32, kind="soft").pack(side="left", padx=12)
        self.pomo_draw()

    def habit_streaks(self, hid):
        S = {date.fromisoformat(r["fecha"]) for r in
             self.db.all("SELECT fecha FROM habito_log WHERE habito_id=?", (hid,))}
        today = date.today()
        d = today if today in S else today - timedelta(days=1)
        cur = 0
        while d in S:
            cur += 1
            d -= timedelta(days=1)
        best = run = 0
        prev = None
        for x in sorted(S):
            run = run + 1 if prev and (x - prev).days == 1 else 1
            best = max(best, run)
            prev = x
        return cur, best

    def draw_heatmap(self, parent, hid):
        weeks, cell, gap, left, top = 26, 15, 3, 22, 20
        today = date.today()
        start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
        sql = "SELECT fecha, COUNT(*) c FROM habito_log WHERE fecha>=? " + ("AND habito_id=? " if hid else "") \
              + "GROUP BY fecha"
        counts = {r["fecha"]: r["c"] for r in self.db.all(sql, (start.isoformat(),) + ((hid,) if hid else ()))}
        total = 1 if hid else max(1, self.db.one("SELECT COUNT(*) FROM habitos"))
        W, H = left + weeks * (cell + gap), top + 7 * (cell + gap)
        cv = tk.Canvas(parent, width=W, height=H, highlightthickness=0, bg=self.col("#ffffff", "#1c1c2b"))
        empty, txt = self.col("#e2e8f0", "#2a2a40"), self.col("#64748b", "#94a3b8")
        for i, l in enumerate(["L", "", "X", "", "V", "", "D"]):
            cv.create_text(8, top + i * (cell + gap) + cell / 2, text=l, fill=txt, font=("Segoe UI", 8))
        last_m = None
        for w in range(weeks):
            ws = start + timedelta(weeks=w)
            x = left + w * (cell + gap)
            if ws.month != last_m:
                cv.create_text(x, 8, text=MESES[ws.month - 1][:3], anchor="w", fill=txt, font=("Segoe UI", 8))
                last_m = ws.month
            for di in range(7):
                d = ws + timedelta(days=di)
                if d > today:
                    continue
                c = counts.get(d.isoformat(), 0)
                color = empty if c == 0 else mix(empty, self.accent, 0.3 + 0.7 * min(1, c / total))
                y = top + di * (cell + gap)
                cv.create_rectangle(x, y, x + cell, y + cell, fill=color, outline="")
        return cv

    def toggle_habit(self, hid, iso):
        if self.db.all("SELECT 1 FROM habito_log WHERE habito_id=? AND fecha=?", (hid, iso)):
            self.db.run("DELETE FROM habito_log WHERE habito_id=? AND fecha=?", (hid, iso))
        else:
            self.db.run("INSERT OR IGNORE INTO habito_log VALUES(?,?)", (hid, iso))
        self.refresh()

    def page_habitos(self, p):
        self.title_label(p, "Hábitos", "Marca cada día y construye rachas")
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", pady=(0, 8))
        e_e = ctk.CTkEntry(f, width=56, height=38, justify="center")
        e_e.insert(0, "⭐")
        e_e.pack(side="left", padx=(0, 6))
        e_n = ctk.CTkEntry(f, placeholder_text="Nuevo hábito (ej: Beber agua, Leer 20 min)…", height=38)
        e_n.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def anadir(_=None):
            if e_n.get().strip():
                self.db.run("INSERT INTO habitos(nombre,emoji) VALUES(?,?)", (e_n.get().strip(), e_e.get() or "⭐"))
                self.refresh()

        self.btn(f, "Añadir", anadir, width=90, height=38).pack(side="left")
        e_n.bind("<Return>", anadir)

        iso = date.today().isoformat()
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent", height=230)
        sc.pack(fill="x")
        habs = self.db.all("SELECT * FROM habitos ORDER BY id")
        if not habs:
            ctk.CTkLabel(sc, text="Añade tu primer hábito arriba ☝", text_color=MUTED).pack(pady=20)
        for h in habs:
            hecho = bool(self.db.all("SELECT 1 FROM habito_log WHERE habito_id=? AND fecha=?", (h["id"], iso)))
            cur, best = self.habit_streaks(h["id"])
            sel = self.hab_sel == h["id"]
            row = ctk.CTkFrame(sc, corner_radius=18, fg_color=ROW, border_width=2 if sel else 0,
                               border_color=self.accent)
            row.pack(fill="x", pady=3, padx=2)
            self.btn(row, "✔ Hecho" if hecho else "Marcar", lambda i=h["id"]: self.toggle_habit(i, iso),
                     width=90, height=32, kind="accent" if not hecho else "soft",
                     fg_color="#22c55e" if hecho else self.accent).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{h['emoji']}  {h['nombre']}", font=ctk.CTkFont(size=15)).pack(side="left")
            ctk.CTkButton(row, text="🗑", width=34, height=30, fg_color="transparent", hover_color="#ef4444",
                          text_color=TEXT, command=lambda i=h["id"]: self.del_habit(i)).pack(side="right", padx=6)
            ctk.CTkButton(row, text="📈", width=34, height=30, fg_color="transparent", hover_color=self.hover,
                          text_color=TEXT, command=lambda i=h["id"]: self.sel_habit(i)).pack(side="right")
            ctk.CTkLabel(row, text=f"🔥 {cur} días  ·  mejor {best}", text_color=MUTED).pack(side="right", padx=8)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.pack(fill="x", pady=(12, 4))
        nombre = "todos los hábitos"
        if self.hab_sel:
            r = self.db.all("SELECT nombre FROM habitos WHERE id=?", (self.hab_sel,))
            nombre = r[0]["nombre"] if r else nombre
        ctk.CTkLabel(top, text=f"Actividad (26 semanas): {nombre}",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.btn(top, "Ver todos", lambda: self.sel_habit(None), width=90, height=30, kind="soft").pack(side="right")
        self.draw_heatmap(p, self.hab_sel).pack(anchor="w")

    def sel_habit(self, i):
        self.hab_sel = i
        self.refresh()

    def del_habit(self, i):
        self.db.run("DELETE FROM habitos WHERE id=?", (i,))
        self.db.run("DELETE FROM habito_log WHERE habito_id=?", (i,))
        if self.hab_sel == i:
            self.hab_sel = None
        self.refresh()

    def page_metas(self, p):
        self.title_label(p, "Metas y objetivos", "Divide cada meta en subtareas y mira tu avance")
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", pady=(0, 8))
        e_n = ctk.CTkEntry(f, placeholder_text="Nueva meta…", height=38)
        e_n.pack(side="left", fill="x", expand=True, padx=(0, 8))
        e_f = ctk.CTkEntry(f, placeholder_text="Límite dd/mm/aaaa", width=140, height=38)
        e_f.pack(side="left", padx=(0, 8))

        def anadir(_=None):
            if not e_n.get().strip():
                return
            try:
                lim = parse_date(e_f.get()).isoformat() if e_f.get().strip() else None
            except ValueError:
                e_f.configure(border_color="#ef4444")
                return
            self.db.run("INSERT INTO metas(titulo,fecha_limite) VALUES(?,?)", (e_n.get().strip(), lim))
            self.refresh()

        self.btn(f, "Añadir meta", anadir, width=110, height=38).pack(side="left")
        e_n.bind("<Return>", anadir)

        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        metas = self.db.all("SELECT * FROM metas ORDER BY id DESC")
        if not metas:
            ctk.CTkLabel(sc, text="Aún no tienes metas 🎯", text_color=MUTED).pack(pady=20)
        for m in metas:
            subs = self.db.all("SELECT * FROM subtareas WHERE meta_id=? ORDER BY id", (m["id"],))
            hechas = sum(s["hecha"] for s in subs)
            pct = hechas / len(subs) if subs else 0
            card = ctk.CTkFrame(sc, corner_radius=18, fg_color=ROW)
            card.pack(fill="x", pady=6, padx=2)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=14, pady=(10, 4))
            ctk.CTkLabel(head, text=m["titulo"], font=ctk.CTkFont(size=17, weight="bold")).pack(side="left")
            ctk.CTkButton(head, text="🗑", width=34, height=30, fg_color="transparent", hover_color="#ef4444",
                          text_color=TEXT, command=lambda i=m["id"]: self.del_meta(i)).pack(side="right")
            ctk.CTkLabel(head, text=f"{int(pct * 100)}%", font=ctk.CTkFont(size=17, weight="bold"),
                         text_color=self.accent).pack(side="right", padx=8)
            if m["fecha_limite"]:
                dias = (date.fromisoformat(m["fecha_limite"]) - date.today()).days
                txt = f"📆 {fmt_d(m['fecha_limite'])}  ·  " + (f"{dias} días" if dias >= 0 else "vencida")
                ctk.CTkLabel(head, text=txt, text_color="#ef4444" if dias < 0 and pct < 1 else MUTED
                             ).pack(side="right", padx=8)
            bar = ctk.CTkProgressBar(card, height=10, progress_color="#22c55e" if pct >= 1 else self.accent)
            bar.pack(fill="x", padx=14, pady=(0, 6))
            bar.set(pct)
            for s in subs:
                r = ctk.CTkFrame(card, fg_color="transparent")
                r.pack(fill="x", padx=18)
                var = ctk.BooleanVar(value=bool(s["hecha"]))
                ctk.CTkCheckBox(r, text=s["titulo"], variable=var, fg_color=self.accent, hover_color=self.accent,
                                font=ctk.CTkFont(size=14, overstrike=bool(s["hecha"])),
                                command=lambda i=s["id"], v=var: self.toggle_sub(i, v.get())).pack(side="left", pady=3)
                ctk.CTkButton(r, text="✕", width=28, height=24, fg_color="transparent", hover_color="#ef4444",
                              text_color=TEXT, command=lambda i=s["id"]: self.del_sub(i)).pack(side="right")
            fr = ctk.CTkFrame(card, fg_color="transparent")
            fr.pack(fill="x", padx=14, pady=(4, 10))
            es = ctk.CTkEntry(fr, placeholder_text="＋ Añadir subtarea…", height=32)
            es.pack(side="left", fill="x", expand=True)

            def add_sub(_=None, e=es, mid=m["id"]):
                if e.get().strip():
                    self.db.run("INSERT INTO subtareas(meta_id,titulo) VALUES(?,?)", (mid, e.get().strip()))
                    self.refresh()

            es.bind("<Return>", add_sub)

    def toggle_sub(self, i, v):
        self.db.run("UPDATE subtareas SET hecha=? WHERE id=?", (int(v), i))
        self.refresh()

    def del_sub(self, i):
        self.db.run("DELETE FROM subtareas WHERE id=?", (i,))
        self.refresh()

    def del_meta(self, i):
        self.db.run("DELETE FROM subtareas WHERE meta_id=?", (i,))
        self.db.run("DELETE FROM metas WHERE id=?", (i,))
        self.refresh()

    def page_diario(self, p):
        d = self.diario_date
        iso = d.isoformat()
        self.title_label(p, "Diario de ánimo", "¿Cómo te sientes? Un emoji al día y una nota opcional")
        nav = ctk.CTkFrame(p, fg_color="transparent")
        nav.pack(fill="x")

        def mover(n):
            self.diario_date = min(date.today(), self.diario_date + timedelta(days=n))
            self.refresh()

        self.btn(nav, "◀", lambda: mover(-1), width=40).pack(side="left")
        ctk.CTkLabel(nav, text=f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} {d.year}",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=14)
        self.btn(nav, "▶", lambda: mover(1), width=40).pack(side="left")
        self.btn(nav, "Hoy", lambda: (setattr(self, "diario_date", date.today()), self.refresh()),
                 width=60, kind="soft").pack(side="left", padx=10)

        row = self.db.all("SELECT * FROM animo WHERE fecha=?", (iso,))
        cur = row[0]["valor"] if row else 0
        nota = (row[0]["nota"] or "") if row else ""
        moods = ctk.CTkFrame(p, fg_color="transparent")
        moods.pack(pady=10)
        tb = ctk.CTkTextbox(p, height=80, corner_radius=12, fg_color=ROW, font=ctk.CTkFont(size=14))

        def guardar(v=None):
            val = v if v is not None else cur
            if not val:
                return
            self.db.run("INSERT OR REPLACE INTO animo(fecha,valor,nota) VALUES(?,?,?)",
                        (iso, val, tb.get("1.0", "end-1c")))
            self.refresh()

        for v, emo in MOODS:
            ctk.CTkButton(moods, text=emo, width=64, height=64, corner_radius=18, font=ctk.CTkFont(size=30),
                          fg_color=MOOD_COLORS[v] if v == cur else ROW, hover_color=mix(MOOD_COLORS[v], "#ffffff", 0.2),
                          text_color="white", command=lambda x=v: guardar(x)).pack(side="left", padx=6)
        tb.insert("1.0", nota)
        tb.pack(fill="x")
        self.btn(p, "Guardar nota", guardar, width=130, kind="soft").pack(anchor="e", pady=6)

        # gráfica de los últimos 30 días
        datos = {r["fecha"]: r["valor"] for r in self.db.all(
            "SELECT fecha, valor FROM animo WHERE fecha>=?", ((date.today() - timedelta(days=29)).isoformat(),))}
        media = sum(datos.values()) / len(datos) if datos else 0
        ctk.CTkLabel(p, text="Últimos 30 días" + (f"   ·   media {media:.1f}/5" if datos else ""),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w")
        cv = tk.Canvas(p, height=130, highlightthickness=0, bg=self.col("#ffffff", "#1c1c2b"))
        cv.pack(fill="x", pady=(4, 6))

        def dibujar(_=None):
            cv.delete("all")
            W, H = cv.winfo_width(), 130
            if W < 60:
                return
            slot = (W - 20) / 30
            for i in range(30):
                dd = date.today() - timedelta(days=29 - i)
                v = datos.get(dd.isoformat())
                x = 10 + i * slot
                cv.create_rectangle(x + 2, 10, x + slot - 2, H - 22, fill=self.col("#f1f5f9", "#26263a"), outline="")
                if v:
                    top = (H - 22) - (H - 32) * v / 5
                    cv.create_rectangle(x + 2, top, x + slot - 2, H - 22, fill=MOOD_COLORS[v], outline="")
                if i % 5 == 0 or i == 29:
                    cv.create_text(x + slot / 2, H - 9, text=dd.strftime("%d/%m"), font=("Segoe UI", 8),
                                   fill=self.col("#64748b", "#94a3b8"))

        cv.bind("<Configure>", dibujar)

        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        for r in self.db.all("SELECT * FROM animo ORDER BY fecha DESC LIMIT 12"):
            txt = f"{dict(MOODS).get(r['valor'], '')}   {fmt_d(r['fecha'])}   {(r['nota'] or '')[:80]}"
            self.btn(sc, txt, lambda f=r["fecha"]: (setattr(self, "diario_date", date.fromisoformat(f)), self.refresh()),
                     kind="soft", anchor="w").pack(fill="x", pady=2)
