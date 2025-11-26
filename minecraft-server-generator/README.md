# Minecraft Server Generator

A Tkinter desktop tool that builds a fully-configured Minecraft Java Edition survival server (Purpur/Paper/Spigot) for up to 100 concurrent players. The generator targets Purpur 1.21.10+ with performance presets, plugin configs, and deployment scripts for Ubuntu 24.04.

## Requirements
- Python 3.10+
- Tkinter (bundled with standard Python installers on Windows/macOS/Linux desktop)
- `requests` for downloading server jars

Install dependencies:
```bash
python -m pip install --upgrade pip
python -m pip install requests
```

## Usage
```bash
cd minecraft-server-generator
python main.py
```
1. Choose an output directory, server name, version, RAM, and fork (Purpur default).
2. Check or uncheck plugins (20+ curated essentials: LuckPerms, EssentialsX, GriefDefender, mcMMO, Dynmap, Spark, Chunky, ViaVersion trio, etc.).
3. Click **Generate Server** to create a ready-to-use folder containing cross-platform start scripts (`start.sh`, `start.ps1`, `start.bat`), configs, plugin download scripts, backups, and documentation (including `REQUIRED DOWNLOAD!!!.txt` for the Java 25 installer link).
4. Use **Preview Files** to view generated configs before writing.
5. Use the **Manage Existing Server** tab to point at an already-generated server folder, tick curated plugins, paste any extra plugin download URLs (one per line), and regenerate download scripts or fetch jars directly (requires `requests`). Add an optional GitHub token to bypass API rate limits.
6. Use the **Tools / Tasks** tab for quick reminders (chunky commands, cron snippets, etc.).
7. Follow the generated README and `setup.sh` for VPS provisioning (firewall, fail2ban, swap, Java 21) and plugin installation.

## Features
- Hardware/VPS guidance (Ryzen 7 7700, 32 GB RAM, NVMe storage, 1 Gbps port) built into GUI.
- Aikar G1GC flags sized to user RAM, Purpur/Paper optimizations (view-distance 8, simulation 6, anti-xray, hopper tweaks).
- Plugin configs: LuckPerms ranks (default/vip/mod/admin), Essentials economy & kits, GriefDefender claims, Dynmap public map, mcMMO balance.
- Scripts: `start.sh` (tmux auto-restart), `start.ps1`/`start.bat` (Windows loops), `backup.sh`/`backup.ps1`, `plugins/download_plugins.{sh,ps1}`, `setup.sh` (Linux hardening), README instructions, Cron/Task Scheduler tips, and a `REQUIRED DOWNLOAD!!!.txt` reminder with the Java 25 download link.
- Manage tab supports on-demand plugin downloads via the GitHub API; supply a PAT/token in the optional field to raise rate limits and paste any custom plugin URLs to download alongside the curated list.
- Advanced tab covers Chunky world pregen, Spark profiling, Dynmap render, backups, Velocity scaling. Tools tab adds operational reminders (cron snippets, one-off commands).
- Error handling validates RAM (>4 GB), player count, directories, and surfaces `requests` dependency guidance.

## Troubleshooting
- Missing Tk support: install `python3-tk` (Linux) or use GUI-enabled environment.
- Missing `requests`: run `python -m pip install requests`.
- Permission issues on generated scripts: run `chmod +x *.sh` after copying to Linux VPS.
- Jar download failures: ensure outbound HTTPS allowed; manual download URL stored in `JAR_DOWNLOAD.txt`.

Happy hosting! 🎮

All rights reserved to Heperkoo. If you need to obtain a license to use the source code above local usability, LMK.
