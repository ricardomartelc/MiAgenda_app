"""Window composition, navigation, splash transitions, and view backgrounds."""
import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageColor, ImageStat

from src.config import CARD, NAV, ROW, SURFACE, TEXT
from src.ui.blob_hero import SplashScreen
from src.utils import cover


class WindowShellMixin:
    def load_bg(self):
        path, self.bg_src = self.cfg["fondo"], None
        if path and os.path.exists(path):
            try:
                self.bg_src = Image.open(path).convert("RGB")
            except Exception:
                pass
        self.render_bg()

    def render_bg(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 50 or height < 50:
            return
        if self.bg_src is not None:
            image = cover(self.bg_src, width, height)
        else:
            image = Image.new("RGB", (width, height), SURFACE)
        self.bg_img = ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
        self.bg_label.configure(image=self.bg_img)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(150, self.render_bg)

    def fade_in(self, alpha=0.0):
        alpha += 0.07
        self.attributes("-alpha", min(alpha, 1.0))
        if alpha < 1.0:
            self.after(14, lambda: self.fade_in(alpha))

    def show_splash(self):
        if self._splash is not None:
            return
        self._splash = SplashScreen(self, self._leave_splash)
        self.deiconify()
        self.attributes("-alpha", 1.0)
        self._splash.place(x=0, y=0, relwidth=1, relheight=1)
        self._splash.lift()

    def _leave_splash(self):
        self._splash = None
        self.attributes("-alpha", 1.0)
        self.deiconify()
        self.sidebar.lift()
        self.content.lift()
        self.bg_label.lower()

    def return_to_splash(self):
        if self._splash is not None:
            return
        self.show_splash()

    def _configured_nav_order(self):
        available = {key for key, _icon, _label in NAV}
        order = ["inicio"]
        for key in self.cfg.get("nav_order", []):
            if key in available and key != "inicio" and key not in order:
                order.append(key)
        order.extend(key for key, _icon, _label in NAV if key not in order)
        return order

    def _select_nav(self, key):
        if not self._nav_drag_moved:
            self.show(key)

    def _nav_drag_start(self, key, _event):
        self._nav_drag_moved = False
        if key == "inicio":
            self._nav_drag_key = None
            return
        self.show(key)
        self._nav_drag_key = key

    def _nav_drag_motion(self, event):
        if not self._nav_drag_key:
            return
        target = min(
            (key for key in self.nav_order if key != "inicio"),
            key=lambda key: abs(
                event.y_root - (self.nav[key].winfo_rooty() + self.nav[key].winfo_height() / 2)
            ),
            default=None,
        )
        if target is None or target == self._nav_drag_key:
            return
        order = [key for key in self.nav_order if key not in ("inicio", self._nav_drag_key)]
        insertion = order.index(target)
        midpoint = self.nav[target].winfo_rooty() + self.nav[target].winfo_height() / 2
        if event.y_root > midpoint:
            insertion += 1
        order.insert(max(0, insertion), self._nav_drag_key)
        new_order = ["inicio"] + order
        if new_order != self.nav_order:
            self.nav_order = new_order
            self._nav_drag_moved = True
            self._layout_nav_buttons()

    def _nav_drag_end(self, _event):
        if self._nav_drag_key is None:
            return
        self._nav_drag_key = None
        if self._nav_drag_moved:
            self.cfg["nav_order"] = list(self.nav_order)
            self.persist_config()

    def _layout_nav_buttons(self):
        for key in self.nav_order:
            button = self.nav[key]
            button.pack_forget()
            button.pack(fill="x", padx=12, pady=2)

    def apply_page_background(self, page_key):
        page = self.pages.get(page_key)
        if page is None:
            return
        selection = self.cfg.get("page_backgrounds", {}).get(page_key, {})
        background_type = selection.get("type")
        value = selection.get("value", "")
        label = self.page_bg_labels.get(page_key)
        if background_type == "color" and value:
            page.configure(fg_color=value)
            self.page_background_luminance[page_key] = self._color_luminance(value)
            if label:
                label.place_forget()
            self.page_bg_images.pop(page_key, None)
            self.apply_page_contrast(page_key)
            return
        if background_type == "image" and value:
            if label is None:
                label = ctk.CTkLabel(page, text="", fg_color="transparent")
                label.place(x=0, y=0, relwidth=1, relheight=1)
                label.lower()
                self.page_bg_labels[page_key] = label
            else:
                label.place(x=0, y=0, relwidth=1, relheight=1)
                label.lower()
            page.configure(fg_color="transparent")
            try:
                self.page_bg_images[page_key] = Image.open(value).convert("RGB")
            except OSError as error:
                messagebox.showerror("Fondo de sección", f"No se pudo abrir la imagen:\n{error}", parent=self)
                self.cfg.get("page_backgrounds", {}).pop(page_key, None)
                self.persist_config()
                label.place_forget()
                self.page_background_luminance[page_key] = self._color_luminance(SURFACE)
                self.apply_page_contrast(page_key)
                return
            sample = ImageStat.Stat(
                self.page_bg_images[page_key].resize((32, 32), Image.Resampling.BOX)
            ).mean
            self.page_background_luminance[page_key] = self._rgb_luminance(sample)
            if page_key not in self._page_bg_bound:
                page.bind(
                    "<Configure>",
                    lambda event, key=page_key: self._resize_page_background(key, event),
                    add="+",
                )
                self._page_bg_bound.add(page_key)
            self._resize_page_background(page_key)
            self.apply_page_contrast(page_key)
            return
        page.configure(fg_color="transparent")
        self.page_background_luminance[page_key] = self._color_luminance(SURFACE)
        if label:
            label.place_forget()
        self.page_bg_images.pop(page_key, None)
        self.apply_page_contrast(page_key)

    @staticmethod
    def _rgb_luminance(rgb):
        channels = [component / 255 for component in rgb]
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    @classmethod
    def _color_luminance(cls, color):
        return cls._rgb_luminance(ImageColor.getrgb(color))

    def apply_page_contrast(self, page_key):
        page = self.pages.get(page_key)
        if page is None:
            return
        light = self.page_background_luminance.get(page_key, self._color_luminance(SURFACE)) >= 0.48
        text_color = "#1d1d1f" if light else "#f8fafc"
        surface = "#ffffff" if light else "#252a34"
        row_surface = "#f5f5f7" if light else "#303642"

        def update(widget):
            try:
                foreground = widget.cget("fg_color")
                if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                    if foreground in (CARD, "#f5f4ee", "#252a34"):
                        widget.configure(
                            fg_color=surface,
                            border_width=1,
                            border_color="#deddd5" if light else "#3a404c",
                        )
                    elif foreground in (ROW, "#e9e8e1", "#303642"):
                        widget.configure(
                            fg_color=row_surface,
                            border_width=1,
                            border_color="#e3e1d9" if light else "#3a404c",
                        )
                elif isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox)):
                    widget.configure(
                        text_color=text_color,
                        fg_color=surface if light else "#20242d",
                        border_color="#e5e5ea" if light else "#454c59",
                    )
                elif isinstance(widget, ctk.CTkCheckBox):
                    widget.configure(text_color=text_color)
                elif isinstance(widget, ctk.CTkButton):
                    if foreground in ("transparent", CARD, ROW, "#f5f4ee", "#252a34", "#e9e8e1", "#303642"):
                        widget.configure(
                            text_color=text_color,
                            fg_color=surface if foreground in (CARD, "#f5f4ee", "#252a34") else row_surface,
                        )
                elif isinstance(widget, ctk.CTkLabel):
                    if foreground in ("transparent", CARD, ROW):
                        widget.configure(text_color=text_color)
            except (AttributeError, TypeError, tk.TclError):
                pass
            for child in widget.winfo_children():
                update(child)

        update(page)

    def _resize_page_background(self, page_key, _event=None):
        image = self.page_bg_images.get(page_key)
        label = self.page_bg_labels.get(page_key)
        if image is None or label is None or not label.winfo_exists():
            return
        width, height = label.winfo_width(), label.winfo_height()
        if width < 20 or height < 20:
            return
        rendered = cover(image, width, height)
        label._background_image = ctk.CTkImage(
            light_image=rendered,
            dark_image=rendered,
            size=(width, height),
        )
        label.configure(image=label._background_image)

    def build_shell(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=232,
            corner_radius=18,
            fg_color=CARD,
            border_width=1,
            border_color=("#e2e0d7", "#3a3d48"),
        )
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(20, 10), pady=20)
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(
            self.sidebar,
            text="MI AGENDA",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w", padx=18, pady=(21, 13))
        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="🔍 Buscar…  (Ctrl+F)",
            height=34,
            corner_radius=12,
        )
        self.search_entry.pack(fill="x", padx=14, pady=(0, 10))
        self.search_entry.bind("<Return>", self.do_search)
        self.nav = {}
        nav_items = {key: (icon, label) for key, icon, label in NAV}
        for key in self.nav_order:
            icon, label = nav_items[key]
            button = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {label}",
                anchor="w",
                height=38,
                corner_radius=12,
                font=ctk.CTkFont(size=13, weight="bold" if key == "inicio" else "normal"),
                fg_color="transparent",
                text_color=TEXT,
                hover_color=("#e8e6df", "#2e2e45"),
                command=lambda selected=key: self._select_nav(selected),
            )
            button.pack(fill="x", padx=12, pady=2)
            button.bind(
                "<ButtonPress-1>",
                lambda event, selected=key: self._nav_drag_start(selected, event),
                add="+",
            )
            button.bind("<B1-Motion>", self._nav_drag_motion, add="+")
            button.bind("<ButtonRelease-1>", self._nav_drag_end, add="+")
            self.nav[key] = button
        self.btn(
            self.sidebar,
            "✦  Blob Reveal",
            self.return_to_splash,
            height=38,
            kind="soft",
        ).pack(side="bottom", fill="x", padx=12, pady=(8, 14))

        self.content = ctk.CTkFrame(
            self,
            corner_radius=18,
            fg_color=CARD,
            border_width=1,
            border_color=("#e2e0d7", "#3a3d48"),
        )
        self.content.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for key in list(self.nav) + ["buscar"]:
            page = ctk.CTkFrame(self.content, fg_color="transparent")
            page.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
            self.pages[key] = page

    def show(self, name):
        self.current = name
        self.pomo_canvas = self.pomo_btn = None
        self.load_cats()
        for key, button in self.nav.items():
            selected = key == name
            button.configure(
                fg_color=self.accent if selected else "transparent",
                text_color="white" if selected else TEXT,
            )
        page = self.pages[name]
        for widget in page.winfo_children():
            if widget is not self.page_bg_labels.get(name):
                widget.destroy()
        self.apply_page_background(name)
        getattr(self, f"page_{name}")(page)
        self.apply_page_contrast(name)
        page.tkraise()
        self.widget_refresh()
