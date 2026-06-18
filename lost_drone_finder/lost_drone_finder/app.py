import math
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from battery import estimate_fpv_from_voltage, find_normal_drone
from geo import format_decimal, parse_decimal_degrees, parse_dms
from physics import calculate_zone
from weather import WeatherError, fetch_elevation, fetch_weather


BG = "#050816"
PANEL = "#0b1224"
INK = "#e6f7ff"
MUTED = "#8aa4b8"
BLUE = "#22d3ee"
DARK_BLUE = "#38bdf8"
GREEN = "#39ff88"
ORANGE = "#f59e0b"
SOFT = "#101a33"
FIELD = "#07111f"
LINE = "#1f3b5b"


class LostDroneFinder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Система за търсене на изгубен дрон")
        self.geometry("1100x780")
        self.minsize(980, 720)
        self.configure(bg=BG)

        self.coord_mode = tk.StringVar(value="decimal")
        self.weather_mode = tk.StringVar(value="auto")
        self.loss_mode = tk.StringVar(value="signal")
        self.speed_unit = tk.StringVar(value="m/s")
        self.drone_type = tk.StringVar(value="fpv")
        self.fpv_mode = tk.StringVar(value="landing")
        self.fpv_battery_mode = tk.StringVar(value="auto")
        self.normal_battery_mode = tk.StringVar(value="auto")
        self.manual_time_unit = tk.StringVar(value="sec")
        self.current_step = 0
        self.latest_result = None
        self.last_battery_note = ""

        self._style()
        self._build_ui()
        self._show_step(0)
        self._toggle_coordinate_mode()
        self._toggle_weather_mode()
        self._toggle_drone_type()
        self._update_direction_arrow()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 12), background=BG, foreground=INK)
        style.configure("Shell.TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Card.TLabelframe", background=PANEL, bordercolor=LINE, relief="solid")
        style.configure("Card.TLabelframe.Label", background=PANEL, foreground=BLUE, font=("Segoe UI", 12, "bold"))
        style.configure("TLabel", background=PANEL, foreground=INK)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 12))
        style.configure("Hero.TLabel", background=BG, foreground="#dffaff", font=("Segoe UI", 28, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground="#7dd3fc", font=("Segoe UI", 13))
        style.configure("Accent.TButton", background="#0891b2", foreground="#ecfeff", padding=(22, 12), borderwidth=0, font=("Segoe UI", 12, "bold"))
        style.map("Accent.TButton", background=[("active", "#06b6d4"), ("disabled", "#164e63")])
        style.configure("Green.TButton", background="#00b86b", foreground="#ecfdf5", padding=(22, 12), borderwidth=0, font=("Segoe UI", 12, "bold"))
        style.map("Green.TButton", background=[("active", "#22c55e")])
        style.configure("Ghost.TButton", background="#15233b", foreground="#dffaff", padding=(20, 12), borderwidth=0, font=("Segoe UI", 12, "bold"))
        style.map("Ghost.TButton", background=[("active", "#1e3a5f")])
        style.configure("TRadiobutton", background=PANEL, foreground=INK, font=("Segoe UI", 12))
        style.map("TRadiobutton", background=[("active", PANEL)], foreground=[("active", BLUE)])
        style.configure("TCombobox", fieldbackground=FIELD, background=SOFT, foreground=INK, arrowcolor=BLUE, font=("Segoe UI", 12))
        style.configure("TEntry", fieldbackground=FIELD, foreground=INK, insertcolor=BLUE, bordercolor=LINE, lightcolor=BLUE, darkcolor=LINE, font=("Segoe UI", 12))

    def _build_ui(self):
        shell = ttk.Frame(self, style="Shell.TFrame", padding=14)
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(1, weight=1)
        shell.columnconfigure(0, weight=1)

        header = ttk.Frame(shell, style="Shell.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hud = tk.Canvas(header, width=230, height=64, bg=BG, highlightthickness=0)
        hud.pack(side="right", padx=(12, 0))
        self._draw_header_hud(hud)
        ttk.Label(header, text="Система за търсене на изгубен дрон", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(header, text="FPV батерия по клетки и волтаж, нормален дрон по модел или ръчно време.", style="Sub.TLabel").pack(anchor="w")

        body = ttk.Frame(shell, style="Shell.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=6)
        body.columnconfigure(1, weight=5)
        body.rowconfigure(0, weight=1)

        self.left = ttk.Frame(body, style="Panel.TFrame", padding=16)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left.rowconfigure(1, weight=1)
        self.left.columnconfigure(0, weight=1)

        right = ttk.Frame(body, style="Panel.TFrame", padding=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.step_title = ttk.Label(self.left, text="", font=("Segoe UI", 20, "bold"), background=PANEL)
        self.step_title.grid(row=0, column=0, sticky="ew")

        self.step_container = ttk.Frame(self.left, style="Panel.TFrame")
        self.step_container.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.step_container.rowconfigure(0, weight=1)
        self.step_container.columnconfigure(0, weight=1)

        self.step_one = ttk.Frame(self.step_container, style="Panel.TFrame")
        self.step_two = ttk.Frame(self.step_container, style="Panel.TFrame")
        for frame in (self.step_one, self.step_two):
            frame.grid(row=0, column=0, sticky="nsew")

        self._step_one_content(self.step_one)
        self._step_two_content(self.step_two)

        nav = ttk.Frame(self.left, style="Panel.TFrame")
        nav.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.back_btn = ttk.Button(nav, text="Назад", style="Ghost.TButton", command=self.back_step)
        self.back_btn.pack(side="left")
        self.calc_btn = ttk.Button(nav, text="Изчисли зона", style="Green.TButton", command=self.calculate)
        self.calc_btn.pack(side="right")
        self.next_btn = ttk.Button(nav, text="Напред", style="Accent.TButton", command=self.next_step)
        self.next_btn.pack(side="right", padx=(0, 8))

        ttk.Label(right, text="Резултат", font=("Segoe UI", 20, "bold"), background=PANEL).grid(row=0, column=0, sticky="w")
        self.output = tk.Text(right, wrap="word", font=("Consolas", 12), bg="#020617", fg="#b7f7ff", insertbackground=BLUE, relief="flat", padx=18, pady=18)
        self.output.grid(row=1, column=0, sticky="nsew", pady=(12, 10))
        ttk.Button(right, text="Отвори в Google Maps", style="Ghost.TButton", command=self.open_maps).grid(row=2, column=0, sticky="ew")

    def _draw_header_hud(self, canvas):
        canvas.create_rectangle(8, 10, 222, 54, outline=LINE, width=2)
        canvas.create_line(18, 42, 62, 42, fill=BLUE, width=2)
        canvas.create_line(62, 42, 82, 26, fill=BLUE, width=2)
        canvas.create_line(82, 26, 112, 26, fill=GREEN, width=2)
        canvas.create_line(112, 26, 134, 36, fill=GREEN, width=2)
        canvas.create_line(134, 36, 188, 36, fill=BLUE, width=2)
        canvas.create_oval(176, 18, 208, 50, outline=GREEN, width=2)
        canvas.create_oval(186, 28, 198, 40, outline=BLUE, width=2)
        canvas.create_text(24, 22, text="GPS", fill=GREEN, anchor="w", font=("Consolas", 9, "bold"))
        canvas.create_text(116, 48, text="SEARCH GRID", fill="#7dd3fc", anchor="center", font=("Consolas", 8))

    def _add_scan_panel(self, parent, title):
        canvas = tk.Canvas(parent, bg=PANEL, highlightthickness=0, height=240)
        canvas.pack(fill="both", expand=True, pady=(14, 0))

        def draw(event=None):
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            canvas.delete("all")
            if width < 20 or height < 20:
                return
            canvas.create_rectangle(4, 4, width - 4, height - 4, outline=LINE, width=2)
            for x in range(24, width, 48):
                canvas.create_line(x, 12, x, height - 12, fill="#0f2742")
            for y in range(24, height, 48):
                canvas.create_line(12, y, width - 12, y, fill="#0f2742")
            canvas.create_text(24, 24, text=title.upper(), fill=BLUE, anchor="w", font=("Consolas", 14, "bold"))
            cx, cy = width // 2, height // 2 + 12
            radius = max(44, min(width, height) // 5)
            canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=GREEN, width=2)
            canvas.create_oval(cx - radius // 2, cy - radius // 2, cx + radius // 2, cy + radius // 2, outline="#155e75", width=2)
            canvas.create_line(cx - radius - 22, cy, cx + radius + 22, cy, fill=BLUE, width=2)
            canvas.create_line(cx, cy - radius - 22, cx, cy + radius + 22, fill=BLUE, width=2)
            canvas.create_line(cx, cy, cx + radius, cy - radius // 2, fill=GREEN, width=4, arrow=tk.LAST)
            canvas.create_text(cx, cy + radius + 32, text="LIVE SEARCH ESTIMATION", fill=MUTED, font=("Consolas", 12))

        canvas.bind("<Configure>", draw)
        return canvas

    def _step_one_content(self, parent):
        self._coordinate_section(parent)
        scenario = ttk.LabelFrame(parent, text="Тип и причина", style="Card.TLabelframe", padding=12)
        scenario.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Label(scenario, text="Какъв е дронът?", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        type_row = ttk.Frame(scenario, style="Panel.TFrame")
        type_row.pack(fill="x", pady=(4, 10))
        ttk.Radiobutton(type_row, text="FPV", variable=self.drone_type, value="fpv", command=self._toggle_drone_type).pack(side="left")
        ttk.Radiobutton(type_row, text="Нормален дрон", variable=self.drone_type, value="normal", command=self._toggle_drone_type).pack(side="left", padx=14)

        ttk.Label(scenario, text="Как е изгубен?", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Radiobutton(scenario, text="Изгубен сигнал", variable=self.loss_mode, value="signal").pack(anchor="w", pady=2)
        ttk.Radiobutton(scenario, text="Блъснал се е някъде", variable=self.loss_mode, value="crash").pack(anchor="w", pady=2)

        self.fpv_box = ttk.LabelFrame(scenario, text="FPV поведение", style="Card.TLabelframe", padding=10)
        ttk.Radiobutton(self.fpv_box, text="Падане", variable=self.fpv_mode, value="fall").pack(anchor="w", pady=2)
        ttk.Radiobutton(self.fpv_box, text="Бавно кацане", variable=self.fpv_mode, value="landing").pack(anchor="w", pady=2)

        self.type_hint = ttk.Label(scenario, text="", style="Muted.TLabel", wraplength=560)
        self.type_hint.pack(anchor="w", fill="x", pady=(12, 0))
        self._add_scan_panel(scenario, "Drone Signal Map")

    def _step_two_content(self, parent):
        flight = ttk.LabelFrame(parent, text="Полет", style="Card.TLabelframe", padding=12)
        flight.pack(fill="x")

        row = ttk.Frame(flight, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Скорост на дрона", width=25).pack(side="left")
        self.speed_entry = ttk.Entry(row)
        self.speed_entry.insert(0, "8")
        self.speed_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Combobox(row, textvariable=self.speed_unit, values=("m/s", "km/h", "mph"), state="readonly", width=8).pack(side="left")

        direction_card = ttk.Frame(flight, style="Panel.TFrame")
        direction_card.pack(fill="x", pady=(8, 4))
        ttk.Label(direction_card, text="Посока на движение (0° = север, 90° = изток, 180° = юг, 270° = запад)", foreground=BLUE).pack(anchor="w")
        direction_row = ttk.Frame(direction_card, style="Panel.TFrame")
        direction_row.pack(fill="x", pady=(5, 0))
        self.direction_entry = ttk.Entry(direction_row, width=12)
        self.direction_entry.insert(0, "90")
        self.direction_entry.pack(side="left")
        self.direction_entry.bind("<KeyRelease>", lambda _event: self._update_direction_arrow())
        self.direction_canvas = tk.Canvas(direction_row, width=132, height=132, bg=PANEL, highlightthickness=0)
        self.direction_canvas.pack(side="left", padx=18)
        self.direction_text = ttk.Label(direction_row, text="", font=("Segoe UI", 11, "bold"), background=PANEL)
        self.direction_text.pack(side="left")

        self.weight_entry = self._entry_row(flight, "Тегло на дрона (грама)", "249")
        self.height_entry = self._entry_row(flight, "Височина над терена (m)", "60")
        self.elapsed_entry = self._entry_row(flight, "Минало време след загуба (секунди)", "60")

        self.battery_box = ttk.LabelFrame(parent, text="Батерия и модел", style="Card.TLabelframe", padding=12)
        self.battery_box.pack(fill="x", pady=(12, 0))
        self.fpv_battery_frame = ttk.Frame(self.battery_box, style="Panel.TFrame")
        fpv_mode_row = ttk.Frame(self.fpv_battery_frame, style="Panel.TFrame")
        fpv_mode_row.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(fpv_mode_row, text="Сметни по батерия", variable=self.fpv_battery_mode, value="auto", command=self._toggle_drone_type).pack(side="left")
        ttk.Radiobutton(fpv_mode_row, text="Ръчно оставащо време", variable=self.fpv_battery_mode, value="manual", command=self._toggle_drone_type).pack(side="left", padx=12)
        self.fpv_cells_entry = self._entry_row(self.fpv_battery_frame, "FPV батерия (брой клетки)", "4")
        self.fpv_voltage_entry = self._entry_row(self.fpv_battery_frame, "FPV батерия (волта)", "15.2")
        self.fpv_inches_entry = self._entry_row(self.fpv_battery_frame, "Размер на FPV дрона (инчове)", "5")

        self.normal_battery_frame = ttk.Frame(self.battery_box, style="Panel.TFrame")
        normal_mode_row = ttk.Frame(self.normal_battery_frame, style="Panel.TFrame")
        normal_mode_row.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(normal_mode_row, text="Сметни по модел и %", variable=self.normal_battery_mode, value="auto", command=self._toggle_drone_type).pack(side="left")
        ttk.Radiobutton(normal_mode_row, text="Ръчно оставащо време", variable=self.normal_battery_mode, value="manual", command=self._toggle_drone_type).pack(side="left", padx=12)
        self.normal_model_entry = self._entry_row(self.normal_battery_frame, "Близко име на модел", "Mini 4")
        self.normal_percent_entry = self._entry_row(self.normal_battery_frame, "Оставаща батерия (%)", "35")
        self.manual_time_frame = ttk.Frame(self.battery_box, style="Panel.TFrame")
        manual_row = ttk.Frame(self.manual_time_frame, style="Panel.TFrame")
        manual_row.pack(fill="x", pady=4)
        ttk.Label(manual_row, text="Ръчно оставащо време", width=31).pack(side="left")
        self.manual_time_entry = ttk.Entry(manual_row)
        self.manual_time_entry.insert(0, "60")
        self.manual_time_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Combobox(manual_row, textvariable=self.manual_time_unit, values=("sec", "min"), state="readonly", width=7).pack(side="left")

        self._weather_section(parent)

    def _coordinate_section(self, parent):
        box = ttk.LabelFrame(parent, text="Последна позиция", style="Card.TLabelframe", padding=12)
        box.pack(fill="x")
        mode_row = ttk.Frame(box, style="Panel.TFrame")
        mode_row.pack(fill="x", pady=(0, 8))
        ttk.Radiobutton(mode_row, text="Десетични координати (7 знака)", variable=self.coord_mode, value="decimal", command=self._toggle_coordinate_mode).pack(side="left")
        ttk.Radiobutton(mode_row, text="Градуси/минути/секунди", variable=self.coord_mode, value="dms", command=self._toggle_coordinate_mode).pack(side="left", padx=10)
        self.decimal_frame = ttk.Frame(box, style="Panel.TFrame")
        self.lat_entry = self._entry_row(self.decimal_frame, "Ширина lat", "42.6977000")
        self.lon_entry = self._entry_row(self.decimal_frame, "Дължина lon", "23.3219000")
        self.dms_frame = ttk.Frame(box, style="Panel.TFrame")
        self.lat_dms = self._dms_row(self.dms_frame, "Ширина", ("42", "41", "51.72"), ("N", "S"))
        self.lon_dms = self._dms_row(self.dms_frame, "Дължина", ("23", "19", "18.84"), ("E", "W"))

    def _weather_section(self, parent):
        box = ttk.LabelFrame(parent, text="Земни и метео данни", style="Card.TLabelframe", padding=12)
        box.pack(fill="both", expand=True, pady=(12, 0))
        mode_row = ttk.Frame(box, style="Panel.TFrame")
        mode_row.pack(fill="x", pady=(0, 8))
        ttk.Radiobutton(mode_row, text="Автоматично от Open-Meteo", variable=self.weather_mode, value="auto", command=self._toggle_weather_mode).pack(side="left")
        ttk.Radiobutton(mode_row, text="Ръчно", variable=self.weather_mode, value="manual", command=self._toggle_weather_mode).pack(side="left", padx=10)
        self.wind_speed_entry = self._entry_row(box, "Вятър скорост (m/s)", "3")
        self.wind_from_entry = self._entry_row(box, "Вятър от посока (0°=N, 90°=E)", "270")
        self.gust_entry = self._entry_row(box, "Пориви (m/s)", "5")
        self._add_scan_panel(box, "Wind Drift Projection")

    def _entry_row(self, parent, label, default):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=34, font=("Segoe UI", 12)).pack(side="left")
        entry = ttk.Entry(row)
        entry.insert(0, default)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _dms_row(self, parent, label, defaults, hemispheres):
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=12, font=("Segoe UI", 12)).pack(side="left")
        deg = ttk.Entry(row, width=7)
        minute = ttk.Entry(row, width=7)
        sec = ttk.Entry(row, width=9)
        hemi = ttk.Combobox(row, width=4, values=hemispheres, state="readonly")
        for widget, value in ((deg, defaults[0]), (minute, defaults[1]), (sec, defaults[2])):
            widget.insert(0, value)
            widget.pack(side="left", padx=(0, 5))
        hemi.set(hemispheres[0])
        hemi.pack(side="left")
        ttk.Label(row, text="град.  мин.  сек.").pack(side="left", padx=8)
        return deg, minute, sec, hemi

    def _show_step(self, index):
        self.current_step = index
        if index == 0:
            self.step_title.configure(text="1. Позиция, тип и причина")
            self.step_one.tkraise()
            self.back_btn.configure(state="disabled")
            self.next_btn.configure(state="normal")
        else:
            self.step_title.configure(text="2. Полет, батерия и условия")
            self.step_two.tkraise()
            self.back_btn.configure(state="normal")
            self.next_btn.configure(state="disabled")

    def next_step(self):
        self._show_step(1)

    def back_step(self):
        self._show_step(0)

    def _toggle_coordinate_mode(self):
        if self.coord_mode.get() == "decimal":
            self.dms_frame.pack_forget()
            self.decimal_frame.pack(fill="x")
        else:
            self.decimal_frame.pack_forget()
            self.dms_frame.pack(fill="x")

    def _toggle_weather_mode(self):
        state = "disabled" if self.weather_mode.get() == "auto" else "normal"
        for entry in (self.wind_speed_entry, self.wind_from_entry, self.gust_entry):
            entry.configure(state=state)

    def _toggle_drone_type(self):
        if self.drone_type.get() == "fpv":
            self.fpv_box.pack(fill="x", pady=(12, 0), before=self.type_hint)
            self.type_hint.configure(text="FPV дронът каца бавно и не спира като GPS дрон. Докато каца, вятърът леко го носи.")
            self.normal_battery_frame.pack_forget()
            self.fpv_battery_frame.pack(fill="x")
            self._toggle_fpv_battery_fields()
        else:
            self.fpv_box.pack_forget()
            self.type_hint.configure(text="Нормален дрон може да задържа позиция. При силен вятър моделът смята дрейф от мястото на изгубения сигнал.")
            self.fpv_battery_frame.pack_forget()
            self.normal_battery_frame.pack(fill="x")
            self._toggle_normal_battery_fields()

    def _set_entries_state(self, entries, state):
        for entry in entries:
            entry.configure(state=state)

    def _toggle_fpv_battery_fields(self):
        manual = self.fpv_battery_mode.get() == "manual"
        self._set_entries_state(
            (self.fpv_cells_entry, self.fpv_voltage_entry, self.fpv_inches_entry),
            "disabled" if manual else "normal",
        )
        if manual:
            self.manual_time_frame.pack(fill="x", pady=(8, 0))
        else:
            self.manual_time_frame.pack_forget()

    def _toggle_normal_battery_fields(self):
        manual = self.normal_battery_mode.get() == "manual"
        self._set_entries_state(
            (self.normal_model_entry, self.normal_percent_entry),
            "disabled" if manual else "normal",
        )
        if manual:
            self.manual_time_frame.pack(fill="x", pady=(8, 0))
        else:
            self.manual_time_frame.pack_forget()

    def _read_float(self, entry, name):
        try:
            return float(entry.get().strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Невалидна стойност за {name}.") from exc

    def _read_coordinates(self):
        if self.coord_mode.get() == "decimal":
            return parse_decimal_degrees(self.lat_entry.get(), self.lon_entry.get())
        lat = parse_dms(*[x.get() for x in self.lat_dms], name="ширина")
        lon = parse_dms(*[x.get() for x in self.lon_dms], name="дължина")
        return lat, lon

    def _speed_to_ms(self, value):
        if self.speed_unit.get() == "km/h":
            return value / 3.6
        if self.speed_unit.get() == "mph":
            return value * 0.44704
        return value

    def _estimate_battery_and_weight(self):
        typed_weight_g = self._read_float(self.weight_entry, "тегло")
        if (
            self.drone_type.get() == "fpv"
            and self.fpv_battery_mode.get() == "manual"
            or self.drone_type.get() == "normal"
            and self.normal_battery_mode.get() == "manual"
        ):
            value = self._read_float(self.manual_time_entry, "ръчно оставащо време")
            remaining = value / 60 if self.manual_time_unit.get() == "sec" else value
            if remaining < 0:
                raise ValueError("Ръчното оставащо време не може да е отрицателно.")
            self.last_battery_note = f"Оставащо време: ръчно въведени {value:g} {self.manual_time_unit.get()}."
            if self.drone_type.get() == "normal":
                model = find_normal_drone(self.normal_model_entry.get())
                wind_limit = model["wind_limit_ms"] if model else 8.0
                weight_g = model["weight_g"] if model and typed_weight_g <= 0 else typed_weight_g
                return remaining, weight_g, wind_limit
            return remaining, typed_weight_g, None

        if self.drone_type.get() == "fpv":
            cells = round(self._read_float(self.fpv_cells_entry, "брой клетки"))
            voltage = self._read_float(self.fpv_voltage_entry, "волтаж")
            inches = self._read_float(self.fpv_inches_entry, "инчове")
            estimate = estimate_fpv_from_voltage(voltage, inches, cells)
            weight_g = typed_weight_g if typed_weight_g > 0 else estimate["estimated_weight_g"]
            self.last_battery_note = (
                f"FPV батерия: {voltage:.2f} V, {estimate['cells']}S, "
                f"{estimate['per_cell']:.2f} V/клетка, {estimate['percent']:.0f}%."
            )
            return estimate["remaining_minutes"], weight_g, None

        model = find_normal_drone(self.normal_model_entry.get())
        if not model:
            raise ValueError("Не разпознах модела. Пробвай например Mini 4, Air 3 или Mavic 3.")
        percent = self._read_float(self.normal_percent_entry, "оставаща батерия в проценти")
        if percent < 0 or percent > 100:
            raise ValueError("Оставащата батерия трябва да е между 0 и 100%.")
        remaining = model["max_minutes"] * (percent / 100)
        self.last_battery_note = f"Разпознат модел: {model['name']}. Батерия: {percent:.0f}% от около {model['max_minutes']} min."
        return remaining, model["weight_g"], model["wind_limit_ms"]

    def _update_direction_arrow(self):
        try:
            direction = float(self.direction_entry.get().strip().replace(",", ".")) % 360
        except ValueError:
            direction = 0.0
        c = self.direction_canvas
        c.delete("all")
        cx, cy, r = 66, 66, 46
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=LINE, width=2, fill="#07111f")
        c.create_oval(cx - 30, cy - 30, cx + 30, cy + 30, outline="#12314f", width=1)
        c.create_line(cx - r, cy, cx + r, cy, fill="#12314f")
        c.create_line(cx, cy - r, cx, cy + r, fill="#12314f")
        c.create_text(cx, cy - r - 10, text="N", fill=BLUE, font=("Segoe UI", 9, "bold"))
        c.create_text(cx + r + 10, cy, text="E", fill=BLUE, font=("Segoe UI", 9, "bold"))
        c.create_text(cx, cy + r + 10, text="S", fill=BLUE, font=("Segoe UI", 9, "bold"))
        c.create_text(cx - r - 10, cy, text="W", fill=BLUE, font=("Segoe UI", 9, "bold"))
        angle = math.radians(direction - 90)
        end_x = cx + math.cos(angle) * 38
        end_y = cy + math.sin(angle) * 38
        c.create_line(cx, cy, end_x, end_y, fill=GREEN, width=5, arrow=tk.LAST, arrowshape=(16, 20, 7))
        c.create_line(cx, cy, end_x, end_y, fill="#bbf7d0", width=2, arrow=tk.LAST, arrowshape=(12, 16, 5))
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=GREEN, outline="")
        self.direction_text.configure(text=f"{direction:.0f}°")

    def calculate(self):
        try:
            self._update_direction_arrow()
            lat, lon = self._read_coordinates()
            speed_value = self._read_float(self.speed_entry, "скорост")
            speed = self._speed_to_ms(speed_value)
            direction = self._read_float(self.direction_entry, "посока") % 360
            remaining_min, weight_g, wind_limit = self._estimate_battery_and_weight()
            height = self._read_float(self.height_entry, "височина")
            elapsed_s = self._read_float(self.elapsed_entry, "минало време")

            elevation_text = "няма данни"
            source = "ръчно въведени данни"
            if self.weather_mode.get() == "auto":
                weather = fetch_weather(lat, lon)
                wind_speed = weather["wind_speed_ms"]
                wind_from = weather["wind_from_deg"]
                gust = weather["wind_gust_ms"]
                source = f"Open-Meteo, време: {weather['time']}"
                try:
                    elevation_text = f"{fetch_elevation(lat, lon):.1f} m"
                except WeatherError:
                    elevation_text = "няма данни"
            else:
                wind_speed = self._read_float(self.wind_speed_entry, "скорост на вятъра")
                wind_from = self._read_float(self.wind_from_entry, "посока на вятъра") % 360
                gust = self._read_float(self.gust_entry, "пориви")

            result = calculate_zone(
                lat, lon, speed, direction, remaining_min, weight_g / 1000, height,
                wind_from, wind_speed, gust,
                loss_mode=self.loss_mode.get(),
                drone_type=self.drone_type.get(),
                fpv_mode=self.fpv_mode.get(),
                elapsed_since_loss_s=elapsed_s,
                normal_wind_limit_ms=wind_limit or 8.0,
            )
            self.latest_result = result
            self._show_result(lat, lon, elevation_text, source, wind_speed, wind_from, gust, speed_value, weight_g, result)
        except (ValueError, WeatherError) as exc:
            messagebox.showerror("Грешка", str(exc))

    def _show_result(self, lat, lon, elevation_text, source, wind_speed, wind_from, gust, speed_value, weight_g, result):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        scenario = "изгубен сигнал" if self.loss_mode.get() == "signal" else "сблъсък"
        drone = "FPV" if self.drone_type.get() == "fpv" else "нормален дрон"
        fpv_text = "падане" if self.fpv_mode.get() == "fall" else "бавно кацане"
        lines = [
            "ВХОД",
            f"Последна позиция: {format_decimal(lat)}, {format_decimal(lon)}",
            f"Тип дрон: {drone}" + (f" ({fpv_text})" if self.drone_type.get() == "fpv" else ""),
            f"Сценарий: {scenario}",
            f"Тегло за модела: {weight_g:.0f} g",
            f"Скорост: {speed_value:.2f} {self.speed_unit.get()} ({result['input_speed_ms']:.2f} m/s)",
            f"Минало време след загуба: {result['elapsed_since_loss_s']:.0f} s",
            f"Оценена оставаща батерия: {result['remaining_battery_min']:.1f} min",
            self.last_battery_note,
            f"Надморска височина от терен API: {elevation_text}",
            f"Източник на вятър: {source}",
            f"Вятър: {wind_speed:.1f} m/s, от {wind_from:.0f}°, пориви {gust:.1f} m/s",
            "",
            "ИЗЧИСЛЕНА ВЕРОЯТНА ЗОНА",
            f"Център: {format_decimal(result['impact_lat'])}, {format_decimal(result['impact_lon'])}",
            f"Радиус на търсене: {result['radius_m']:.0f} m",
            f"Посока от последната позиция: {result['bearing_deg']:.0f}°",
            f"Разстояние от последната позиция: {result['distance_m']:.0f} m",
            "",
            "ДЕТАЙЛИ НА МОДЕЛА",
            result["model_note"],
            f"Вятърът духа към: {result['wind_blowing_to_deg']:.0f}°",
            f"Оценена земна скорост: {result['ground_speed_ms']:.1f} m/s",
            f"Време с тяга/носене: {result['flight_time_s']:.0f} s",
            f"Време след изтощаване: {result['post_power_s']:.0f} s",
            f"Оценено време на падане: {result['fall_time_s']:.1f} s",
            "",
            "Google Maps:",
            self._maps_url(),
        ]
        self.output.insert("1.0", "\n".join(lines))
        self.output.configure(state="disabled")

    def _maps_url(self):
        if not self.latest_result:
            return ""
        return "https://www.google.com/maps/search/?api=1&query=" f"{self.latest_result['impact_lat']:.7f},{self.latest_result['impact_lon']:.7f}"

    def open_maps(self):
        if not self.latest_result:
            messagebox.showinfo("Няма резултат", "Първо натисни „Изчисли зона“.")
            return
        webbrowser.open(self._maps_url())


if __name__ == "__main__":
    app = LostDroneFinder()
    app.mainloop()
