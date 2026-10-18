"""Weekly timetable editor backed by the local SQLite database."""
from tkinter import colorchooser, messagebox

import customtkinter as ctk

from src.config import DIAS, ROW


class SchedulePagesMixin:
    def page_horario(self, page):
        self.title_label(page, "Horario semanal", "Un mapa claro para clases, trabajo y tiempo propio.")

        legend = ctk.CTkFrame(page, fg_color="transparent")
        legend.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            legend,
            text="Lunes a domingo · franjas de dos horas · selecciona un bloque para editarlo",
            text_color=("#64748b", "#94a3b8"),
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        grid = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=14)
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=0, minsize=102)
        for day_index in range(7):
            grid.grid_columnconfigure(day_index + 1, weight=1, uniform="day")
            ctk.CTkLabel(
                grid,
                text=DIAS[day_index].upper(),
                height=36,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#64748b", "#a1a1b5"),
            ).grid(row=0, column=day_index + 1, sticky="ew", padx=2, pady=(0, 4))

        all_entries = self.db.all("SELECT * FROM horario ORDER BY dia, hora")
        entries_by_slot = {}
        for row in all_entries:
            if 8 <= row["hora"] < 20:
                slot = (row["dia"], 8 + ((row["hora"] - 8) // 2) * 2)
                entries_by_slot.setdefault(slot, []).append(row)

        start_hours = range(8, 20, 2)
        for row_index, hour in enumerate(start_hours, start=1):
            time_label = f"{hour:02d}:00–{hour + 2:02d}:00"
            ctk.CTkLabel(
                grid,
                text=time_label,
                width=94,
                height=76,
                font=ctk.CTkFont(size=11),
                text_color=("#64748b", "#94a3b8"),
            ).grid(row=row_index, column=0, sticky="nsew", padx=(0, 5))
            for day in range(7):
                slot_entries = entries_by_slot.get((day, hour), [])
                cell = ctk.CTkFrame(grid, fg_color="transparent", height=72)
                cell.grid_propagate(False)
                cell.grid(row=row_index, column=day + 1, sticky="nsew", padx=2, pady=3)
                has_start_entry = any(entry["hora"] == hour for entry in slot_entries)
                compact = len(slot_entries) > 1 or not has_start_entry
                for entry in slot_entries:
                    text = entry["titulo"]
                    if entry["detalle"]:
                        text += f"\n{entry['detalle']}"
                    button = ctk.CTkButton(
                        cell,
                        text=text,
                        height=31 if compact else 72,
                        corner_radius=12,
                        fg_color=entry["color"],
                        hover_color=entry["color"],
                        text_color="white",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        command=lambda day=day, row=entry: self.edit_schedule(day, row["hora"], row),
                    )
                    button.pack(fill="x", expand=True, pady=1)
                if not slot_entries or not has_start_entry:
                    button = ctk.CTkButton(
                        cell,
                        text="＋ Añadir bloque" if slot_entries else "+",
                        height=24 if slot_entries else 72,
                        corner_radius=12,
                        fg_color=ROW,
                        hover_color=("#e6e4dc", "#35354d"),
                        text_color=("#a8a69e", "#81819a"),
                        font=ctk.CTkFont(size=14),
                        command=lambda day=day, hour=hour: self.edit_schedule(day, hour),
                    )
                    button.pack(fill="x", expand=True, pady=1)

        outside_hours = [row for row in all_entries if row["hora"] < 8 or row["hora"] >= 20]
        if outside_hours:
            ctk.CTkLabel(
                grid,
                text="Otros bloques guardados fuera del horario 08:00–20:00",
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=7, column=0, columnspan=8, sticky="ew", padx=4, pady=(14, 6))
            for index, entry in enumerate(outside_hours, start=8):
                end = min(entry["hora"] + 1, 24)
                text = (
                    f"{DIAS[entry['dia']]}  ·  {entry['hora']:02d}:00–{end:02d}:00"
                    f"     {entry['titulo']}"
                )
                if entry["detalle"]:
                    text += f"  ·  {entry['detalle']}"
                self.btn(
                    grid,
                    text,
                    lambda row=entry: self.edit_schedule(row["dia"], row["hora"], row),
                    kind="soft",
                ).grid(row=index, column=0, columnspan=8, sticky="ew", padx=3, pady=2)

    def edit_schedule(self, day, hour, entry=None):
        duration = 2 if 8 <= hour < 20 and hour % 2 == 0 else 1
        dialog = ctk.CTkToplevel(self)
        dialog.title("Editar bloque" if entry else "Nuevo bloque")
        dialog.geometry("440x350")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        self.title_label(
            body,
            f"{DIAS[day]} · {hour:02d}:00–{hour + duration:02d}:00",
            "Cada nueva asignación ocupa una franja fija de dos horas.",
        )
        title = ctk.CTkEntry(body, placeholder_text="Asignatura o actividad", height=40)
        title.pack(fill="x", pady=(8, 8))
        title.insert(0, entry["titulo"] if entry else "")
        detail = ctk.CTkEntry(body, placeholder_text="Aula o ubicación (opcional)", height=38)
        detail.pack(fill="x", pady=(0, 12))
        detail.insert(0, entry["detalle"] if entry else "")
        color = entry["color"] if entry else self.accent
        color_sample = ctk.CTkLabel(
            body,
            text=f"Color  ·  {color}",
            fg_color=color,
            text_color="white",
            corner_radius=8,
        )
        color_sample.pack(anchor="w", padx=10, pady=5)

        def choose_color():
            nonlocal color
            _rgb, selected = colorchooser.askcolor(color=color, parent=dialog, title="Color")
            if selected:
                color = selected
                color_sample.configure(text=f"Color  ·  {color}", fg_color=color)

        def save():
            name = title.get().strip()
            if not name:
                messagebox.showwarning("Horario semanal", "Escribe el nombre de la asignatura o actividad.", parent=dialog)
                title.focus_set()
                return
            self.db.run(
                "INSERT INTO horario(dia,hora,titulo,detalle,color) VALUES(?,?,?,?,?) "
                "ON CONFLICT(dia,hora) DO UPDATE SET titulo=excluded.titulo, "
                "detalle=excluded.detalle, color=excluded.color",
                (day, hour, name, detail.get().strip(), color),
            )
            dialog.destroy()
            self.refresh()

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", side="bottom", pady=(14, 0))
        if entry:
            self.btn(
                actions,
                "Eliminar",
                lambda: self.delete_schedule(day, hour, dialog),
                kind="danger",
            ).pack(side="left")
        self.btn(actions, "Cambiar color", choose_color, kind="soft").pack(side="left", padx=8)
        self.btn(actions, "Guardar", save).pack(side="right")
        title.focus_set()

    def delete_schedule(self, day, hour, dialog):
        if messagebox.askyesno("Eliminar bloque", "¿Quieres quitar esta asignación del horario?", parent=dialog):
            self.db.run("DELETE FROM horario WHERE dia=? AND hora=?", (day, hour))
            dialog.destroy()
            self.refresh()
