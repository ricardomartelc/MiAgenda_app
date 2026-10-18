"""Animated, in-window welcome screen with a cursor-driven reveal mask."""
import math
import random
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageTk, ImageOps
import customtkinter as ctk


PAPER = "#ffffff"


class SplashScreen(ctk.CTkFrame):
    def __init__(self, master, on_enter):
        super().__init__(master, fg_color=PAPER, corner_radius=0)
        self.master = master
        self.on_enter = on_enter
        self._animation = None
        self._fade = None
        self._pointer = None
        self._trail = []
        self._last_pointer = 0.0
        self._phase = random.random() * math.tau
        self._click_time = None
        self._photo = None
        self._image_item = None
        self._base = None
        self._texture = None
        self._text_mask = None
        self._dimensions = (0, 0)

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=PAPER, cursor="arrow")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", self._on_resize)
        self._animation = self.after(16, self._animate)

    def _font(self, size, bold=False):
        font_dir = Path("C:/Windows/Fonts")
        candidates = (
            ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf")
            if bold else ("segoeui.ttf", "arial.ttf", "calibri.ttf")
        )
        for candidate in candidates:
            try:
                return ImageFont.truetype(str(font_dir / candidate), size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    def _prepare_layers(self, width, height):
        self._dimensions = (width, height)
        base = Image.new("RGB", (width, height), PAPER)
        draw = ImageDraw.Draw(base)
        for x in range(48, width, 72):
            draw.line((x, 0, x, height), fill="#f1efe8", width=1)
        for y in range(48, height, 72):
            draw.line((0, y, width, y), fill="#f1efe8", width=1)
        draw.text(
            (52, 36),
            "MI AGENDA   /   TU ESPACIO PERSONAL",
            fill="#5e5c56",
            font=self._font(12, True),
        )
        draw.text(
            (width - 52, 37),
            datetime.now().strftime("%A  ·  %d %B").upper(),
            fill="#88857c",
            font=self._font(11, True),
            anchor="ra",
        )

        size = int(height * 0.245)
        font = self._font(size, True)
        title = "MI AGENDA"
        bounds = font.getbbox(title)
        while bounds[2] - bounds[0] > width - 100 and size > 42:
            size -= 4
            font = self._font(size, True)
            bounds = font.getbbox(title)
        title_y = int(height * 0.41)
        title_x = (width - (bounds[2] - bounds[0])) // 2 - bounds[0]
        draw.text((title_x, title_y), title, fill="#19191b", font=font)

        text_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(text_mask).text(
            (title_x, title_y),
            title,
            fill=255,
            font=font,
        )
        underline_y = int(height * 0.41 + size * 1.14)
        draw.rounded_rectangle(
            (width // 2 - 42, underline_y, width // 2 + 42, underline_y + 5),
            radius=2,
            fill="#bd604d",
        )
        draw.text(
            (width // 2, underline_y + 35),
            "UN LUGAR PARA PENSAR CON CLARIDAD",
            fill="#64615a",
            font=self._font(12, True),
            anchor="ma",
        )
        draw.text(
            (52, height - 54),
            "PLANEA     /     AVANZA     /     DISFRUTA",
            fill="#77746d",
            font=self._font(11, True),
        )
        draw.text(
            (width - 52, height - 54),
            "HAZ CLIC PARA ENTRAR  ↗",
            fill="#19191b",
            font=self._font(11, True),
            anchor="ra",
        )
        self._base = base
        self._text_mask = text_mask

        gradient = Image.linear_gradient("L").resize((width, height)).rotate(32)
        texture = ImageOps.colorize(gradient, black="#10131f", white="#30384d")
        texture = texture.crop((0, 0, width, height))
        color_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        color_draw = ImageDraw.Draw(color_layer)
        span = min(width, height)
        for x, y, radius, color in (
            (0.13, 0.27, 0.35, (105, 50, 145, 175)),
            (0.38, 0.77, 0.31, (20, 102, 115, 155)),
            (0.66, 0.28, 0.29, (130, 46, 83, 155)),
            (0.91, 0.68, 0.38, (38, 76, 121, 175)),
        ):
            r = int(span * radius)
            cx, cy = int(width * x), int(height * y)
            color_draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
        color_layer = color_layer.filter(ImageFilter.GaussianBlur(max(12, span * 0.055)))
        self._texture = Image.alpha_composite(texture.convert("RGBA"), color_layer).convert("RGB")
        texture_draw = ImageDraw.Draw(self._texture, "RGBA")
        for i in range(28):
            y = int(height * (0.12 + i * 0.03))
            texture_draw.line(
                (0, y, width, y - int(height * 0.08)),
                fill=(201, 213, 232, 15),
                width=1,
            )
        for _ in range(max(40, width // 16)):
            x, y = random.randrange(width), random.randrange(height)
            texture_draw.ellipse((x, y, x + 1, y + 1), fill=(220, 229, 242, 35))

    @staticmethod
    def _blob_points(cx, cy, width, height, phase, scale=1.0):
        radius = min(width * 0.42, height * 0.58) * scale
        points = []
        for index in range(88):
            angle = index * math.tau / 88
            wave = (
                1
                + 0.18 * math.sin(3 * angle + phase)
                + 0.12 * math.cos(5 * angle - phase * 0.73)
                + 0.075 * math.sin(7 * angle + phase * 0.41)
                + 0.035 * math.cos(9 * angle - phase * 0.29)
            )
            distance = radius * wave * (1 + 0.035 * math.sin(phase * 0.31))
            points.append((
                cx + math.cos(angle) * distance * 1.14,
                cy + math.sin(angle) * distance * 0.82,
            ))
        return points

    def _animate(self):
        self._animation = None
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 200 or height < 200:
            self._animation = self.after(16, self._animate)
            return
        if self._dimensions != (width, height):
            self._prepare_layers(width, height)
            self._pointer = (width * 0.5, height * 0.5)
            self._image_item = self.canvas.create_image(0, 0, anchor="nw")

        now = time.monotonic()
        self._phase += 0.045
        self._trail = [(point, stamp) for point, stamp in self._trail if now - stamp < 0.62]
        glow = Image.new("L", (width, height), 0)
        glow_draw = ImageDraw.Draw(glow)
        for point, stamp in self._trail:
            age = now - stamp
            strength = int(95 * max(0, 1 - age / 0.62))
            if strength:
                glow_draw.polygon(
                    self._blob_points(
                        point[0],
                        point[1],
                        width,
                        height,
                        self._phase - age * 2.7,
                        scale=max(0.18, 0.55 * (1 - age / 0.8)),
                    ),
                    fill=strength,
                )
        glow_draw.polygon(
            self._blob_points(*self._pointer, width, height, self._phase),
            fill=255,
        )
        if self._click_time is not None:
            age = now - self._click_time
            if age < 0.36:
                pulse = Image.new("L", (width, height), 0)
                ImageDraw.Draw(pulse).ellipse(
                    (
                        self._pointer[0] - age * width * 0.45,
                        self._pointer[1] - age * height * 0.45,
                        self._pointer[0] + age * width * 0.45,
                        self._pointer[1] + age * height * 0.45,
                    ),
                    outline=190,
                    width=max(2, int(6 * (1 - age / 0.36))),
                )
                glow = ImageChops.lighter(glow, pulse)
            else:
                self._click_time = None

        reveal = glow.filter(ImageFilter.GaussianBlur(max(7, min(width, height) * 0.014)))
        image = Image.composite(self._texture, self._base, reveal)
        intersected_letters = ImageChops.multiply(glow, self._text_mask)
        image.paste(self._base, (0, 0), self._text_mask)
        image.paste("#ffffff", (0, 0, width, height), intersected_letters)
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.itemconfigure(self._image_item, image=self._photo)
        self._animation = self.after(16, self._animate)

    def _on_click(self, _event):
        self._click_time = time.monotonic()
        self.after(140, self.enter)

    def _on_resize(self, _event):
        self._dimensions = (0, 0)

    def enter(self):
        if self._fade is not None:
            return
        if self._animation is not None:
            self.after_cancel(self._animation)
            self._animation = None
        self._fade_step(1.0)

    def _fade_step(self, opacity):
        opacity -= 0.2
        if opacity <= 0:
            self.destroy()
            self.on_enter()
            return
        try:
            self.master.attributes("-alpha", opacity)
        except tk.TclError:
            self.destroy()
            self.on_enter()
            return
        self._fade = self.after(18, lambda: self._fade_step(opacity))
