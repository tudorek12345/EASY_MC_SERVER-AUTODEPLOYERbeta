from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, unquote
import re
import zipfile
import xml.etree.ElementTree as ET

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None

MIN_RAM_GB = 8


@dataclass(frozen=True)
class Plugin:
    name: str
    description: str
    url: str
    default: bool = True
    download_type: str = "direct"
    download_meta: Optional[Dict[str, str]] = None


DEFAULT_PLUGINS: List[Plugin] = [
    Plugin("LuckPerms", "Permissions & ranks", "https://download.luckperms.net/latest/bukkit"),
    Plugin("Vault", "Economy API", "https://github.com/MilkBowl/Vault/releases/latest/download/Vault.jar"),
    Plugin(
        "EssentialsX",
        "Core commands",
        "https://github.com/EssentialsX/Essentials/releases/latest",
        download_type="github_release",
        download_meta={"owner": "EssentialsX", "repo": "Essentials", "asset_pattern": r"^EssentialsX-.*\.jar$"},
    ),
    Plugin(
        "EssentialsXChat",
        "Chat formatting",
        "https://github.com/EssentialsX/Essentials/releases/latest",
        download_type="github_release",
        download_meta={"owner": "EssentialsX", "repo": "Essentials", "asset_pattern": r"^EssentialsXChat-.*\.jar$"},
    ),
    Plugin(
        "EssentialsXSpawn",
        "Spawn control",
        "https://github.com/EssentialsX/Essentials/releases/latest",
        download_type="github_release",
        download_meta={"owner": "EssentialsX", "repo": "Essentials", "asset_pattern": r"^EssentialsXSpawn-.*\.jar$"},
    ),
    Plugin(
        "WorldEdit",
        "Building tools",
        "https://maven.enginehub.org/repo/com/sk89q/worldedit/worldedit-bukkit/",
        download_type="maven",
        download_meta={
            "base_url": "https://maven.enginehub.org/repo",
            "group": "com.sk89q.worldedit",
            "artifact": "worldedit-bukkit",
        },
    ),
    Plugin(
        "WorldGuard",
        "Region protection",
        "https://maven.enginehub.org/repo/com/sk89q/worldguard/worldguard-bukkit/",
        download_type="maven",
        download_meta={
            "base_url": "https://maven.enginehub.org/repo",
            "group": "com.sk89q.worldguard",
            "artifact": "worldguard-bukkit",
        },
    ),
    Plugin("GriefDefender", "Claims & anti-grief", "https://github.com/bloodmc/GriefDefender/releases/latest/download/GriefDefender.zip"),
    Plugin("CoreProtect", "Block logging", "https://ci.lucko.me/job/CoreProtect/lastSuccessfulBuild/artifact/target/CoreProtect-21.6.jar"),
    Plugin("Matrix", "Anti-cheat", "https://matrix.rico-gamer.de/latest/Matrix-latest.jar"),
    Plugin("AdvancedBan", "Moderation", "https://github.com/DevLeoko/AdvancedBan/releases/latest/download/AdvancedBan.jar"),
    Plugin("Shopkeepers", "Player shops", "https://github.com/Shopkeepers/Shopkeepers/releases/latest/download/Shopkeepers.jar"),
    Plugin("mcMMO", "Skills system", "https://ci.minebench.de/job/mcMMO/lastStableBuild/artifact/target/mcMMO-2.2.20.jar"),
    Plugin("Dynmap", "Live map", "https://github.com/webbukkit/dynmap/releases/latest/download/Dynmap-3.7-beta-6-spigot.jar"),
    Plugin("Spark", "Profiling", "https://download.lucko.me/spark/latest/bukkit"),
    Plugin("Chunky", "World pregen", "https://github.com/pop4959/Chunky/releases/latest/download/Chunky-Bukkit-1.4.28.jar"),
    Plugin("ViaVersion", "Allow newer clients", "https://ci.viaversion.com/job/ViaVersion/lastSuccessfulBuild/artifact/build/libs/ViaVersion-5.0.1.jar"),
    Plugin("ViaBackwards", "Allow older clients", "https://ci.viaversion.com/job/ViaBackwards/lastSuccessfulBuild/artifact/build/libs/ViaBackwards-5.0.1.jar"),
    Plugin("ViaRewind", "Legacy mobs", "https://ci.viaversion.com/job/ViaRewind/lastSuccessfulBuild/artifact/build/libs/ViaRewind-4.0.5.jar"),
    Plugin("EconomyShopGUI", "GUI shops", "https://github.com/Gypopo/EconomyShopGUI-Plugin/releases/latest/download/EconomyShopGUI-6.8.0.jar"),
    Plugin("PlayerWarps", "Player warp system", "https://github.com/OmerBenGera/PlayerWarps/releases/latest/download/PlayerWarps.jar"),
    Plugin("BetterSleeping3", "Skip nights", "https://github.com/Nuytemans-Dieter/BetterSleeping3/releases/latest/download/BetterSleeping3.jar"),
    Plugin("LiteBans", "Punishment management", "https://github.com/ruany/LiteBans/releases/latest/download/LiteBans.jar", default=False),
]

PLUGIN_LOOKUP = {plugin.name: plugin for plugin in DEFAULT_PLUGINS}


def _slugify(name: str) -> str:
    safe = [ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name.strip()]
    slug = "".join(safe).strip("-")
    return slug or "minecraft-server"


def _jar_download_info(fork: str, version: str) -> tuple[str, str | None]:
    fork_lower = fork.lower()
    if fork_lower == "purpur":
        return (f"purpur-{version}.jar", f"https://api.purpurmc.org/v2/purpur/{version}/latest/download")
    if fork_lower == "paper":
        return (f"paper-{version}.jar", f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/latest/downloads/paper-{version}.jar")
    if fork_lower == "spigot":
        return (f"spigot-{version}.jar", f"https://download.getbukkit.org/spigot/spigot-{version}.jar")
    if fork_lower == "forge":
        return (f"forge-{version}-server.jar", None)
    return (f"server-{version}.jar", None)


def _ensure_requests_available() -> None:
    if requests is None:
        raise RuntimeError(
            "The 'requests' package is required to download server jars. Install it via 'pip install requests'."
        )


def _download_file(url: str, destination: Path) -> None:
    _ensure_requests_available()
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    destination.write_bytes(response.content)


def _get_github_release_asset(meta: Dict[str, str], token: Optional[str] = None) -> Tuple[str, str]:
    _ensure_requests_available()
    owner = meta["owner"]
    repo = meta["repo"]
    pattern = meta["asset_pattern"]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(api_url, timeout=60, headers=headers)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        if status == 403:
            raise RuntimeError(
                f"GitHub API rate limit reached while fetching {owner}/{repo}. "
                "Try again later, disable 'Download now', or set a GITHUB_TOKEN environment variable."
            ) from exc
        raise
    release = response.json()
    regex = re.compile(pattern)
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if regex.search(name):
            download_url = asset.get("browser_download_url")
            if download_url:
                return name, download_url
    raise RuntimeError(f"Could not find asset matching '{pattern}' for {owner}/{repo}")


def _get_maven_release_asset(meta: Dict[str, str]) -> Tuple[str, str]:
    _ensure_requests_available()
    base_url = meta["base_url"].rstrip("/")
    group = meta["group"]
    artifact = meta["artifact"]
    group_path = group.replace(".", "/")
    metadata_url = f"{base_url}/{group_path}/{artifact}/maven-metadata.xml"
    response = requests.get(metadata_url, timeout=60)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    version = root.findtext("./versioning/release") or root.findtext("./versioning/latest")
    if not version:
        versions = root.findall("./versioning/versions/version")
        if versions:
            version = versions[-1].text
    if not version:
        raise RuntimeError(f"Unable to determine version for {group}:{artifact}")
    filename = f"{artifact}-{version}.jar"
    download_url = f"{base_url}/{group_path}/{artifact}/{version}/{filename}"
    return filename, download_url


def _resolve_forge_installer(mc_version: str) -> Tuple[str, str]:
    """Return (version_string, installer_url) for the latest Forge build matching the MC version prefix."""
    _ensure_requests_available()
    metadata_url = "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
    response = requests.get(metadata_url, timeout=60)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    versions = [elem.text for elem in root.findall("./versioning/versions/version") if elem.text]
    prefix = f"{mc_version}-"
    for version in reversed(versions):
        if version.startswith(prefix):
            url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
            return version, url
    raise RuntimeError(
        f"Forge installer for Minecraft {mc_version} not found. Check https://files.minecraftforge.net/ for supported versions."
    )


def _determine_plugin_download_url(plugin: Plugin) -> Optional[str]:
    if plugin.download_type == "github_release" and plugin.download_meta:
        if requests is None:
            return None
        try:
            _, download_url = _get_github_release_asset(plugin.download_meta, token=os.getenv("GITHUB_TOKEN"))
            return download_url
        except Exception:
            return None
    if plugin.download_type == "maven" and plugin.download_meta:
        try:
            _, download_url = _get_maven_release_asset(plugin.download_meta)
            return download_url
        except Exception:
            return None
    return plugin.url


def _derive_filename_from_url(url: str, fallback: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if name:
        return unquote(name)
    return fallback


def _render_start_sh(config: dict, jar_name: str) -> str:
    ram = config["ram_gb"]
    is_forge = config["fork"].lower() == "forge"
    jar_resolution = ""
    jar_variable = "$JAR_FILE"
    if is_forge:
        jar_resolution = textwrap.dedent(
            """
            resolve_forge_jar() {
              if [ -f "$JAR_FILE" ]; then
                echo "$JAR_FILE"
                return
              fi
              local candidate
              candidate=$(ls forge-*-server.jar 2>/dev/null | head -n 1)
              if [ -n "$candidate" ]; then
                echo "$candidate"
                return
              fi
              echo ""
            }
            """
        ).strip()
        jar_variable = "$(resolve_forge_jar)"
    jvm_flags = textwrap.dedent(
        f"""
        #!/bin/bash
        set -euo pipefail
        cd "$(dirname "$0")"
        SESSION_NAME="purpur"
        JAR_FILE="{jar_name}"
        if ! command -v tmux >/dev/null 2>&1; then
          echo "tmux is required. Install via 'sudo apt install -y tmux'."
          exit 1
        fi
        {"\n".join(jar_resolution.splitlines()) if jar_resolution else ""}
        while true; do
          TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
          echo "[$TIMESTAMP] Starting server..."
          {"RESOLVED_JAR=$" + jar_variable + "\n          if [ -z \"$RESOLVED_JAR\" ]; then\n            echo \"Forge server jar not found. Run 'java -jar forge-installer.jar --installServer' first.\"\n            sleep 10\n            continue\n          fi" if is_forge else ""}
          tmux new-session -d -s "$SESSION_NAME" "exec java \\
            -Xms{ram}G -Xmx{ram}G \\
            -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions -XX:+ParallelRefProcEnabled -XX:G1NewSizePercent=30 \\
            -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M \\
            -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 \\
            -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 \\
            -XX:G1MixedGCLiveThresholdPercent=85 -XX:G1RSetUpdatingPauseTimePercent=5 \\
            -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 \\
            -XX:+AlwaysPreTouch \\
            -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true \\
            -Dfile.encoding=UTF-8 -Djline.terminal=jline.UnsupportedTerminal \\
            -Dcom.mojang.eula.agree=true -jar {"$RESOLVED_JAR" if is_forge else "$JAR_FILE"} nogui"
          tmux attach -t "$SESSION_NAME"
          EXIT_CODE=$?
          echo "Server exited with code $EXIT_CODE. Restarting in 10 seconds..."
          tmux kill-session -t "$SESSION_NAME" >/dev/null 2>&1 || true
          sleep 10
        done
        """
    ).strip()
    return jvm_flags + "\n"


def _render_start_ps1(config: dict, jar_name: str) -> str:
    ram = config["ram_gb"]
    is_forge = config["fork"].lower() == "forge"
    resolve_function = ""
    jar_var = "$jarFile"
    if is_forge:
        resolve_function = textwrap.dedent(
            """
            function Resolve-ForgeJar {
              param($Default)
              if (Test-Path $Default) { return $Default }
              $candidate = Get-ChildItem -Filter 'forge-*-server.jar' | Select-Object -First 1
              if ($candidate) { return $candidate.Name }
              return $null
            }
            """
        ).strip()
        jar_var = "$selectedJar"
    return textwrap.dedent(
        f"""
        $ErrorActionPreference = "Stop"
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
        Set-Location $scriptDir
        $jarFile = "{jar_name}"
        {resolve_function}
        while ($true) {{
          $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
          Write-Host "[$timestamp] Starting server..."
          {"$selectedJar = Resolve-ForgeJar -Default $jarFile\n          if (-not $selectedJar) { Write-Host \"Forge jar not found. Run 'java -jar forge-installer.jar --installServer' first.\"; Start-Sleep -Seconds 10; continue }\n" if is_forge else ""}
          $arguments = @(
            "-Xms{ram}G",
            "-Xmx{ram}G",
            "-XX:+UseG1GC",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+ParallelRefProcEnabled",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:G1HeapWastePercent=5",
            "-XX:G1MixedGCCountTarget=4",
            "-XX:InitiatingHeapOccupancyPercent=15",
            "-XX:G1MixedGCLiveThresholdPercent=85",
            "-XX:G1RSetUpdatingPauseTimePercent=5",
            "-XX:SurvivorRatio=32",
            "-XX:+PerfDisableSharedMem",
            "-XX:MaxTenuringThreshold=1",
            "-XX:+AlwaysPreTouch",
            "-Dusing.aikars.flags=https://mcflags.emc.gs",
            "-Daikars.new.flags=true",
            "-Dfile.encoding=UTF-8",
            "-Djline.terminal=jline.UnsupportedTerminal",
            "-Dcom.mojang.eula.agree=true",
            "-jar",
            {jar_var},
            "nogui"
          )
          & java @arguments
          $exitCode = $LASTEXITCODE
          Write-Host "Server exited with code $exitCode. Restarting in 10 seconds..."
          Start-Sleep -Seconds 10
        }}
        """
    ).strip() + "\n"


def _render_start_bat(config: dict, jar_name: str) -> str:
    ram = config["ram_gb"]
    is_forge = config["fork"].lower() == "forge"
    forge_block = ""
    jar_ref = "\"%JAR_FILE%\""
    if is_forge:
        forge_block = textwrap.dedent(
            """
            set "RESOLVED_JAR=%JAR_FILE%"
            if not exist "%RESOLVED_JAR%" (
              set "RESOLVED_JAR="
              for %%F in (forge-*-server.jar) do (
                set "RESOLVED_JAR=%%F"
                goto found_forge
              )
            )
            :found_forge
            if not defined RESOLVED_JAR (
              echo Forge server jar not found. Run "java -jar forge-installer.jar --installServer" first.
              timeout /t 10 /nobreak >nul
              goto loop
            )
            """
        ).strip()
        jar_ref = "\"%RESOLVED_JAR%\""
    return textwrap.dedent(
        f"""
        @echo off
        setlocal ENABLEDELAYEDEXPANSION
        cd /d %~dp0
        set "JAR_FILE={jar_name}"
        set "JAVA_FLAGS=-Xms{ram}G -Xmx{ram}G -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions -XX:+ParallelRefProcEnabled -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=85 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -XX:+AlwaysPreTouch -Dusing.aikars.flags=https://mcflags.emc.gs -Daikars.new.flags=true -Dfile.encoding=UTF-8 -Djline.terminal=jline.UnsupportedTerminal -Dcom.mojang.eula.agree=true"
        :loop
        echo [%date% %time%] Starting server...
        {forge_block}
        java %JAVA_FLAGS% -jar {jar_ref} nogui
        set EXITCODE=%ERRORLEVEL%
        echo Server exited with code %EXITCODE%. Restarting in 10 seconds...
        timeout /t 10 /nobreak >nul
        goto loop
        """
    ).strip() + "\n"


def _render_server_properties(config: dict) -> str:
    return textwrap.dedent(
        f"""
        enable-jmx-monitoring=false
        rcon.port=25575
        level-seed=
        gamemode=survival
        enable-command-block=false
        enable-query=true
        generator-settings=
        level-name=world
        motd={config['server_name']} | Economy - Claims - Skills
        query.port=25565
        pvp=true
        difficulty=hard
        network-compression-threshold=256
        require-resource-pack=false
        max-tick-time=60000
        use-native-transport=true
        max-players={config['max_players']}
        online-mode=true
        enable-status=true
        allow-flight=false
        broadcast-rcon-to-ops=false
        view-distance={config['view_distance']}
        simulation-distance={config['simulation_distance']}
        max-build-height=384
        server-ip=
        allow-nether=true
        server-port=25565
        enable-rcon=false
        sync-chunk-writes=false
        op-permission-level=4
        prevent-proxy-connections=false
        resource-pack=
        entity-broadcast-range-percentage=75
        player-idle-timeout=0
        text-filtering-config=
        spawn-protection=0
        force-gamemode=false
        rate-limit=0
        hardcore=false
        white-list=false
        enforce-whitelist=false
        broadcast-console-to-ops=true
        spawn-npcs=true
        spawn-animals=true
        spawn-monsters=true
        snooper-enabled=false
        function-permission-level=2
        level-type=minecraft:normal
        spawn-keeploaded=true
        """
    ).strip() + "\n"


def _render_purpur_yml() -> str:
    return textwrap.dedent(
        """
        settings:
          check-for-updates: false
          bStats: true
        world-settings:
          default:
            redstone:
              optimize: true
              use-vanilla-logic: false
            alt-item-drops: true
            armor-stand:
              tick: false
            bat-go-to-sleep: true
            block-fall-time: 2
            disable-teleporting-dropping-items: true
            experience:
              merge-radius: 4.0
            item:
              merge-radius: 4.0
            block-ticking:
              max-tile-ticks-per-tick: 1000
            entity-tracking-range:
              players: 64
              animals: 48
              monsters: 48
              misc: 32
            entity-activation-range:
              animals: 24
              monsters: 32
              raiders: 48
              misc: 16
            mob-spawning:
              animal-cap: 32
              monster-cap: 70
              ambient-cap: 10
              water-animal-cap: 15
              water-ambient-cap: 20
            anti-xray:
              enabled: true
              engine-mode: 2
              layer-check: 5
              hidden-blocks:
                - ancient_debris
                - copper_ore
                - diamond_ore
                - deepslate_diamond_ore
                - emerald_ore
                - deepslate_emerald_ore
                - gold_ore
                - iron_ore
                - lapis_ore
                - redstone_ore
            hopper:
              disable-move-event: true
              cooldown-when-full: true
            player:
              disable-ticking: false
              use-alternate-keepalive: true
              portal-search-radius: 64
            villager:
              search-radius: 40
              work-immunity-after: 20
              activate-brain-ticks: 1
            wither:
              disable-block-damage: false
            tnt:
              allow-multi-ignite: false
              detonate-on-player-interact: false
            mechanics:
              use-alternate-keepalive: true
              disable-chunk-owners: true
        """
    ).strip() + "\n"


def _render_paper_yml(config: dict) -> str:
    return textwrap.dedent(
        f"""
        timings:
          enabled: false
        settings:
          velocity-support:
            enabled: {str(config['enable_velocity']).lower()}
            online-mode: true
            secret: change-me-for-velocity
        world-settings:
          default:
            view-distance: {config['view_distance']}
            simulation-distance: {config['simulation_distance']}
            enable-treasure-maps: false
            despawn-ranges:
              monster: 48
              creature: 32
              ambient: 24
              axolotls: 24
            entity-per-chunk-save-limit:
              area_effect_cloud: 16
              arrow: 32
              lightning_bolt: 1
            hopper:
              cooldown-when-full: true
              disable-move-event: true
            fixed-chunk-inhabitants: true
            chunks-per-tick: 6
            chunk-loading:
              min-load-radius: 2
              enable-frustum-priority: true
            max-auto-save-chunks-per-tick: 12
            anti-xray:
              enabled: true
              engine-mode: 2
              hidden-blocks:
                - copper_ore
                - iron_ore
                - gold_ore
                - diamond_ore
                - deepslate_diamond_ore
                - ancient_debris
            use-faster-eigencraft-redstone: true
            tick-rates:
              behavior: 3
              sensor: 2
            mob-spawn-limits:
              monsters: 55
              animals: 30
              water-animals: 10
              water-ambient: 20
              ambient: 5
        """
    ).strip() + "\n"


def _render_backup_sh() -> str:
    return textwrap.dedent(
        """
        #!/bin/bash
        set -euo pipefail
        BASE_DIR="$(cd \"$(dirname \"$0\")\" && pwd)"
        SRC_DIR="$BASE_DIR"
        BACKUP_DIR="$BASE_DIR/backups"
        mkdir -p "$BACKUP_DIR"
        TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
        tar --exclude="backups" --exclude="plugins/dynmap/web/tiles" -czf "$BACKUP_DIR/server_$TIMESTAMP.tar.gz" "$SRC_DIR"
        find "$BACKUP_DIR" -type f -mtime +7 -delete
        echo "Backup complete: $BACKUP_DIR/server_$TIMESTAMP.tar.gz"
        """
    ).strip() + "\n"


def _render_backup_ps1() -> str:
    return textwrap.dedent(
        """
        $ErrorActionPreference = "Stop"
        $baseDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
        $backupDir = Join-Path $baseDir "backups"
        if (-not (Test-Path $backupDir)) {
          New-Item -ItemType Directory -Path $backupDir | Out-Null
        }
        $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
        $archivePath = Join-Path $backupDir ("server_{0}.zip" -f $timestamp)
        $items = Get-ChildItem -LiteralPath $baseDir -Force | Where-Object { $_.Name -ne "backups" }
        if ($items.Count -eq 0) {
          Write-Host "No files to back up."
          exit 0
        }
        Compress-Archive -Path ($items | ForEach-Object { $_.FullName }) -DestinationPath $archivePath -Force
        $threshold = (Get-Date).AddDays(-7)
        Get-ChildItem -Path $backupDir -File | Where-Object { $_.LastWriteTime -lt $threshold } | Remove-Item -Force
        Write-Host ("Backup complete: {0}" -f $archivePath)
        """
    ).strip() + "\n"


def _render_luckperms_group(name: str, inherits: Iterable[str], perms: Iterable[str], weight: int) -> str:
    inherit_lines = "\n".join(f"  - {inherit}" for inherit in inherits) if inherits else "  []"
    perm_lines = "\n".join(f"  - {perm}" for perm in perms) if perms else "  []"
    template = textwrap.dedent(
        """
        name: {name}
        weight: {weight}
        inheritances:
        {inherits_block}
        permissions:
        {perms_block}
        """
    ).strip()
    return template.format(name=name, weight=weight, inherits_block=inherit_lines, perms_block=perm_lines) + "\n"


def _render_essentials_config() -> str:
    return textwrap.dedent(
        """
        settings:
          locale: en_US
          debug: false
          starting-balance: 500
          currency-symbol: "$"
        newbies:
          kit: starter
        spawnpoint:
          world: world
          x: 0.5
          y: 100
          z: 0.5
        kits:
          starter:
            delay: 86400
            items:
              - "stone_sword 1"
              - "bread 16"
          vip:
            delay: 43200
            items:
              - "diamond_sword 1 sharpness:2"
              - "golden_apple 3"
        chat:
          format: "&7[{GROUP}] &f{DISPLAYNAME}&7: &f{MESSAGE}"
          radius: 0
        homes:
          per-group:
            default: 1
            vip: 5
            mod: 10
        teleport-cooldown: 3
        teleport-delay: 3
        """
    ).strip() + "\n"


def _render_griefdefender_config() -> str:
    return textwrap.dedent(
        """
        claim-management:
          initial-claim-blocks: 2000
          accrual-blocks-per-hour: 150
          max-accrual-blocks: 12000
          abandons-restore-nature: true
        options:
          player-command-enter-claim: true
          claim-auto-extend-min-size: 10
          grief-defender-says: "&6[Claims]&f"
        flags:
          block-break: deny
          block-place: deny
          entity-damage: allow
        storage:
          provider: file
        """
    ).strip() + "\n"


def _render_dynmap_config() -> str:
    return textwrap.dedent(
        """
        update-interval: 300
        webserver-bindaddress: 0.0.0.0
        webserver-port: 8123
        defaultzoom: 2
        enable-web-login: false
        use-chunk-timestamps: true
        processed-tiles-per-tick: 32
        render-triggers:
          - blockplaced
          - blockbreak
          - playerjoin
          - playerquit
          - chunkgenerated
        """
    ).strip() + "\n"


def _render_mcmmo_config() -> str:
    return textwrap.dedent(
        """
        experience:
          base-multiplier: 1.0
          mob-spawners: 0.2
          fishing: 0.8
        skills:
          enable-pvp-skill-damage: false
          ability-length-modifier: 1.0
        cooldowns:
          tree-feller: 240
          serrated-strikes: 240
          giga-drill-breaker: 240
        """
    ).strip() + "\n"


def _build_plugin_script(selected_plugins: List[str], manual_urls: List[str]) -> str:
    lines = ["#!/bin/bash", "set -euo pipefail", "cd \"$(dirname \"$0\")\""]
    for name in selected_plugins:
        plugin = PLUGIN_LOOKUP.get(name)
        if not plugin:
            continue
        download_url = _determine_plugin_download_url(plugin)
        if not download_url:
            lines.append(f"echo \"Manual download required for {plugin.name}: {plugin.url}\"")
            continue
        filename = download_url.split("/")[-1] or f"{plugin.name}.jar"
        if plugin.name == "GriefDefender":
            lines.append(
                "wget -O GriefDefender.zip https://github.com/bloodmc/GriefDefender/releases/latest/download/GriefDefender.zip && "
                "unzip -o GriefDefender.zip && rm GriefDefender.zip"
            )
        else:
            lines.append(f"wget -O {filename} {download_url}")
    manual_count = 1
    for url in manual_urls:
        safe_name = f"manual-plugin-{manual_count}.jar"
        manual_count += 1
        lines.append(f"wget -O {safe_name} {url}")
    return "\n".join(lines) + "\n"


def _build_plugin_script_ps1(selected_plugins: List[str], manual_urls: List[str]) -> str:
    lines = [
        "$ErrorActionPreference = \"Stop\"",
        "$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition",
        "Set-Location $scriptDir",
    ]
    for name in selected_plugins:
        plugin = PLUGIN_LOOKUP.get(name)
        if not plugin:
            continue
        download_url = _determine_plugin_download_url(plugin)
        if not download_url:
            lines.append(f"Write-Host \"Manual download required for {plugin.name}: {plugin.url}\"")
            continue
        filename = download_url.split("/")[-1] or f"{plugin.name}.jar"
        is_zip = filename.lower().endswith(".zip")
        lines.append(f"Write-Host \"Downloading {plugin.name}...\"")
        lines.append(f"Invoke-WebRequest -Uri \"{download_url}\" -OutFile \"{filename}\" -UseBasicParsing")
        if is_zip:
            lines.append(f"Expand-Archive -LiteralPath \"{filename}\" -DestinationPath . -Force")
            lines.append(f"Remove-Item \"{filename}\" -Force")
    manual_count = 1
    for url in manual_urls:
        safe_name = f"manual-plugin-{manual_count}.jar"
        manual_count += 1
        lines.append(f"Write-Host \"Downloading manual plugin from {url}\"")
        lines.append(f"Invoke-WebRequest -Uri \"{url}\" -OutFile \"{safe_name}\" -UseBasicParsing")
    return "\n".join(lines) + "\n"


def _write_plugin_scripts(target_dir: Path, selected_plugins: List[str], manual_urls: List[str]) -> None:
    sh_path = target_dir / "download_plugins.sh"
    ps_path = target_dir / "download_plugins.ps1"
    sh_path.write_text(_build_plugin_script(selected_plugins, manual_urls), encoding="utf-8")
    ps_path.write_text(_build_plugin_script_ps1(selected_plugins, manual_urls), encoding="utf-8")
    os.chmod(sh_path, 0o755)


def _download_plugin_to_directory(plugin: Plugin, destination: Path, token: Optional[str] = None) -> Path:
    _ensure_requests_available()
    if plugin.download_type == "github_release" and plugin.download_meta:
        filename, download_url = _get_github_release_asset(plugin.download_meta, token)
    elif plugin.download_type == "maven" and plugin.download_meta:
        filename, download_url = _get_maven_release_asset(plugin.download_meta)
    else:
        filename = plugin.url.split("/")[-1] or f"{plugin.name}.jar"
        download_url = plugin.url
    temp_path = destination / filename
    response = requests.get(download_url, timeout=120)
    response.raise_for_status()
    temp_path.write_bytes(response.content)
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(temp_path, "r") as archive:
            archive.extractall(destination)
        temp_path.unlink()
        return destination
    return temp_path


def _download_manual_url(url: str, destination: Path, index: int) -> Path:
    _ensure_requests_available()
    fallback = f"manual-plugin-{index}.jar"
    filename = _derive_filename_from_url(url, fallback)
    target = destination / filename
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def _render_readme(config: dict, jar_name: str) -> str:
    velocity_section = textwrap.dedent(
        """
        ## Scaling with Velocity/Bungee
        - Deploy Velocity proxy, copy `forwarding-secret` into `paper.yml`.
        - Set `server.properties -> online-mode=false` on backend servers when proxying.
        - Move lobby/resource worlds into dedicated servers, sync permissions via LuckPerms MySQL.
        """
    ).strip() if config["enable_velocity"] else ""

    setup = textwrap.dedent(
        f"""
        # {config['server_name']} Deployment Guide

        ## Requirements
        - Ubuntu 24.04 LTS VPS (8c/16t CPU, 32 GB RAM, 200 GB NVMe, 1 Gbps)
        - Java 21 (Eclipse Temurin) installed system-wide

        ## Quick Start (Linux)
        1. Upload this folder to `/opt/minecraft/server` (owner `mc` user).
        2. Run `chmod +x start.sh backup.sh plugins/download_plugins.sh setup.sh`.
        3. Execute `./setup.sh` once on a fresh VPS for firewall + Java install notes.
        4. Download plugins: `cd plugins && ./download_plugins.sh`.
        5. Start the server with `./start.sh` (tmux auto-restart). Use `tmux attach -t purpur` to view console.
        6. In-game: `/op YourName`, `/lp user YourName parent set admin`.

        ## Quick Start (Windows 10/11)
        1. Ensure Java 21 is installed and on PATH (Eclipse Temurin recommended).
        2. Open PowerShell in the server folder and run `powershell -ExecutionPolicy Bypass -File .\\plugins\\download_plugins.ps1`.
        3. Launch `start.ps1` the same way for auto-restarts, or double-click `start.bat` for a classic loop.
        4. Use `powershell -ExecutionPolicy Bypass -File .\\backup.ps1` or Task Scheduler for periodic ZIP backups.
        5. Use `stop` in the console to shut down cleanly before closing the window.

        ## Included Files
        - `start.sh`: Auto-restarting tmux launcher with Aikar flags sized to {config['ram_gb']}G.
        - `start.ps1` / `start.bat`: PowerShell or CMD loops for Windows hosts (same flags).
        - `backup.sh`: Hourly cron-ready tarball backups with 7-day retention.
        - `backup.ps1`: PowerShell backup alternative with ZIP archives and pruning.
        - `setup.sh`: idempotent script listing OS hardening, Java install, firewall, swap, Velocity notes.
        - `server.properties`, `paper.yml`, `purpur.yml`: tuned for 100p SMP.
        - `plugins/download_plugins.sh` and `plugins/download_plugins.ps1`: download selected plugins on Linux or Windows.
        - `plugins/LuckPerms/...`: predefined ranks (default/vip/mod/admin).
        - `README.md`: this file.

        ## World Pre-Generation
        - Run `/chunky world world`, `/chunky radius 5000`, `/chunky start` after first join.

        ## Backups & Restarts
        - Add cron jobs: `0 * * * * /opt/minecraft/server/backup.sh` and `0 */6 * * * tmux send-keys -t purpur "stop" ENTER`.

        ## Monitoring
        - `/spark profiler --timeout 60`, `tail -f logs/latest.log`, `htop`, `df -h`.
        {velocity_section}
        """
    ).strip()

    forge_section = ""
    if config["fork"].lower() == "forge":
        forge_section = textwrap.dedent(
            """
            ## Forge-specific notes
            - The Forge installer (`forge-installer.jar`) is included. Run `java -jar forge-installer.jar --installServer` in this folder to generate the server jar.
            - The start scripts auto-detect the generated `forge-*-server.jar`. If it is missing, rerun the installer.
            - Copy your mods into the `mods/` folder and ensure both client and server have matching mod versions.
            - Forge servers do not use the Paper/Purpur configs; adjust `server.properties` and mod configs as needed.
            """
        ).strip()
        setup += "\n\n" + forge_section

    return setup + "\n"


def _render_java_download_notice() -> str:
    return textwrap.dedent(
        """
        REQUIRED DOWNLOAD!!!

        Please install Java 25 LTS before launching the server on Windows.
        Download the official installer from:
        https://adoptium.net/download?link=https%3A%2F%2Fgithub.com%2Fadoptium%2Ftemurin25-binaries%2Freleases%2Fdownload%2Fjdk-25.0.1%252B8%2FOpenJDK25U-jdk_x64_windows_hotspot_25.0.1_8.msi
        """
    ).strip() + "\n"


def _render_setup_script(config: dict) -> str:
    return textwrap.dedent(
        """
        #!/bin/bash
        set -euo pipefail
        echo "Updating system packages..."
        apt update && apt -y upgrade
        echo "Installing base utilities..."
        apt install -y curl wget git unzip htop screen tmux ufw fail2ban
        if ! command -v java >/dev/null 2>&1; then
          echo "Installing Eclipse Temurin 21..."
          apt install -y wget apt-transport-https gpg
          wget -O- https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | tee /etc/apt/keyrings/adoptium.gpg >/dev/null
          echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb noble main" > /etc/apt/sources.list.d/adoptium.list
          apt update && apt install -y temurin-21-jdk
        fi
        echo "Configuring firewall..."
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp
        ufw allow 25565/tcp
        ufw allow 25565/udp
        ufw allow 8123/tcp
        ufw --force enable
        echo "Enabling fail2ban..."
        systemctl enable --now fail2ban
        if ! swapon --show | grep -q swapfile; then
          fallocate -l 8G /swapfile
          chmod 600 /swapfile
          mkswap /swapfile
          swapon /swapfile
          echo '/swapfile none swap sw 0 0' >> /etc/fstab
        fi
        echo "Setup complete. Review /etc/fail2ban/jail.local and secure SSH keys."
        """
    ).strip() + "\n"


def build_file_map(config: dict, jar_name: str) -> Dict[str, str]:
    files: Dict[str, str] = {
        "start.sh": _render_start_sh(config, jar_name),
        "start.ps1": _render_start_ps1(config, jar_name),
        "start.bat": _render_start_bat(config, jar_name),
        "server.properties": _render_server_properties(config),
        "purpur.yml": _render_purpur_yml(),
        "paper.yml": _render_paper_yml(config),
        "backup.sh": _render_backup_sh(),
        "backup.ps1": _render_backup_ps1(),
        "README.md": _render_readme(config, jar_name),
        "REQUIRED DOWNLOAD!!!.txt": _render_java_download_notice(),
        "setup.sh": _render_setup_script(config),
        "plugins/download_plugins.sh": _build_plugin_script(config["plugins"], []),
        "plugins/download_plugins.ps1": _build_plugin_script_ps1(config["plugins"], []),
        "plugins/README.md": "Generated plugin configs + download script. Run download script before starting server.\n",
        "plugins/LuckPerms/yaml-storage/groups/default.yml": _render_luckperms_group(
            "default",
            [],
            [
                "essentials.home",
                "essentials.spawn",
                "essentials.msg",
                "essentials.balance",
                "griefdefender.claim.basic",
                "mcmmo.skills.*",
                "shopkeepers.trade",
                "dynmap.webchat",
                "chunky.use",
            ],
            1,
        ),
        "plugins/LuckPerms/yaml-storage/groups/vip.yml": _render_luckperms_group(
            "vip",
            ["default"],
            [
                "essentials.sethome.multiple.vip",
                "essentials.kits.vip",
                "essentials.repair",
                "griefdefender.claim.blocks.extra.5000",
                "mcmmo.ability.doublexp",
                "dynmap.marker.create",
            ],
            10,
        ),
        "plugins/LuckPerms/yaml-storage/groups/mod.yml": _render_luckperms_group(
            "mod",
            ["vip"],
            [
                "essentials.kick",
                "essentials.tempban",
                "advancedban.tempban",
                "coreprotect.inspect",
                "coreprotect.rollback",
                "griefdefender.claim.manage",
                "worldguard.region.info",
                "matrix.notify",
                "spark.viewer",
            ],
            50,
        ),
        "plugins/LuckPerms/yaml-storage/groups/admin.yml": _render_luckperms_group(
            "admin",
            ["mod"],
            ["*"],
            100,
        ),
        "plugins/Essentials/config.yml": _render_essentials_config(),
        "plugins/GriefDefender/global.conf": _render_griefdefender_config(),
        "plugins/Dynmap/configuration.txt": _render_dynmap_config(),
        "plugins/mcMMO/config.yml": _render_mcmmo_config(),
    }
    return files


def install_plugins_to_server(
    server_path: str,
    plugin_names: List[str],
    manual_urls: Optional[List[str]] = None,
    download_now: bool = False,
    github_token: Optional[str] = None,
) -> Dict[str, Path]:
    if not plugin_names:
        raise ValueError("Select at least one plugin to install.")
    server_dir = Path(server_path).expanduser().resolve()
    if not server_dir.exists():
        raise FileNotFoundError(f"Server directory '{server_dir}' does not exist.")
    plugins_dir = server_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    manual_urls = [url.strip() for url in (manual_urls or []) if url.strip()]
    _write_plugin_scripts(plugins_dir, plugin_names, manual_urls)
    downloaded: Dict[str, Path] = {}
    if download_now:
        for name in plugin_names:
            plugin = PLUGIN_LOOKUP.get(name)
            if not plugin:
                continue
            path = _download_plugin_to_directory(plugin, plugins_dir, token=github_token)
            downloaded[name] = path
        for idx, url in enumerate(manual_urls, start=1):
            try:
                path = _download_manual_url(url, plugins_dir, idx)
                downloaded[f"manual_{idx}"] = path
            except Exception as exc:
                raise RuntimeError(f"Failed to download manual plugin {url}: {exc}") from exc
    return {"server": server_dir, "plugins_dir": plugins_dir, "downloaded": downloaded}


def generate_server(config: dict) -> Dict[str, List[Path]]:
    slug = _slugify(config["server_name"])
    target_dir = Path(config["output_dir"]).expanduser().resolve() / f"{slug}-server"
    target_dir.mkdir(parents=True, exist_ok=True)

    jar_name, jar_url = _jar_download_info(config["fork"], config["version"])
    forge_installer_url = None
    forge_manual_message = None
    if config["fork"].lower() == "forge":
        try:
            if requests is not None:
                _, forge_installer_url = _resolve_forge_installer(config["version"])
            else:
                raise RuntimeError(
                    "Forge installer requires the 'requests' package. Install it or download manually."
                )
        except Exception as exc:
            forge_manual_message = (
                f"{exc}\nDownload the installer manually from https://files.minecraftforge.net/ "
                "and place it here as forge-installer.jar."
            )
    files = build_file_map(config, jar_name)
    written: List[Path] = []
    for relative, content in files.items():
        destination = target_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        if destination.name.endswith(('.sh', '.py')) or destination.name in {"start.sh", "backup.sh", "setup.sh"}:
            os.chmod(destination, 0o755)
        written.append(destination)

    jar_path = target_dir / jar_name
    if forge_installer_url:
        installer_path = target_dir / "forge-installer.jar"
        if requests is None:
            (target_dir / "FORGE_DOWNLOAD.txt").write_text(
                f"Download Forge installer from:\n{forge_installer_url}\nSave as forge-installer.jar and run:\n"
                "java -jar forge-installer.jar --installServer\n",
                encoding="utf-8",
            )
        else:
            _download_file(forge_installer_url, installer_path)
            written.append(installer_path)
    elif forge_manual_message:
        (target_dir / "FORGE_DOWNLOAD.txt").write_text(
            forge_manual_message + "\n", encoding="utf-8"
        )
    elif jar_url:
        if requests is None:
            (target_dir / "JAR_DOWNLOAD.txt").write_text(
                f"Download the server jar manually from:\n{jar_url}\nSave as {jar_name} in this folder.\n",
                encoding="utf-8",
            )
        else:
            _download_file(jar_url, jar_path)
            written.append(jar_path)

    return {"target": [target_dir], "files": written}


def generate_preview(config: dict) -> str:
    jar_name, _ = _jar_download_info(config["fork"], config["version"])
    files = build_file_map(config, jar_name)
    preview_blocks = []
    for relative, content in files.items():
        block = f"## {relative}\n{content.strip()}"
        preview_blocks.append(block)
    return "\n\n".join(preview_blocks)


__all__ = [
    "Plugin",
    "DEFAULT_PLUGINS",
    "MIN_RAM_GB",
    "generate_server",
    "generate_preview",
    "install_plugins_to_server",
]
