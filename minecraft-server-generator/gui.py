from __future__ import annotations

import pathlib
import textwrap
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import List

from generator import (
    DEFAULT_PLUGINS,
    MIN_RAM_GB,
    generate_preview,
    generate_server,
    install_plugins_to_server,
)


class Tooltip:
    """Lightweight tooltip helper for Tk widgets."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, _event: tk.Event | None = None) -> None:
        if self.tip_window or not self.text:
            return
        x, y, _, cy = self.widget.bbox("insert") if self.widget.winfo_viewable() else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20 + cy
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
            wraplength=300,
        )
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, _event: tk.Event | None = None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class ServerGeneratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Minecraft Server Generator")
        self.root.geometry("1024x720")
        self.root.minsize(960, 640)

        self.server_path_var = tk.StringVar()
        self.server_name_var = tk.StringVar(value="Enhanced-SMP")
        self.version_var = tk.StringVar(value="1.21.10")
        self.player_count_var = tk.IntVar(value=100)
        self.ram_var = tk.IntVar(value=24)
        self.cpu_var = tk.IntVar(value=8)
        self.view_distance_var = tk.IntVar(value=8)
        self.sim_distance_var = tk.IntVar(value=6)
        self.fork_var = tk.StringVar(value="Purpur")
        self.enable_velocity_var = tk.BooleanVar(value=False)
        self.manage_path_var = tk.StringVar()
        self.manage_download_now_var = tk.BooleanVar(value=False)
        self.github_token_var = tk.StringVar()
        self.manual_urls_widget: ScrolledText | None = None
        self._manual_placeholder_cleared = False

        self.plugin_vars: dict[str, tk.BooleanVar] = {}
        self.manage_plugin_vars: dict[str, tk.BooleanVar] = {}

        self._build_layout()

    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        basics_frame = ttk.Frame(notebook, padding=12)
        self._build_basics_tab(basics_frame)
        notebook.add(basics_frame, text="Basics")

        hardware_frame = ttk.Frame(notebook, padding=12)
        self._build_hardware_tab(hardware_frame)
        notebook.add(hardware_frame, text="Hardware / VPS")

        optimizations_frame = ttk.Frame(notebook, padding=12)
        self._build_optimizations_tab(optimizations_frame)
        notebook.add(optimizations_frame, text="Optimizations")

        plugins_frame = ttk.Frame(notebook, padding=12)
        self._build_plugins_tab(plugins_frame)
        notebook.add(plugins_frame, text="Plugins")

        configs_frame = ttk.Frame(notebook, padding=12)
        self._build_configs_tab(configs_frame)
        notebook.add(configs_frame, text="Configs & Permissions")

        advanced_frame = ttk.Frame(notebook, padding=12)
        self._build_advanced_tab(advanced_frame)
        notebook.add(advanced_frame, text="Advanced")

        manage_frame = ttk.Frame(notebook, padding=12)
        self._build_manage_tab(manage_frame)
        notebook.add(manage_frame, text="Manage Existing Server")

        tools_frame = ttk.Frame(notebook, padding=12)
        self._build_tools_tab(tools_frame)
        notebook.add(tools_frame, text="Tools / Tasks")

        button_row = ttk.Frame(container)
        button_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_row, text="Generate Server", command=self.generate).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(button_row, text="Preview Files", command=self.preview).pack(side=tk.RIGHT, padx=4)
        ttk.Button(button_row, text="Quit", command=self.quit_application).pack(side=tk.RIGHT, padx=4)

    # ------------------------------------------------------------------
    def _build_basics_tab(self, frame: ttk.Frame) -> None:
        grid = ttk.Frame(frame)
        grid.pack(fill=tk.BOTH, expand=True)

        labels = [
            ("Server Name", self.server_name_var),
            ("Minecraft Version", self.version_var),
            ("Max Players", self.player_count_var),
            ("RAM (GB)", self.ram_var),
            ("CPU Cores", self.cpu_var),
            ("View Distance", self.view_distance_var),
            ("Simulation Distance", self.sim_distance_var),
        ]
        for idx, (label_text, var) in enumerate(labels):
            ttk.Label(grid, text=label_text).grid(row=idx, column=0, sticky=tk.W, pady=4)
            entry = ttk.Entry(grid, textvariable=var)
            entry.grid(row=idx, column=1, sticky=tk.EW, pady=4)
            Tooltip(entry, f"Set {label_text.lower()}. Suggested default shown.")

        ttk.Label(grid, text="Server Fork").grid(row=len(labels), column=0, sticky=tk.W, pady=4)
        fork_combo = ttk.Combobox(grid, textvariable=self.fork_var, values=["Purpur", "Paper", "Spigot"], state="readonly")
        fork_combo.grid(row=len(labels), column=1, sticky=tk.EW, pady=4)
        Tooltip(fork_combo, "Choose Purpur for best performance. Paper/Spigot supported.")

        ttk.Label(grid, text="Target Directory").grid(row=len(labels) + 1, column=0, sticky=tk.W, pady=4)
        path_entry = ttk.Entry(grid, textvariable=self.server_path_var)
        path_entry.grid(row=len(labels) + 1, column=1, sticky=tk.EW, pady=4)
        Tooltip(path_entry, "Folder where generated server files will be created.")

        browse = ttk.Button(grid, text="Browse", command=self._pick_directory)
        browse.grid(row=len(labels) + 1, column=2, padx=(6, 0))

        velocity_chk = ttk.Checkbutton(
            grid,
            text="Include Velocity scaling notes",
            variable=self.enable_velocity_var,
        )
        velocity_chk.grid(row=len(labels) + 2, column=0, columnspan=3, sticky=tk.W, pady=6)
        Tooltip(velocity_chk, "Adds Velocity/Bungee proxy guidance to generated README/setup.")

        grid.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _build_hardware_tab(self, frame: ttk.Frame) -> None:
        text = textwrap.dedent(
            """
            Recommended minimum hardware for up to 100 concurrent players:
            • CPU: 8c/16t Ryzen 7 7700 (4.5 GHz+) or Intel Xeon Gold 63xx
            • RAM: 32 GB DDR5 (allocate 24 GB to JVM, keep rest for OS, plugins, caches)
            • Storage: 200 GB NVMe SSD (room for world, Dynmap tiles, backups)
            • Network: 1 Gbps port / 500 Mbps upload, dedicated IPv4

            Provider ideas: Hetzner CPX51 (~$30/mo), OVH Rise-2, DigitalOcean 16 vCPU / 64 GB.
            Why: Sustains 20 TPS with 50+ plugins, pregen chunks, Dynmap renders, hourly backups.
            """
        ).strip()
        text_box = ScrolledText(frame, height=18, wrap=tk.WORD)
        text_box.insert(tk.END, text)
        text_box.config(state=tk.DISABLED)
        text_box.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _build_optimizations_tab(self, frame: ttk.Frame) -> None:
        info = textwrap.dedent(
            """
            JVM Flags (auto-generated): Uses 2025 Aikar G1GC flags sized to your RAM input.
            View distance defaults to 8 with simulation distance 6 for balanced performance.
            Native optimizations include hopper cooldown tweaks, anti-xray, entity activation ranges,
            and TPS-friendly mob caps. Adjust entries on Basics tab to customize.
            """
        ).strip()
        text_widget = ScrolledText(frame, height=16, wrap=tk.WORD)
        text_widget.insert(tk.END, info)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _build_plugins_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Select plugins to include (download script + sample configs).",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for plugin in DEFAULT_PLUGINS:
            var = tk.BooleanVar(value=plugin.default)
            self.plugin_vars[plugin.name] = var
            chk = ttk.Checkbutton(inner, text=f"{plugin.name} — {plugin.description}", variable=var)
            chk.pack(anchor=tk.W, pady=2)
            Tooltip(chk, f"Download URL: {plugin.url}")

    # ------------------------------------------------------------------
    def _build_configs_tab(self, frame: ttk.Frame) -> None:
        info = textwrap.dedent(
            """
            LuckPerms groups generated: default, vip, mod, admin (with sample permissions).
            EssentialsX configuration sets starter/vip kits, $ currency, spawn, balanced homes.
            GriefDefender defaults to 2,000 initial claim blocks, 150/hour accrual.
            Dynmap binds to 0.0.0.0:8123 with secure defaults. mcMMO settings tuned for SMP.
            Use the /lp editor command after first start to fine-tune live permissions.
            """
        ).strip()
        text_widget = ScrolledText(frame, wrap=tk.WORD)
        text_widget.insert(tk.END, info)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _build_advanced_tab(self, frame: ttk.Frame) -> None:
        info = textwrap.dedent(
            """
            Advanced guidance includes:
            • Chunk pre-generation via Chunky (/chunky radius 5000, start)
            • Automated backups (hourly tarball + 7-day retention) and 6h restarts
            • Velocity/Bungee scaling instructions with secret-forwarding and multi-world split
            • VPS setup (Ubuntu 24.04) commands + firewall + Java install script (setup.sh)
            """
        ).strip()
        text_widget = ScrolledText(frame, wrap=tk.WORD)
        text_widget.insert(tk.END, info)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _build_tools_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Common Operational Tasks", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        tasks = textwrap.dedent(
            """
            • Pregen World: After start, run `/chunky world world`, `/chunky radius 5000`, `/chunky start`.
            • Run Backups Manually: `./backup.sh` on Linux or `powershell -ExecutionPolicy Bypass -File .\\backup.ps1`.
            • Inspect Performance: `/spark profiler --timeout 60` then `/spark tps`.
            • Update Plugins: Use the Manage tab with "Download now" checked (or run plugins/download_plugins scripts).
            • Validate TPS: `/forge tps` equivalent is `/spark tps`; watch console for timings.
            • Autosave Off/On: `/save-off`, perform operations, then `/save-on` + `/save-all`.
            """
        ).strip()
        box = ScrolledText(frame, wrap=tk.WORD, height=12)
        box.insert(tk.END, tasks)
        box.config(state=tk.DISABLED)
        box.pack(fill=tk.BOTH, expand=True, pady=8)

        ttk.Label(frame, text="Maintenance Scripts", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        maintenance = textwrap.dedent(
            """
            Linux cron ideas:
              0 * * * * /opt/minecraft/server/backup.sh >/dev/null 2>&1
              0 */6 * * * tmux send-keys -t purpur "stop" ENTER

            Windows Task Scheduler:
              Program: powershell
              Args: -ExecutionPolicy Bypass -File C:\\path\\to\\backup.ps1
            """
        ).strip()
        box2 = ScrolledText(frame, wrap=tk.WORD, height=10)
        box2.insert(tk.END, maintenance)
        box2.config(state=tk.DISABLED)
        box2.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def _build_manage_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Manage an existing server's plugins", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 8)
        )
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=tk.X)
        ttk.Label(path_frame, text="Server directory").pack(side=tk.LEFT)
        path_entry = ttk.Entry(path_frame, textvariable=self.manage_path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(path_frame, text="Browse", command=self._pick_manage_directory).pack(side=tk.LEFT)

        inner_frame = ttk.Frame(frame)
        inner_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        ttk.Label(inner_frame, text="Select plugins to add or update:").pack(anchor=tk.W)
        canvas = tk.Canvas(inner_frame)
        scrollbar = ttk.Scrollbar(inner_frame, orient=tk.VERTICAL, command=canvas.yview)
        plugin_container = ttk.Frame(canvas)
        plugin_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=plugin_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for plugin in DEFAULT_PLUGINS:
            var = tk.BooleanVar(value=plugin.default)
            self.manage_plugin_vars[plugin.name] = var
            chk = ttk.Checkbutton(plugin_container, text=f"{plugin.name} — {plugin.description}", variable=var)
            chk.pack(anchor=tk.W, pady=2)
            Tooltip(chk, f"Download URL: {plugin.url}")

        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X, pady=6)
        ttk.Checkbutton(
            options_frame,
            text="Download now (requires internet + requests)",
            variable=self.manage_download_now_var,
        ).pack(anchor=tk.W)

        manual_frame = ttk.LabelFrame(frame, text="Additional plugin URLs (one per line)")
        manual_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        manual_box = ScrolledText(manual_frame, height=6, wrap=tk.WORD)
        manual_box.insert(
            tk.END,
            "Example:\nhttps://example.com/MyPlugin.jar\nhttps://cdn.modrinth.com/xyz/latest.jar",
        )
        manual_box.bind("<FocusIn>", lambda _e: self._clear_manual_placeholder())
        manual_box.pack(fill=tk.BOTH, expand=True)
        self.manual_urls_widget = manual_box

        token_frame = ttk.Frame(frame)
        token_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(token_frame, text="GitHub token (optional, raises API limits)").pack(anchor=tk.W)
        ttk.Entry(token_frame, textvariable=self.github_token_var, show="•").pack(fill=tk.X, expand=True)
        ttk.Label(
            token_frame,
            text="Generate at https://github.com/settings/tokens (classic) with public_repo scope.",
            foreground="#555",
        ).pack(anchor=tk.W)
        ttk.Button(frame, text="Apply to Server", command=self.apply_plugins_to_existing_server).pack(anchor=tk.E, pady=4)

    # ------------------------------------------------------------------
    def _pick_directory(self) -> None:
        path = filedialog.askdirectory(title="Select output folder for generated server")
        if path:
            self.server_path_var.set(path)

    # ------------------------------------------------------------------
    def _pick_manage_directory(self) -> None:
        path = filedialog.askdirectory(title="Select existing server directory")
        if path:
            self.manage_path_var.set(path)

    # ------------------------------------------------------------------
    def _clear_manual_placeholder(self) -> None:
        if not self.manual_urls_widget or self._manual_placeholder_cleared is True:
            return
        current = self.manual_urls_widget.get("1.0", tk.END).strip()
        if current.startswith("Example:"):
            self.manual_urls_widget.delete("1.0", tk.END)
        self._manual_placeholder_cleared = True

    # ------------------------------------------------------------------
    def _collect_inputs(self) -> dict | None:
        try:
            ram = int(self.ram_var.get())
            if ram < MIN_RAM_GB:
                raise ValueError(f"RAM must be at least {MIN_RAM_GB} GB")
            players = int(self.player_count_var.get())
            if players <= 0:
                raise ValueError("Player count must be positive")
            view_distance = int(self.view_distance_var.get())
            sim_distance = int(self.sim_distance_var.get())
            if view_distance < 4 or sim_distance < 2:
                raise ValueError("Distances must be reasonable (>=4 view, >=2 simulation)")
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc))
            return None

        output_dir = self.server_path_var.get().strip()
        if not output_dir:
            messagebox.showerror("Missing Path", "Please select an output directory.")
            return None

        selected_plugins = [name for name, var in self.plugin_vars.items() if var.get()]
        if not selected_plugins:
            messagebox.showwarning("No Plugins", "It is recommended to select at least one plugin.")

        config = {
            "server_name": self.server_name_var.get().strip() or "Enhanced-SMP",
            "version": self.version_var.get().strip() or "1.21.10",
            "max_players": players,
            "ram_gb": ram,
            "cpu_cores": int(self.cpu_var.get() or 8),
            "view_distance": view_distance,
            "simulation_distance": sim_distance,
            "fork": self.fork_var.get(),
            "output_dir": output_dir,
            "plugins": selected_plugins,
            "enable_velocity": bool(self.enable_velocity_var.get()),
        }
        return config

    # ------------------------------------------------------------------
    def generate(self) -> None:
        config = self._collect_inputs()
        if not config:
            return
        try:
            summary = generate_server(config)
        except Exception as exc:  # pragma: no cover - runtime errors shown to user
            messagebox.showerror("Generation Failed", f"{exc}")
            return
        message = "Created files:\n" + "\n".join(str(path) for path in summary.get("files", []))
        messagebox.showinfo("Success", message)

    # ------------------------------------------------------------------
    def preview(self) -> None:
        config = self._collect_inputs()
        if not config:
            return
        try:
            preview_text = generate_preview(config)
        except Exception as exc:
            messagebox.showerror("Preview Failed", str(exc))
            return
        window = tk.Toplevel(self.root)
        window.title("Preview")
        window.geometry("900x600")
        text = ScrolledText(window, wrap=tk.WORD)
        text.insert(tk.END, preview_text)
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    def quit_application(self) -> None:
        self.root.quit()
        self.root.destroy()

    # ------------------------------------------------------------------
    def apply_plugins_to_existing_server(self) -> None:
        server_path = self.manage_path_var.get().strip()
        if not server_path:
            messagebox.showerror("Missing Path", "Select the server directory you want to manage.")
            return
        selected_plugins = [name for name, var in self.manage_plugin_vars.items() if var.get()]
        if not selected_plugins:
            messagebox.showerror("No Plugins Selected", "Choose at least one plugin to add.")
            return
        manual_urls = self._get_manual_urls()
        try:
            result = install_plugins_to_server(
                server_path,
                selected_plugins,
                manual_urls=manual_urls,
                download_now=bool(self.manage_download_now_var.get()),
                github_token=(self.github_token_var.get().strip() or None),
            )
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Plugin Install Failed", str(exc))
            return
        msg = (
            f"Scripts updated in {result['plugins_dir']}. "
            + ("Plugins downloaded." if result["downloaded"] else "Run the download script to fetch plugins.")
        )
        messagebox.showinfo("Success", msg)

    # ------------------------------------------------------------------
    def _get_manual_urls(self) -> List[str]:
        if not self.manual_urls_widget:
            return []
        raw = self.manual_urls_widget.get("1.0", tk.END)
        urls = [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("Example:")]
        return urls


__all__ = ["ServerGeneratorApp"]
