"""Fiş Yazıcı - X5h mini termal yazıcı için modern fiş tasarlama ve yazdırma uygulaması."""
import copy
import json
import os
import queue
import time
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

import render
from printer import ENERGY, X5Printer

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_FILE = os.path.join(APP_DIR, "son_fis.json")
SETTINGS_FILE = os.path.join(APP_DIR, "ayarlar.json")

# ---------------------------------------------------------------- renkler
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
BG = ("#eef2f7", "#0f1115")
CARD = ("#ffffff", "#181b22")
SUB = ("#f3f5f9", "#22262f")
SUB_HOVER = ("#e6eaf1", "#2b303a")
BORDER = ("#e2e6ed", "#2c313b")
TEXT = ("#111827", "#e7eaf0")
MUTED = ("#6b7280", "#8f98a8")
SEL = ("#e5edff", "#1e2a44")
PREVIEW_BG = {"Light": "#e4e9f0", "Dark": "#0c0e12"}
SHADOW = {"Light": "#c4cbd6", "Dark": "#050608"}

STATE_STYLE = {
    "disconnected": ("#9ca3af", "Bağlı değil"),
    "connecting": ("#f59e0b", "Bağlanıyor"),
    "connected": ("#16a34a", "Bağlantı sağlam"),
    "weak": ("#f97316", "Yanıt yok"),
    "lost": ("#dc2626", "Bağlantı koptu"),
    "error": ("#dc2626", "Bağlanamadı"),
}
TYPE_STYLE = {
    "text": ("Aa", "#2563eb"),
    "image": ("Foto", "#9333ea"),
    "line": ("—", "#64748b"),
    "space": ("↕", "#0d9488"),
}
ALIGN_TR = {"left": "Sol", "center": "Orta", "right": "Sağ"}
ALIGN_EN = {v: k for k, v in ALIGN_TR.items()}
THEMES = {"Açık": "light", "Koyu": "dark", "Sistem": "system"}

DEFAULT_BLOCKS = [
    {"type": "text", "text": "FİŞ BAŞLIĞI", "size": 36, "align": "center", "bold": True, "font": "Arial"},
    {"type": "text", "text": "{tarih}   {saat}", "size": 20, "align": "center", "bold": False, "font": "Arial"},
    {"type": "line", "style": "dashed", "thickness": 2},
    {"type": "text", "text": "Buraya istediğiniz metni yazın.\nBirden fazla satır olabilir.",
     "size": 24, "align": "left", "bold": False, "font": "Arial"},
    {"type": "line", "style": "solid", "thickness": 2},
    {"type": "text", "text": "Teşekkürler!", "size": 28, "align": "center", "bold": True, "font": "Arial"},
]
NEW_TEXT = {"type": "text", "text": "Yeni metin", "size": 24, "align": "left", "bold": False, "font": "Arial"}
NEW_LINE = {"type": "line", "style": "solid", "thickness": 2}
NEW_SPACE = {"type": "space", "height": 24}


def describe(b):
    t = b.get("type")
    if t == "text":
        first = (b.get("text", "").strip().splitlines() or [""])[0] or "(boş metin)"
        if len(first) > 26:
            first = first[:25] + "…"
        extra = " · Kalın" if b.get("bold") else ""
        return first, f"Metin · {b.get('size', 24)} px · {ALIGN_TR.get(b.get('align'), 'Sol')}{extra}"
    if t == "image":
        name = os.path.basename(b.get("path", "")) or "(dosya yok)"
        if len(name) > 26:
            name = name[:25] + "…"
        yon = " · Yatay" if b.get("orientation") == "landscape" else ""
        return name, f"Fotoğraf · %{b.get('width', 100)} genişlik{yon}"
    if t == "line":
        return "Çizgi", ("Kesikli" if b.get("style") == "dashed" else "Düz") + f" · {b.get('thickness', 2)} px"
    if t == "space":
        return "Boşluk", f"{b.get('height', 0)} px  (~{b.get('height', 0) / 8:.0f} mm)"
    return t, ""


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.printer = X5Printer(self.q.put)
        data = load_json(LAST_FILE, None)
        self.blocks = data if isinstance(data, list) else copy.deepcopy(DEFAULT_BLOCKS)
        self.settings = load_json(SETTINGS_FILE, {})
        self.sel = None
        self.rows = []
        self._preview_job = None
        self._save_job = None
        self._pulse_job = None
        self._pulse_on = False
        self._photo = None
        self._thumb = None
        self._busy = False
        self.last_reply = None
        self.copies = 1

        F = "Segoe UI"
        self.f_title = ctk.CTkFont(F, 22, "bold")
        self.f_h2 = ctk.CTkFont(F, 15, "bold")
        self.f_body = ctk.CTkFont(F, 13)
        self.f_bold = ctk.CTkFont(F, 13, "bold")
        self.f_small = ctk.CTkFont(F, 11)
        self.f_print = ctk.CTkFont(F, 17, "bold")

        root.title("Fiş Yazıcı")
        root.geometry("1280x800")
        root.minsize(1100, 660)
        root.configure(fg_color=BG)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self.refresh_list()
        if self.blocks:
            self.select(0)
        self.schedule_preview()

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<Control-p>", lambda e: self.do_print())
        root.after(100, self._poll)
        root.after(1000, self._tick)
        if self.settings.get("auto_connect", True):
            root.after(500, self.toggle_connect)

    # ================================================================ başlık
    def card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER, **kw)

    def _build_header(self):
        h = self.card(self.root)
        h.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        h.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(h, fg_color="transparent")
        brand.grid(row=0, column=0, padx=(20, 10), pady=14, sticky="w")
        icon_png = os.path.join(APP_DIR, "icon.png")
        if os.path.exists(icon_png):
            self._logo = ctk.CTkImage(light_image=Image.open(icon_png), size=(46, 46))
            logo = ctk.CTkLabel(brand, text="", image=self._logo, width=46, height=46)
        else:
            logo = ctk.CTkLabel(brand, text="F", width=44, height=44, corner_radius=12, fg_color=ACCENT,
                                text_color="white", font=ctk.CTkFont("Segoe UI", 22, "bold"))
        logo.pack(side="left")
        tb = ctk.CTkFrame(brand, fg_color="transparent")
        tb.pack(side="left", padx=12)
        ctk.CTkLabel(tb, text="Fiş Yazıcı", font=self.f_title, text_color=TEXT, height=26).pack(anchor="w")
        ctk.CTkLabel(tb, text="X5h mini termal yazıcı", font=self.f_small, text_color=MUTED,
                     height=16).pack(anchor="w")

        # bağlantı durumu kapsülü
        pill = ctk.CTkFrame(h, fg_color=SUB, corner_radius=14)
        pill.grid(row=0, column=1, padx=10, pady=14, sticky="w")
        self.dot = ctk.CTkLabel(pill, text="●", font=ctk.CTkFont("Segoe UI", 22), text_color="#9ca3af", width=24)
        self.dot.pack(side="left", padx=(14, 6), pady=6)
        txt = ctk.CTkFrame(pill, fg_color="transparent")
        txt.pack(side="left", padx=(0, 18), pady=6)
        self.lbl_state = ctk.CTkLabel(txt, text="Bağlı değil", font=self.f_bold, text_color=TEXT, height=18)
        self.lbl_state.pack(anchor="w")
        self.lbl_detail = ctk.CTkLabel(txt, text="Yazıcıyı açıp Bağlan'a basın", font=self.f_small,
                                       text_color=MUTED, height=16)
        self.lbl_detail.pack(anchor="w")

        right = ctk.CTkFrame(h, fg_color="transparent")
        right.grid(row=0, column=2, padx=(10, 16), pady=14, sticky="e")
        files = ctk.CTkFrame(right, fg_color=SUB, corner_radius=10)
        files.pack(side="left", padx=(0, 14))
        for t, cmd in [("Yeni", self.new_receipt), ("Aç", self.open_template), ("Kaydet", self.save_template)]:
            ctk.CTkButton(files, text=t, command=cmd, width=64, height=30, fg_color="transparent",
                          hover_color=SUB_HOVER, text_color=TEXT, font=self.f_small,
                          corner_radius=8).pack(side="left", padx=2, pady=2)
        self.theme_seg = ctk.CTkSegmentedButton(right, values=list(THEMES), command=self._set_theme,
                                                font=self.f_small, height=30)
        self.theme_seg.set(self.settings.get("theme", "Sistem"))
        self.theme_seg.pack(side="left", padx=(0, 14))
        self.auto_var = tk.BooleanVar(value=self.settings.get("auto_connect", True))
        ctk.CTkSwitch(right, text="Otomatik bağlan", variable=self.auto_var, font=self.f_small,
                      command=self._save_settings, progress_color=ACCENT).pack(side="left", padx=(0, 14))
        self.btn_connect = ctk.CTkButton(right, text="Bağlan", width=170, height=42, corner_radius=12,
                                         font=self.f_bold, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                         command=self.toggle_connect)
        self.btn_connect.pack(side="left")

    # ================================================================ gövde
    def _build_body(self):
        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        self._build_list(body)
        self._build_editor(body)
        self._build_preview(body)

    def _btn(self, parent, text, cmd, width=0, **kw):
        opts = dict(fg_color=SUB, hover_color=SUB_HOVER, text_color=TEXT, corner_radius=10,
                    height=36, font=self.f_body, border_width=1, border_color=BORDER)
        opts.update(kw)
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, **opts)

    def _build_list(self, body):
        c = self.card(body, width=320)
        c.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        c.grid_propagate(False)
        c.grid_rowconfigure(1, weight=1)
        c.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(c, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(top, text="Fiş içeriği", font=self.f_h2, text_color=TEXT).pack(side="left")
        self.lbl_count = ctk.CTkLabel(top, text="", font=self.f_small, text_color=MUTED)
        self.lbl_count.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(c, fg_color="transparent", corner_radius=0)
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=8)

        tools = ctk.CTkFrame(c, fg_color="transparent")
        tools.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 4))
        for i, (t, cmd) in enumerate([("▲", lambda: self.move(-1)), ("▼", lambda: self.move(1)),
                                      ("Çoğalt", self.duplicate), ("Sil", self.delete)]):
            kw = dict(text_color=("#dc2626", "#f87171")) if t == "Sil" else {}
            self._btn(tools, t, cmd, height=32, **kw).grid(row=0, column=i, sticky="ew", padx=3)
            tools.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(c, text="EKLE", font=self.f_small, text_color=MUTED, height=14).grid(
            row=3, column=0, sticky="w", padx=20, pady=(10, 2))
        add = ctk.CTkFrame(c, fg_color="transparent")
        add.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 14))
        for i, (t, cmd, key) in enumerate([("Metin", self.add_text, "text"), ("Fotoğraf", self.add_image, "image"),
                                           ("Çizgi", self.add_line, "line"), ("Boşluk", self.add_space, "space")]):
            col = TYPE_STYLE[key][1]
            self._btn(add, "+  " + t, cmd, height=40, text_color=col, font=self.f_bold).grid(
                row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
        add.grid_columnconfigure((0, 1), weight=1)

    def _build_editor(self, body):
        c = self.card(body)
        c.grid(row=0, column=1, sticky="nsew", padx=8)
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(c, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 4))
        self.ed_badge = ctk.CTkLabel(head, text="", width=40, height=28, corner_radius=8,
                                     text_color="white", font=self.f_bold)
        self.ed_badge.pack(side="left")
        self.ed_title = ctk.CTkLabel(head, text="Düzenle", font=self.f_h2, text_color=TEXT)
        self.ed_title.pack(side="left", padx=10)
        self.editor = ctk.CTkFrame(c, fg_color="transparent")
        self.editor.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.editor.grid_columnconfigure(1, weight=1)

    def _build_preview(self, body):
        c = self.card(body, width=490)
        c.grid(row=0, column=2, sticky="ns", padx=(8, 0))
        c.grid_propagate(False)
        c.grid_columnconfigure(0, weight=1)
        c.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(c, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(top, text="Önizleme", font=self.f_h2, text_color=TEXT).pack(side="left")
        self.lbl_size = ctk.CTkLabel(top, text="", font=self.f_small, text_color=MUTED)
        self.lbl_size.pack(side="right")

        wrap = ctk.CTkFrame(c, fg_color=SUB, corner_radius=12)
        wrap.grid(row=1, column=0, sticky="nsew", padx=14)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(wrap, highlightthickness=0, bd=0, bg=self._preview_bg())
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        sb = ctk.CTkScrollbar(wrap, command=self.canvas.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units"))
        self.canvas.bind("<Configure>", lambda e: self.schedule_preview())

        ctl = ctk.CTkFrame(c, fg_color="transparent")
        ctl.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 16))
        ctl.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ctl, text="Koyuluk", font=self.f_body, text_color=MUTED).grid(row=0, column=0, sticky="w")
        self.energy_seg = ctk.CTkSegmentedButton(ctl, values=list(ENERGY), font=self.f_small, height=30,
                                                 command=lambda v: self._save_settings())
        self.energy_seg.set(self.settings.get("energy", "Normal"))
        self.energy_seg.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(12, 0))

        ctk.CTkLabel(ctl, text="Kopya", font=self.f_body, text_color=MUTED).grid(row=1, column=0, sticky="w",
                                                                                 pady=(10, 0))
        step = ctk.CTkFrame(ctl, fg_color=SUB, corner_radius=10)
        step.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(10, 0))
        ctk.CTkButton(step, text="−", width=34, height=30, fg_color="transparent", hover_color=SUB_HOVER,
                      text_color=TEXT, font=self.f_bold, command=lambda: self._copies(-1)).pack(side="left")
        self.lbl_copies = ctk.CTkLabel(step, text="1", width=34, font=self.f_bold, text_color=TEXT)
        self.lbl_copies.pack(side="left")
        ctk.CTkButton(step, text="+", width=34, height=30, fg_color="transparent", hover_color=SUB_HOVER,
                      text_color=TEXT, font=self.f_bold, command=lambda: self._copies(1)).pack(side="left")
        self._btn(ctl, "Kağıt ilerlet", self.do_feed, height=32, font=self.f_small).grid(
            row=1, column=2, sticky="e", pady=(10, 0))

        self.btn_print = ctk.CTkButton(ctl, text="Yazdır", height=54, corner_radius=14, font=self.f_print,
                                       fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self.do_print)
        self.btn_print.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(14, 8))
        self.progress = ctk.CTkProgressBar(ctl, height=6, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(ctl, text="Kısayol: Ctrl+P", font=self.f_small, text_color=MUTED, height=16).grid(
            row=4, column=0, columnspan=3, pady=(6, 0))

    # ================================================================ liste
    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows = []
        for i, b in enumerate(self.blocks):
            row = ctk.CTkFrame(self.list_frame, corner_radius=12, fg_color="transparent", border_width=1,
                               border_color=CARD, cursor="hand2")
            row.pack(fill="x", pady=2)
            txt, color = TYPE_STYLE.get(b.get("type"), ("?", "#888"))
            badge = ctk.CTkLabel(row, text=txt, width=44, height=32, corner_radius=9, fg_color=color,
                                 text_color="white", font=self.f_bold)
            badge.pack(side="left", padx=(8, 10), pady=8)
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, pady=6)
            title, sub = describe(b)
            t = ctk.CTkLabel(col, text=title, anchor="w", font=self.f_bold, text_color=TEXT, height=18)
            t.pack(fill="x")
            s = ctk.CTkLabel(col, text=sub, anchor="w", font=self.f_small, text_color=MUTED, height=15)
            s.pack(fill="x")
            for w in (row, badge, col, t, s):
                w.bind("<Button-1>", lambda e, i=i: self.select(i))
            self.rows.append((row, t, s))
        self.lbl_count.configure(text=f"{len(self.blocks)} öğe")
        self._highlight()

    def _highlight(self):
        for i, (row, _, _) in enumerate(self.rows):
            if i == self.sel:
                row.configure(fg_color=SEL, border_color=ACCENT)
            else:
                row.configure(fg_color="transparent", border_color=CARD)

    def select(self, idx):
        if not self.blocks:
            self.sel = None
        else:
            self.sel = max(0, min(idx, len(self.blocks) - 1))
        self._highlight()
        self.build_editor()

    def insert_block(self, b):
        pos = len(self.blocks) if self.sel is None else self.sel + 1
        self.blocks.insert(pos, b)
        self.sel = pos
        self.refresh_list()
        self.select(pos)
        self.changed(relist=False)

    def add_text(self):
        self.insert_block(copy.deepcopy(NEW_TEXT))

    def add_line(self):
        self.insert_block(copy.deepcopy(NEW_LINE))

    def add_space(self):
        self.insert_block(copy.deepcopy(NEW_SPACE))

    def add_image(self):
        path = self._ask_image()
        if path:
            self.insert_block({"type": "image", "path": path, "width": 100, "brightness": 1.0,
                               "contrast": 1.0, "dither": True, "align": "center", "orientation": "portrait"})

    def _ask_image(self):
        return filedialog.askopenfilename(
            title="Fotoğraf seç",
            filetypes=[("Resimler", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("Tüm dosyalar", "*.*")])

    def move(self, d):
        if self.sel is None:
            return
        j = self.sel + d
        if 0 <= j < len(self.blocks):
            self.blocks[self.sel], self.blocks[j] = self.blocks[j], self.blocks[self.sel]
            self.sel = j
            self.refresh_list()
            self.changed(relist=False)

    def duplicate(self):
        if self.sel is not None:
            self.insert_block(copy.deepcopy(self.blocks[self.sel]))

    def delete(self):
        if self.sel is None:
            return
        del self.blocks[self.sel]
        new = min(self.sel, len(self.blocks) - 1)
        self.sel = None
        self.refresh_list()
        self.select(new)
        self.changed(relist=False)

    # ================================================================ düzenleyici
    def set_prop(self, b, key, value):
        if b.get(key) != value:
            b[key] = value
            self.changed()

    def _label(self, parent, row, text):
        ctk.CTkLabel(parent, text=text, font=self.f_body, text_color=MUTED, anchor="w", width=110).grid(
            row=row, column=0, sticky="w", padx=(10, 8), pady=8)

    def _hint(self, parent, row, text):
        ctk.CTkLabel(parent, text=text, font=self.f_small, text_color=MUTED, anchor="w", justify="left",
                     wraplength=300).grid(row=row, column=1, columnspan=2, sticky="w", pady=(0, 6))

    def _segment(self, parent, row, label, values, current, on_change):
        self._label(parent, row, label)
        seg = ctk.CTkSegmentedButton(parent, values=values, command=on_change, font=self.f_body, height=32)
        seg.set(current)
        seg.grid(row=row, column=1, sticky="w")
        return seg

    def _slider(self, parent, row, label, lo, hi, value, steps, fmt, on_change):
        self._label(parent, row, label)
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=1, columnspan=2, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        val = ctk.CTkLabel(f, text=fmt(value), font=self.f_bold, text_color=TEXT, width=60, anchor="e")

        def cb(v):
            val.configure(text=fmt(v))
            on_change(v)
        s = ctk.CTkSlider(f, from_=lo, to=hi, number_of_steps=steps, command=cb, progress_color=ACCENT,
                          button_color=ACCENT, button_hover_color=ACCENT_HOVER)
        s.set(value)
        s.grid(row=0, column=0, sticky="ew")
        val.grid(row=0, column=1, padx=(10, 0))
        return s, val

    def _switch(self, parent, text, value, on_change):
        var = tk.BooleanVar(value=value)
        sw = ctk.CTkSwitch(parent, text=text, variable=var, font=self.f_body, text_color=TEXT,
                           progress_color=ACCENT, command=lambda: on_change(var.get()))
        sw._var_ref = var
        return sw

    def build_editor(self):
        for w in self.editor.winfo_children():
            w.destroy()
        self._thumb = None
        p = self.editor
        if self.sel is None:
            self.ed_badge.configure(text="", fg_color="transparent")
            self.ed_title.configure(text="Düzenle")
            ctk.CTkLabel(p, text="Fiş boş.\nSoldaki 'Ekle' bölümünden metin veya fotoğraf ekleyin.",
                         font=self.f_body, text_color=MUTED, justify="center").grid(row=0, column=0,
                                                                                  columnspan=3, pady=60)
            return
        b = self.blocks[self.sel]
        t = b["type"]
        badge, color = TYPE_STYLE[t]
        self.ed_badge.configure(text=badge, fg_color=color)
        self.ed_title.configure(text={"text": "Metin", "image": "Fotoğraf", "line": "Çizgi",
                                      "space": "Boşluk"}[t])
        getattr(self, f"_edit_{t}")(p, b)

    def _edit_text(self, p, b):
        tb = ctk.CTkTextbox(p, height=180, wrap="word", font=ctk.CTkFont("Segoe UI", 16), corner_radius=12,
                            border_width=1, border_color=BORDER, fg_color=SUB, text_color=TEXT)
        tb.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 6))
        tb.insert("1.0", b.get("text", ""))
        inner = tb._textbox
        inner.configure(undo=True)
        inner.edit_modified(False)

        def on_mod(_e):
            if inner.edit_modified():
                inner.edit_modified(False)
                self.set_prop(b, "text", tb.get("1.0", "end-1c"))
        inner.bind("<<Modified>>", on_mod)
        tb.focus_set()

        chips = ctk.CTkFrame(p, fg_color="transparent")
        chips.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 6))
        ctk.CTkLabel(chips, text="Ekle:", font=self.f_small, text_color=MUTED).pack(side="left", padx=(0, 6))
        for label, token in [("Tarih", "{tarih}"), ("Saat", "{saat}")]:
            self._btn(chips, "+ " + label, lambda tk_=token: (tb.insert("insert", tk_), tb.focus_set()),
                      height=26, font=self.f_small, corner_radius=13).pack(side="left", padx=3)
        ctk.CTkLabel(chips, text="baskı anındaki tarih/saat yazılır", font=self.f_small,
                     text_color=MUTED).pack(side="left", padx=8)

        self._label(p, 2, "Yazı tipi")
        om = ctk.CTkOptionMenu(p, values=list(render.FONTS), command=lambda v: self.set_prop(b, "font", v),
                               font=self.f_body, dropdown_font=self.f_body, width=220, height=32,
                               fg_color=SUB, button_color=SUB_HOVER, button_hover_color=BORDER,
                               text_color=TEXT, corner_radius=10)
        om.set(b.get("font", "Arial"))
        om.grid(row=2, column=1, sticky="w")

        slider, val = self._slider(p, 3, "Boyut", 10, 120, b.get("size", 24), 55, lambda v: f"{int(v)} px",
                                   lambda v: self.set_prop(b, "size", int(v)))
        pre = ctk.CTkFrame(p, fg_color="transparent")
        pre.grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 4))
        for name, size in [("Küçük", 18), ("Normal", 24), ("Büyük", 36), ("Dev", 56)]:
            def setsize(s=size):
                slider.set(s)
                val.configure(text=f"{s} px")
                self.set_prop(b, "size", s)
            self._btn(pre, name, setsize, width=58, height=28, font=self.f_small).pack(side="left", padx=(0, 5))

        self._segment(p, 5, "Hizalama", list(ALIGN_EN), ALIGN_TR.get(b.get("align", "left")),
                      lambda v: self.set_prop(b, "align", ALIGN_EN[v]))
        self._label(p, 6, "Stil")
        self._switch(p, "Kalın", b.get("bold", False), lambda v: self.set_prop(b, "bold", v)).grid(
            row=6, column=1, sticky="w")
        self._switch(p, "Ters renk (siyah zemin)", b.get("invert", False),
                     lambda v: self.set_prop(b, "invert", v)).grid(row=7, column=1, sticky="w", pady=(0, 8))

    def _edit_image(self, p, b):
        box = ctk.CTkFrame(p, fg_color=SUB, corner_radius=12)
        box.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 10))
        box.grid_columnconfigure(1, weight=1)
        thumb_lbl = ctk.CTkLabel(box, text="", width=110, height=110)
        thumb_lbl.grid(row=0, column=0, rowspan=2, padx=12, pady=12)
        name_lbl = ctk.CTkLabel(box, text="", font=self.f_bold, text_color=TEXT, anchor="w")
        name_lbl.grid(row=0, column=1, sticky="sw")
        info_lbl = ctk.CTkLabel(box, text="", font=self.f_small, text_color=MUTED, anchor="w")
        info_lbl.grid(row=1, column=1, sticky="nw")

        def show():
            path = b.get("path", "")
            name_lbl.configure(text=os.path.basename(path) or "(dosya yok)")
            try:
                im = ImageOps.exif_transpose(Image.open(path))
                info_lbl.configure(text=f"{im.width} × {im.height} px")
                if b.get("orientation") == "landscape":
                    im = im.transpose(Image.Transpose.ROTATE_90)
                im.thumbnail((110, 110))
                self._thumb = ctk.CTkImage(light_image=im.convert("RGB"), size=im.size)
                thumb_lbl.configure(image=self._thumb, text="")
            except Exception:
                info_lbl.configure(text="Dosya açılamadı")
                self._thumb = None
                thumb_lbl.configure(image=None, text="?")
        show()

        def change():
            path = self._ask_image()
            if path:
                b["path"] = path
                show()
                self.changed()
        self._btn(box, "Değiştir", change, width=100).grid(row=0, column=2, rowspan=2, padx=14)

        def set_orientation(v):
            self.set_prop(b, "orientation", "landscape" if v == "Yatay" else "portrait")
            show()
        self._segment(p, 7, "Yön", ["Dikey", "Yatay"],
                      "Yatay" if b.get("orientation") == "landscape" else "Dikey", set_orientation)
        self._hint(p, 8, "Yatay: fotoğraf 90° döndürülür ve fişe boylu boyunca basılır. "
                         "Enine geniş fotoğraflar için idealdir.")

        self._slider(p, 1, "Genişlik", 15, 100, b.get("width", 100), 85, lambda v: f"%{int(v)}",
                     lambda v: self.set_prop(b, "width", int(v)))
        self._slider(p, 2, "Parlaklık", 0.3, 2.0, b.get("brightness", 1.0), 34, lambda v: f"{v:.2f}",
                     lambda v: self.set_prop(b, "brightness", round(v, 2)))
        self._slider(p, 3, "Kontrast", 0.5, 3.0, b.get("contrast", 1.0), 50, lambda v: f"{v:.2f}",
                     lambda v: self.set_prop(b, "contrast", round(v, 2)))
        self._segment(p, 4, "Hizalama", list(ALIGN_EN), ALIGN_TR.get(b.get("align", "center")),
                      lambda v: self.set_prop(b, "align", ALIGN_EN[v]))
        self._label(p, 5, "Mod")
        self._switch(p, "Fotoğraf modu (gri tonlar noktalarla)", b.get("dither", True),
                     lambda v: self.set_prop(b, "dither", v)).grid(row=5, column=1, sticky="w")
        self._hint(p, 6, "Logo veya yazı içeren resimlerde fotoğraf modunu kapatmak daha net sonuç verir.")

    def _edit_line(self, p, b):
        self._segment(p, 0, "Çizgi tipi", ["Düz", "Kesikli"], "Kesikli" if b.get("style") == "dashed" else "Düz",
                      lambda v: self.set_prop(b, "style", "dashed" if v == "Kesikli" else "solid"))
        self._slider(p, 1, "Kalınlık", 1, 12, b.get("thickness", 2), 11, lambda v: f"{int(v)} px",
                     lambda v: self.set_prop(b, "thickness", int(v)))

    def _edit_space(self, p, b):
        self._slider(p, 0, "Yükseklik", 4, 300, b.get("height", 24), 74,
                     lambda v: f"{int(v)} px", lambda v: self.set_prop(b, "height", int(v)))
        self._hint(p, 1, "8 px ≈ 1 mm kağıt")

    # ================================================================ önizleme / kayıt
    def changed(self, relist=True):
        if relist and self.sel is not None and self.sel < len(self.rows):
            _, t, s = self.rows[self.sel]
            title, sub = describe(self.blocks[self.sel])
            t.configure(text=title)
            s.configure(text=sub)
        self.schedule_preview()
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(1000, lambda: save_json(LAST_FILE, self.blocks))

    def schedule_preview(self):
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(150, self.update_preview)

    def _preview_bg(self):
        return PREVIEW_BG[ctk.get_appearance_mode()]

    def _scale(self):
        try:
            return ctk.ScalingTracker.get_widget_scaling(self.root)
        except Exception:
            return 1.0

    def update_preview(self):
        self._preview_job = None
        img = render.render(self.blocks).convert("L")
        self.lbl_size.configure(text=f"{len(self.blocks)} öğe · ~{img.height / 8:.0f} mm")
        s = self._scale()
        if abs(s - 1) > 0.01:
            img = img.resize((round(img.width * s), max(1, round(img.height * s))), Image.Resampling.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        c = self.canvas
        mode = ctk.get_appearance_mode()
        c.configure(bg=PREVIEW_BG[mode])
        c.delete("all")
        pad = int(10 * s)
        w, h = img.width + 2 * pad, img.height + 2 * pad
        x0 = max(int(10 * s), (c.winfo_width() - w) // 2)
        y0 = int(16 * s)
        tooth = int(7 * s)

        def paper(dx, dy, fill):
            pts = [x0 + dx, y0 + dy, x0 + w + dx, y0 + dy, x0 + w + dx, y0 + h + dy]
            x = x0 + w
            down = True
            while x > x0:
                x = max(x0, x - tooth)
                pts += [x + dx, y0 + h + dy + (tooth if down else 0)]
                down = not down
            pts += [x0 + dx, y0 + h + dy]
            c.create_polygon(pts, fill=fill, outline="")
        paper(int(3 * s), int(5 * s), SHADOW[mode])
        paper(0, 0, "#ffffff")
        c.create_image(x0 + pad, y0 + pad, image=self._photo, anchor="nw")
        c.configure(scrollregion=(0, 0, x0 + w + 20, y0 + h + tooth + int(30 * s)))

    def _set_theme(self, label):
        ctk.set_appearance_mode(THEMES[label])
        self._save_settings()
        self.root.after(50, self.update_preview)

    def _copies(self, d):
        self.copies = max(1, min(20, self.copies + d))
        self.lbl_copies.configure(text=str(self.copies))

    def new_receipt(self):
        if messagebox.askyesno("Yeni fiş", "Mevcut içerik silinip örnek fiş yüklensin mi?"):
            self._load_blocks(copy.deepcopy(DEFAULT_BLOCKS))

    def _load_blocks(self, blocks):
        self.blocks = blocks
        self.sel = None
        self.refresh_list()
        self.select(0)
        self.changed(relist=False)

    def save_template(self):
        p = filedialog.asksaveasfilename(title="Şablonu kaydet", defaultextension=".json",
                                         initialdir=APP_DIR, filetypes=[("Fiş şablonu", "*.json")])
        if p:
            save_json(p, self.blocks)

    def open_template(self):
        p = filedialog.askopenfilename(title="Şablon aç", initialdir=APP_DIR, filetypes=[("Fiş şablonu", "*.json")])
        if p:
            data = load_json(p, None)
            if isinstance(data, list):
                self._load_blocks(data)
            else:
                messagebox.showerror("Hata", "Bu dosya geçerli bir fiş şablonu değil.")

    def _save_settings(self):
        self.settings.update(auto_connect=self.auto_var.get(), energy=self.energy_seg.get(),
                             theme=self.theme_seg.get())
        save_json(SETTINGS_FILE, self.settings)

    # ================================================================ yazıcı
    def toggle_connect(self):
        st = self.printer.state
        if st == "connecting":
            return
        if st in ("connected", "weak"):
            self.printer.disconnect()
        else:
            self.printer.connect()

    def _start_job(self, fut, kind):
        self._busy = True
        self.btn_print.configure(state="disabled", text="Yazdırılıyor…" if kind == "print" else "Kağıt ilerliyor…")
        self.progress.set(0)

        def done(f):
            try:
                exc = f.exception()
            except Exception as e:
                exc = e
            self.q.put(("done", kind, exc))
        fut.add_done_callback(done)

    def _require_connection(self):
        if self.printer.connected:
            return True
        if messagebox.askyesno("Yazıcı bağlı değil", "Yazıcı bağlı değil. Şimdi bağlanılsın mı?"):
            self.toggle_connect()
        return False

    def do_print(self):
        if self._busy or not self._require_connection():
            return
        rows = render.to_rows(render.render(self.blocks))   # tarih/saat baskı anında güncellenir
        energy = ENERGY.get(self.energy_seg.get(), ENERGY["Normal"])
        self._start_job(self.printer.print_rows(rows, energy, self.copies), "print")

    def do_feed(self):
        if self._busy or not self._require_connection():
            return
        self._start_job(self.printer.feed(80), "feed")

    def _pulse(self):
        if self.printer.state != "connecting":
            self._pulse_job = None
            return
        self._pulse_on = not self._pulse_on
        self.dot.configure(text_color="#f59e0b" if self._pulse_on else "#fcd34d")
        self._pulse_job = self.root.after(450, self._pulse)

    def _apply_state(self, state, msg):
        color, title = STATE_STYLE.get(state, ("#9ca3af", state))
        self.dot.configure(text_color=color)
        self.lbl_state.configure(text=title)
        if msg:
            self.lbl_detail.configure(text=msg)
        if state == "connecting":
            self.btn_connect.configure(text="Bağlanıyor…", state="disabled")
            if not self._pulse_job:
                self._pulse()
        elif state in ("connected", "weak"):
            self.btn_connect.configure(text="Bağlantıyı kes", state="normal", fg_color=SUB,
                                       hover_color=SUB_HOVER, text_color=TEXT, border_width=1,
                                       border_color=BORDER)
        else:
            self.btn_connect.configure(text="Bağlan", state="normal", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                       text_color="white", border_width=0)
            self.last_reply = None

    def _poll(self):
        try:
            while True:
                ev = self.q.get_nowait()
                kind = ev[0]
                if kind == "state":
                    self._apply_state(ev[1], ev[2])
                elif kind == "reply":
                    self.last_reply = ev[1]
                elif kind == "progress":
                    self.progress.set(ev[1])
                    if self._busy:
                        self.btn_print.configure(text=f"Yazdırılıyor…  %{int(ev[1] * 100)}")
                elif kind == "done":
                    self._busy = False
                    self.btn_print.configure(state="normal", text="Yazdır")
                    if ev[2]:
                        self.progress.set(0)
                        messagebox.showerror("İşlem başarısız", str(ev[2]))
                    elif ev[1] == "print":
                        self.progress.set(1)
                        self.btn_print.configure(text="Tamamlandı ✓", fg_color="#16a34a", hover_color="#15803d")
                        self.root.after(1800, lambda: self.btn_print.configure(
                            text="Yazdır", fg_color=ACCENT, hover_color=ACCENT_HOVER))
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _tick(self):
        if self.printer.state in ("connected", "weak") and self.last_reply:
            age = int(time.time() - self.last_reply)
            self.lbl_detail.configure(text=f"{self.printer.address}  ·  son yanıt {age} sn önce")
        self.root.after(1000, self._tick)

    def on_close(self):
        save_json(LAST_FILE, self.blocks)
        self._save_settings()
        self.printer.shutdown()
        self.root.destroy()


APP_ID = "Emir.FisYazici.1"
ICON_ICO = os.path.join(APP_DIR, "icon.ico")


def set_windows_app_id():
    """Windows'a bu pencerenin python.exe değil ayrı bir uygulama olduğunu söyler.
    Böylece görev çubuğunda Python simgesi yerine uygulamanın kendi simgesi görünür."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def main():
    set_windows_app_id()
    settings = load_json(SETTINGS_FILE, {})
    ctk.set_appearance_mode(THEMES.get(settings.get("theme", "Sistem"), "system"))
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    if os.path.exists(ICON_ICO):
        # default= ile açılan tüm alt pencereler (dosya seçme, uyarılar) de aynı simgeyi alır
        root.iconbitmap(default=ICON_ICO)
        root.iconbitmap(ICON_ICO)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
