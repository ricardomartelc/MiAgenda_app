"""Per-page image and colour personalization."""
import os
import shutil
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk

from src.config import ASSETS_DIR, NAV, ROW


class CustomizationPagesMixin:
    def page_fondos(self, page):
        self.title_label(
            page,
            "Fondos y colores",
            "Dale a cada sección una atmósfera propia, sin perder legibilidad.",
        )
        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 12))
        self.btn(actions, "＋  Añadir imagen", self.add_background_image, width=158).pack(side="left")
        ctk.CTkLabel(
            actions,
            text="Las imágenes se guardan en assets/backgrounds",
            text_color=("#64748b", "#94a3b8"),
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=12)

        sc = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=14)
        sc.pack(fill="both", expand=True)
        backgrounds = self.cfg.setdefault("page_backgrounds", {})
        for key, _icon, label in NAV:
            row = ctk.CTkFrame(sc, fg_color=ROW, corner_radius=18)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row,
                text=label,
                width=170,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(side="left", padx=(14, 8), pady=10)

            options = self.background_image_options(backgrounds.get(key))
            selected, image_paths = options
            menu = ctk.CTkOptionMenu(
                row,
                values=list(image_paths),
                width=210,
                height=32,
                corner_radius=9,
                fg_color=self.accent,
                button_color=self.accent,
                button_hover_color=self.hover,
                command=lambda value, page_key=key, paths=image_paths:
                    self.set_page_background_image(page_key, value, paths),
            )
            menu.set(selected)
            menu.pack(side="left", padx=4)
            self.btn(
                row,
                "Color",
                lambda page_key=key: self.choose_page_background_color(page_key),
                width=74,
                kind="soft",
            ).pack(side="left", padx=4)
            self.btn(
                row,
                "Restablecer",
                lambda page_key=key: self.reset_page_background(page_key),
                width=102,
                kind="soft",
            ).pack(side="left", padx=(4, 10))

    def background_image_options(self, current):
        current = current if isinstance(current, dict) else {}
        os.makedirs(ASSETS_DIR, exist_ok=True)
        paths = {"Sin imagen": None}
        for path in sorted(Path(ASSETS_DIR).iterdir(), key=lambda item: item.name.casefold()):
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                paths[path.name] = str(path)
        selected = "Sin imagen"
        if current and current.get("type") == "image":
            value = current.get("value", "")
            selected = next((name for name, path in paths.items() if path == value), Path(value).name)
            if selected not in paths:
                paths[selected] = value
        elif current and current.get("type") == "color":
            selected = "Color personalizado"
            paths[selected] = None
        return selected, paths

    def add_background_image(self):
        source = filedialog.askopenfilename(
            parent=self,
            title="Añadir imagen de fondo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp")],
        )
        if not source:
            return
        try:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            source_path = Path(source)
            target = Path(ASSETS_DIR) / source_path.name
            suffix = 2
            while target.exists() and target.resolve() != source_path.resolve():
                target = Path(ASSETS_DIR) / f"{source_path.stem}_{suffix}{source_path.suffix}"
                suffix += 1
            if target.resolve() != source_path.resolve():
                shutil.copy2(source_path, target)
        except OSError as error:
            messagebox.showerror("No se pudo añadir la imagen", str(error), parent=self)
            return
        self.refresh()

    def set_page_background_image(self, page_key, selected, paths):
        image_path = paths.get(selected)
        if image_path:
            self.cfg.setdefault("page_backgrounds", {})[page_key] = {
                "type": "image",
                "value": image_path,
            }
        else:
            self.cfg.setdefault("page_backgrounds", {}).pop(page_key, None)
        self.persist_config()
        self.apply_page_background(page_key)

    def choose_page_background_color(self, page_key):
        current = self.cfg.setdefault("page_backgrounds", {}).get(page_key, {})
        initial = current.get("value", "#ffffff") if current.get("type") == "color" else "#ffffff"
        _rgb, color = colorchooser.askcolor(color=initial, parent=self, title="Color de sección")
        if color:
            self.cfg["page_backgrounds"][page_key] = {"type": "color", "value": color}
            self.persist_config()
            self.apply_page_background(page_key)
            if self.current == "fondos":
                self.refresh()

    def reset_page_background(self, page_key):
        self.cfg.setdefault("page_backgrounds", {}).pop(page_key, None)
        self.persist_config()
        self.apply_page_background(page_key)
        if self.current == "fondos":
            self.refresh()
