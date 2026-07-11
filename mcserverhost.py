#!/usr/bin/env python3
"""
MCServerHost - Host a Minecraft Server Instantly
Downloads Paper MC and exposes it via playit.gg (no port forwarding needed).
"""

import subprocess
import sys
import platform
import shutil
import os
import re


def _is_root():
    if sys.platform == "win32":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _detect_pkg_manager():
    if sys.platform == "win32":
        return "winget"
    if sys.platform == "darwin":
        return "brew"
    for m in ["apt", "apt-get", "dnf", "yum", "pacman", "zypper"]:
        if shutil.which(m):
            return m
    return None


def _install_package(name):
    pm = _detect_pkg_manager()
    if pm in ("apt", "apt-get"):
        sudo = ["sudo"] if not _is_root() else []
        return _run(sudo + [pm, "install", "-y", name])
    elif pm == "dnf":
        sudo = ["sudo"] if not _is_root() else []
        return _run(sudo + ["dnf", "install", "-y", name])
    elif pm == "yum":
        sudo = ["sudo"] if not _is_root() else []
        return _run(sudo + ["yum", "install", "-y", name])
    elif pm == "pacman":
        sudo = ["sudo"] if not _is_root() else []
        return _run(sudo + ["pacman", "-S", "--noconfirm", name])
    elif pm == "zypper":
        sudo = ["sudo"] if not _is_root() else []
        return _run(sudo + ["zypper", "install", "-y", name])
    elif pm == "brew":
        return _run(["brew", "install", name])
    elif pm == "winget":
        return _run(["winget", "install", "--id", name,
                      "--accept-source-agreements", "--accept-package-agreements"])
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="no package manager found")


def _try_import_tkinter():
    try:
        import tkinter
        return True
    except ImportError:
        return False


def _install_tkinter():
    system = platform.system()
    pm = _detect_pkg_manager()
    print("[bootstrap] tkinter not found. Installing...")

    if system == "Linux":
        if pm in ("apt", "apt-get"):
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            r = _install_package(f"{pyver}-tk")
            if r.returncode != 0:
                r = _install_package("python3-tk")
            return r.returncode == 0
        elif pm == "dnf":
            return _install_package("python3-tkinter").returncode == 0
        elif pm == "yum":
            return _install_package("python3-tkinter").returncode == 0
        elif pm == "pacman":
            return _install_package("tk").returncode == 0
        elif pm == "zypper":
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}-tk"
            return _install_package(pyver).returncode == 0
    elif system == "Darwin":
        return _install_package("python-tk").returncode == 0
    elif system == "Windows":
        print("[bootstrap] On Windows, re-run the Python installer with 'tcl/tk and IDLE' checked.")
        return False
    return False



def _install_java():
    system = platform.system()
    pm = _detect_pkg_manager()
    print("[bootstrap] Java 21+ not found. Installing OpenJDK...")

    if system == "Linux":
        if pm in ("apt", "apt-get"):
            for pkg in ("openjdk-25-jre-headless", "openjdk-21-jre-headless", "openjdk-17-jre-headless"):
                r = _install_package(pkg)
                if r.returncode == 0:
                    return True
            return False
        elif pm in ("dnf", "yum"):
            for pkg in ("java-25-openjdk-headless", "java-21-openjdk-headless", "java-17-openjdk-headless"):
                r = _install_package(pkg)
                if r.returncode == 0:
                    return True
            return False
        elif pm == "pacman":
            return _install_package("jre-openjdk").returncode == 0
        elif pm == "zypper":
            for pkg in ("java-25-openjdk-headless", "java-21-openjdk-headless", "java-17-openjdk-headless"):
                r = _install_package(pkg)
                if r.returncode == 0:
                    return True
            return False
    elif system == "Darwin":
        if shutil.which("brew"):
            r = _install_package("openjdk")
            if r.returncode == 0:
                return True
        print("[bootstrap] Install Java 21+ from https://adoptium.net")
        return False
    elif system == "Windows":
        print("[bootstrap] Attempting to download and install Java 21 from Adoptium...")
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False
        if not is_admin:
            print("[bootstrap] Java install requires admin. Please run as Administrator or install manually.")
            print("[bootstrap] Download from https://adoptium.net")
            return False
        arch = platform.machine().lower()
        if arch in ("amd64", "x86_64"):
            jarch = "x64"
        elif arch in ("arm64", "aarch64"):
            jarch = "aarch64"
        else:
            jarch = "x64"
        url = f"https://api.adoptium.net/v3/binary/latest/21/ga/windows/{jarch}/jdk/hotspot/normal/eclipse?project=jdk"
        tmp_msi = os.path.join(os.environ.get("TEMP", "."), "adoptium-jdk21.msi")
        try:
            print("[bootstrap] Downloading Java 21 MSI...")
            curl_ok = shutil.which("curl")
            if curl_ok:
                r = subprocess.run(["curl", "-L", "-o", tmp_msi, url],
                                   capture_output=True, timeout=300)
                dl_ok = r.returncode == 0 and os.path.exists(tmp_msi) and os.path.getsize(tmp_msi) > 1_000_000
            else:
                dl_ok = False
            if not dl_ok:
                ps_cmd = f"Invoke-WebRequest -Uri '{url}' -OutFile '{tmp_msi}'"
                r = subprocess.run(["powershell", "-Command", ps_cmd],
                                   capture_output=True, timeout=300)
                dl_ok = r.returncode == 0 and os.path.exists(tmp_msi) and os.path.getsize(tmp_msi) > 1_000_000
            if not dl_ok:
                print("[bootstrap] Failed to download Java 21 MSI.")
                print("[bootstrap] Download from https://adoptium.net")
                return False
            print("[bootstrap] Installing Java 21 (silent)...")
            r = subprocess.run(["msiexec", "/i", tmp_msi, "/qn", "ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome"],
                               capture_output=True, timeout=300)
            try:
                os.remove(tmp_msi)
            except Exception:
                pass
            if r.returncode == 0:
                print("[bootstrap] Java 21 installed successfully.")
                return True
            print(f"[bootstrap] MSI install returned code {r.returncode}")
            return False
        except Exception as e:
            print(f"[bootstrap] Java install failed: {e}")
            print("[bootstrap] Download from https://adoptium.net")
            return False
    return False


# ── Java check (used by bootstrap) ──────────────────────────
def check_java():
    try:
        result = subprocess.run(
            ["java", "-version"], capture_output=True, text=True, timeout=10
        )
        output = result.stderr or result.stdout
        first_line = output.strip().split("\n")[0] if output.strip() else "Unknown"
        match = re.search(r'"(\d+)', output)
        if match:
            return int(match.group(1)), first_line
        return None, first_line
    except FileNotFoundError:
        return None, "Java not found"
    except Exception as e:
        return None, str(e)


def get_java_install_hint():
    system = platform.system()
    if system == "Linux":
        return "Install with: sudo apt install openjdk-21-jre (Ubuntu/Debian)"
    elif system == "Windows":
        return "Download from https://adoptium.net (Java 21+)"
    elif system == "Darwin":
        return "Install with: brew install openjdk (Homebrew)"
    return "Install Java 21+ from https://adoptium.net"


def bootstrap():
    print(f"{'=' * 50}")
    print(f"  MCServerHost - Dependency Check")
    print(f"{'=' * 50}")

    if not _try_import_tkinter():
        if _install_tkinter() and _try_import_tkinter():
            print("[bootstrap] tkinter installed OK")
        else:
            print("[bootstrap] FAILED to install tkinter. Install manually and re-run.")
            input("Press Enter to exit...")
            sys.exit(1)
    else:
        print("[bootstrap] tkinter: OK")

    java_ver, java_info = check_java()
    if not java_ver or java_ver < 21:
        if _install_java():
            java_ver2, java_info2 = check_java()
            if java_ver2 and java_ver2 >= 21:
                print(f"[bootstrap] Java: OK ({java_info2})")
            else:
                print("[bootstrap] Java installed but may need a restart or PATH update.")
        else:
            print("[bootstrap] Java not installed. Install Java 21+ from https://adoptium.net")
            print("[bootstrap] You can still open the app, but need Java to run the server.")
    else:
        print(f"[bootstrap] Java: OK ({java_info})")

    print(f"{'=' * 50}\n")


# ── Phase 1: Bootstrap before any GUI imports ──────────────
if __name__ == "__main__":
    bootstrap()

# ── Phase 2: GUI imports (tkinter guaranteed installed) ─────
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import urllib.request
import urllib.error
import urllib.parse
import csv
import time
import webbrowser
from pathlib import Path
import zipfile
import datetime
import socket
import hashlib
import tarfile

# ── Constants ───────────────────────────────────────────────
APP_NAME = "MCServerHost"
VERSION = "2.1.3"
SERVER_DIR = Path.home() / "MCServerHost"
PAPER_JAR = SERVER_DIR / "paper.jar"
VANILLA_JAR = SERVER_DIR / "server.jar"
PLAYIT_BIN = SERVER_DIR / ("playit.exe" if sys.platform == "win32" else "playit")
CONFIG_FILE = SERVER_DIR / "config.json"
EULA_FILE = SERVER_DIR / "eula.txt"
PROPS_FILE = SERVER_DIR / "server.properties"

PAPER_API = "https://fill.papermc.io/v3/projects/paper"
MOJANG_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
USER_AGENT = f"{APP_NAME}/{VERSION}"
MODRINTH_API = "https://api.modrinth.com/v2"
FABRIC_META = "https://meta.fabricmc.net/v2"
FABRIC_MAVEN = "https://maven.fabricmc.net"
FORGE_MAVEN = "https://maven.minecraftforge.net"
PROFILES_DIR = SERVER_DIR / "profiles"
FABRIC_JAR = SERVER_DIR / "fabric-server.jar"
FORGE_JAR = SERVER_DIR / "forge-server.jar"
INSTANCES_DIR = SERVER_DIR / "servers"

BG_DARK = "#1a1a2e"
BG_MID = "#22223a"
BG_LIGHT = "#2d2d4a"
BG_HOVER = "#36365a"
BG_ENTRY = "#16162a"
FG_MAIN = "#dcdcdc"
FG_ACCENT = "#7c8cf8"
FG_GREEN = "#4ade80"
FG_RED = "#f87171"
FG_YELLOW = "#fbbf24"
FG_DIM = "#6b7280"
FG_BRIGHT = "#f0f0f0"

DEFAULT_CONFIG = {
    "server_port": 25565,
    "ram_min": "1G",
    "ram_max": "2G",
    "motd": "A Minecraft Server",
    "max_players": 20,
    "online_mode": True,
    "difficulty": "normal",
    "gamemode": "survival",
    "view_distance": 10,
    "simulation_distance": 10,
    "use_playit": True,
    "server_type": "paper",
    "mc_version": "",
    "accepted_eula": False,
    "white_list": False,
    "pvp": True,
    "spawn_protection": 16,
    "level_seed": "",
    "level_type": "minecraft:normal",
    "level_name": "world",
    "enable_command_block": False,
    "spawn_monsters": True,
    "spawn_animals": True,
    "spawn_npcs": True,
    "generate_structures": True,
    "allow_nether": True,
    "hardcore": False,
    "max_tick_time": 60000,
    "network_compression_threshold": 256,
    "rate_limit": 0,
    "auto_restart": False,
    "restart_delay": 10,
    "auto_backup": True,
    "scheduled_restart": False,
    "scheduled_restart_hours": 24,
    "periodic_backup": False,
    "periodic_backup_interval": 30,
    "log_export": False,
    "backup_max_age_days": 0,
    "backup_max_count": 0,
    "resource_pack": "",
    "resource_pack_sha1": "",
    "resource_pack_prompt": "",
    "require_resource_pack": False,
    "notifications_enabled": True,
    "cloud_backup_remote": "",
    "scheduled_tasks": [],
    "widget_visible_cards": True,
    "widget_visible_ram": True,
    "widget_visible_tps": True,
}

SERVER_PRESETS = {
    "Survival SMP": {
        "motd": "A Survival World",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 10,
        "spawn_protection": 16,
        "max_players": 20,
        "ram_min": "1G",
        "ram_max": "2G",
        "server_type": "paper",
    },
    "Hardcore Survival": {
        "motd": "Hardcore Survival",
        "gamemode": "survival",
        "difficulty": "hard",
        "pvp": True,
        "hardcore": True,
        "view_distance": 12,
        "spawn_protection": 16,
        "max_players": 10,
        "ram_min": "2G",
        "ram_max": "4G",
        "server_type": "paper",
    },
    "Creative / Builder": {
        "motd": "Creative Builder",
        "gamemode": "creative",
        "difficulty": "peaceful",
        "pvp": False,
        "hardcore": False,
        "view_distance": 16,
        "spawn_protection": 0,
        "max_players": 30,
        "ram_min": "2G",
        "ram_max": "4G",
        "server_type": "paper",
    },
    "Skyblock": {
        "motd": "Skyblock Server",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 8,
        "spawn_protection": 0,
        "max_players": 15,
        "ram_min": "1G",
        "ram_max": "3G",
        "server_type": "paper",
    },
    "Minigames / PVP": {
        "motd": "PVP Arena",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 8,
        "spawn_protection": 0,
        "max_players": 50,
        "ram_min": "2G",
        "ram_max": "6G",
        "server_type": "paper",
    },
    "Vanilla (No Mods)": {
        "motd": "Vanilla Minecraft",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 10,
        "spawn_protection": 16,
        "max_players": 20,
        "ram_min": "1G",
        "ram_max": "2G",
        "server_type": "vanilla",
    },
    "Modded (Forge)": {
        "motd": "Modded Server",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 8,
        "spawn_protection": 16,
        "max_players": 20,
        "ram_min": "3G",
        "ram_max": "6G",
        "server_type": "forge",
    },
    "Modded (Fabric)": {
        "motd": "Fabric Modded",
        "gamemode": "survival",
        "difficulty": "normal",
        "pvp": True,
        "hardcore": False,
        "view_distance": 8,
        "spawn_protection": 16,
        "max_players": 20,
        "ram_min": "2G",
        "ram_max": "4G",
        "server_type": "fabric",
    },
}


# ── Utility functions ───────────────────────────────────────
def get_latest_paper_version():
    req = urllib.request.Request(PAPER_API, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        versions_dict = data.get("versions", {})
        all_versions = []
        for group, vers in versions_dict.items():
            for v in vers:
                lower = v.lower()
                if any(tag in lower for tag in ("-pre", "-rc", "alpha", "beta", "snapshot")):
                    continue
                all_versions.append(v)

        def vk(v):
            nums = re.findall(r"\d+", v)
            return tuple(int(n) for n in nums)

        all_versions.sort(key=vk, reverse=True)
        return all_versions if all_versions else []
    except Exception:
        return []


def get_paper_build_url(version):
    url = f"{PAPER_API}/versions/{version}/builds"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        stable = [b for b in data if b.get("channel") == "STABLE"]
        if not stable:
            return None, None, None
        build = stable[-1]
        bid = build.get("id")
        dl = build.get("downloads", {}).get("server:default", {})
        return dl.get("url"), bid, dl.get("name")
    except Exception:
        return None, None, None


def get_vanilla_versions():
    req = urllib.request.Request(MOJANG_MANIFEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        releases = [v["id"] for v in data["versions"] if v["type"] == "release"]
        return releases
    except Exception:
        return []


def get_vanilla_download_url(version):
    req = urllib.request.Request(MOJANG_MANIFEST, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            manifest = json.loads(resp.read())
        entry = next((v for v in manifest["versions"] if v["id"] == version), None)
        if not entry:
            return None
        req2 = urllib.request.Request(entry["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            vdata = json.loads(resp2.read())
        srv = vdata["downloads"]["server"]
        return srv["url"]
    except Exception:
        return None


def download_file(url, dest, progress_cb=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest + ".tmp"
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(done, total)
        shutil.move(tmp, dest)
        return True
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return False


def get_playit_url():
    system = platform.system()
    machine = platform.machine().lower()
    base = "https://github.com/playit-cloud/playit-agent/releases/latest/download"
    if system == "Linux":
        arch = "aarch64" if ("aarch64" in machine or "arm" in machine) else "amd64"
        return f"{base}/playit-linux-{arch}"
    elif system == "Windows":
        return f"{base}/playit-windows-amd64.exe"
    elif system == "Darwin":
        arch = "aarch64" if ("arm" in machine or "aarch64" in machine) else "amd64"
        return f"{base}/playit-macos-{arch}"
    return None


def get_public_ip():
    for url in ["https://api.ipify.org", "https://ifconfig.me", "https://icanhazip.com"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode().strip()
        except Exception:
            continue
    return None


def get_fabric_server_url(mc_version):
    url = f"{FABRIC_META}/versions/loader/{mc_version}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if not data:
            return None, None
        latest = data[0]
        loader_ver = latest["loader"]["version"]
        server_url = f"{FABRIC_META}/versions/loader/{mc_version}/{loader_ver}/server/jar"
        return server_url, f"fabric-server-{mc_version}.jar"
    except Exception:
        return None, None


def get_forge_server_url(mc_version):
    req = urllib.request.Request(
        f"{FORGE_MAVEN}/net/minecraftforge/forge/promotions_slim.json",
        headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        promos = data.get("promos", {})
        forge_ver = None
        for key in reversed(list(promos.keys())):
            if key.startswith(mc_version + "-"):
                forge_ver = promos[key]
                break
        if not forge_ver:
            for key in reversed(list(promos.keys())):
                if mc_version in key:
                    forge_ver = promos[key]
                    break
        if not forge_ver:
            return None, None, None
        full_ver = f"{mc_version}-{forge_ver}"
        jar_url = f"{FORGE_MAVEN}/net/minecraftforge/forge/{full_ver}/forge-{full_ver}-installer.jar"
        label = f"Forge {full_ver}"
        return jar_url, f"forge-{full_ver}-installer.jar", label
    except Exception:
        return None, None, None


def generate_server_properties(config):
    props = {
        "generator-settings": "{}",
        "allow-nether": str(config.get("allow_nether", True)).lower(),
        "level-name": config.get("level_name", "world"),
        "enable-command-block": str(config.get("enable_command_block", False)).lower(),
        "gamemode": config.get("gamemode", "survival"),
        "level-seed": str(config.get("level_seed", "")),
        "server-port": str(config.get("server_port", 25565)),
        "difficulty": config.get("difficulty", "normal"),
        "spawn-monsters": str(config.get("spawn_monsters", True)).lower(),
        "max-players": str(config.get("max_players", 20)),
        "spawn-animals": str(config.get("spawn_animals", True)).lower(),
        "texturepack": "",
        "level-type": config.get("level_type", "minecraft:normal"),
        "pvp": str(config.get("pvp", True)).lower(),
        "spawn-npcs": str(config.get("spawn_npcs", True)).lower(),
        "generate-structures": str(config.get("generate_structures", True)).lower(),
        "view-distance": str(config.get("view_distance", 10)),
        "simulation-distance": str(config.get("simulation_distance", 10)),
        "max-tick-time": str(config.get("max_tick_time", 60000)),
        "network-compression-threshold": str(config.get("network_compression_threshold", 256)),
        "motd": config.get("motd", "A Minecraft Server"),
        "rate-limit": str(config.get("rate_limit", 0)),
        "white-list": str(config.get("white_list", False)).lower(),
        "online-mode": str(config.get("online_mode", True)).lower(),
        "hardcore": str(config.get("hardcore", False)).lower(),
        "spawn-protection": str(config.get("spawn_protection", 16)),
        "enforce-secure-profile": "true",
        "hide-online-players": "false",
        "player-idle-timeout": "0",
        "allow-flight": "false",
        "max-world-size": "29999984",
        "prevent-proxy-connections": "false",
        "server-location": "",
        "require-resource-pack": str(config.get("require_resource_pack", False)).lower(),
        "resource-pack-prompt": config.get("resource_pack_prompt", ""),
        "resource-pack-id": "",
        "resource-pack": config.get("resource_pack", ""),
        "resource-pack-sha1": config.get("resource_pack_sha1", ""),
        "resource-pack-server-overlay": "false",
        "debug": "false",
        "sync-chunk-writes": "true",
        "entity-broadcast-range-percentage": "100",
        "text-filtering-config": "",
        "log-ips": "true",
        "use-native-transport": "true",
        "status-port": str(config.get("server_port", 25565)),
        "allow-jmx-monitoring": "false",
        "io.netty.allocator.max-direct-memory": "-1",
        "force-gamemode": "false",
        "chunk-format": "data-driven",
        "function-permission-level": "2",
        "initial-disabled-packs": "",
        "initial-enabled-packs": "vanilla",
        "proxy-rewrite-flow": "true",
        "report-unused-overrides": "true",
        "validate-messages": "false",
        "compact-format": "false",
        "log-deprecated-nbt-usage": "false",
        "initial-tick": "-1",
        "extra-custom-tab-list-data": "",
        "realm-backup-id": "-1",
        "server-authoritative-blocking": "true",
        "restrict-to-same-ip-connection": "false",
        "broadcast-console-to-ops": "true",
        "broadcast-rcon-to-ops": "true",
        "bungeecord": "false",
        "enable-query": "false",
        "query.port": str(config.get("server_port", 25565)),
        "enable-rcon": "false",
        "rcon.password": "",
        "rcon.port": "25575",
        "save-player-positions": "true",
        "auto-save": "true",
        "max-chained-neighbor-updates": "1000000",
        "enforce-whitelist": "false",
        "op-permission-level": "4",
    }
    lines = ["#Minecraft server properties"]
    for key, value in props.items():
        lines.append(f"{key}={value}")
    lines.append("#" + time.strftime("%a %b %d %H:%M:%S %Z %Y"))
    return "\n".join(lines) + "\n"


# ── Main Application ────────────────────────────────────────
class MCServerHost:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1060x740")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG_DARK)

        self.server_process = None
        self.playit_process = None
        self.running = False
        self.server_ready = False
        self.playit_claim_url = None
        self.playit_address = None
        self.public_ip = None
        self.stopped_manually = False
        self.online_players = set()
        self.scheduled_restart_timer = None
        self.periodic_backup_timer = None
        self.resource_monitor_id = None
        self.log_file = None
        self._log_flush_id = None
        self._log_queue = []
        self._log_lock = threading.Lock()
        self._players_lock = threading.Lock()
        self.active_instance = "default"
        self._perf_ram_history = []
        self._perf_tps_history = []
        self._perf_player_history = []
        self._perf_start_time = None
        self.scheduled_task_timers = []
        self._player_session_starts = {}
        self._player_stats_data = {}
        self._player_stats_lock = threading.Lock()

        self.config = self._load_config()
        self._setup_styles()
        self._build_ui()
        self.root.bind_all("<MouseWheel>", MCServerHost._on_global_mousewheel)
        self.root.bind_all("<Button-4>", MCServerHost._on_global_mousewheel)
        self.root.bind_all("<Button-5>", MCServerHost._on_global_mousewheel)
        self.root.after(200, self._initial_checks)
        self.root.after(300, self._refresh_players)
        self.root.after(300, self._refresh_bans)
        self.root.after(300, self._refresh_task_list)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_instance_dir(self, name):
        if name == "default":
            return SERVER_DIR
        return INSTANCES_DIR / name

    def _server_dir(self):
        return self._get_instance_dir(self.active_instance)

    def _load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    main_cfg = json.load(f)
                self.active_instance = main_cfg.get("active_instance", "default")
                if self.active_instance == "default":
                    cfg.update(main_cfg)
            except Exception:
                pass
        inst_dir = self._get_instance_dir(self.active_instance)
        inst_cfg = inst_dir / "config.json"
        if inst_cfg.exists() and self.active_instance != "default":
            try:
                with open(inst_cfg) as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        cfg["active_instance"] = self.active_instance
        return cfg

    def _save_config(self):
        sd = self._server_dir()
        sd.mkdir(parents=True, exist_ok=True)
        if self.active_instance == "default":
            cfg_file = CONFIG_FILE
        else:
            cfg_file = sd / "config.json"
        with open(cfg_file, "w") as f:
            json.dump(self.config, f, indent=2)
        if self.active_instance != "default":
            main_cfg = {}
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE) as f:
                        main_cfg = json.load(f)
                except Exception:
                    pass
            main_cfg["active_instance"] = self.active_instance
            SERVER_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(main_cfg, f, indent=2)

    def _build_instance_selector(self):
        self.instance_var = tk.StringVar(value=self.active_instance)
        self.instance_combo = ttk.Combobox(
            self.hdr_instance_frame, textvariable=self.instance_var,
            state="readonly", width=18, values=self._get_instance_names()
        )
        self.instance_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.instance_combo.bind("<<ComboboxSelected>>", lambda e: self._switch_instance(self.instance_var.get()))
        ttk.Button(self.hdr_instance_frame, text="+", width=3,
                   command=self._create_instance).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(self.hdr_instance_frame, text="-", width=3,
                   command=self._delete_instance).pack(side=tk.LEFT, padx=(2, 0))

    def _get_instance_names(self):
        names = ["default"]
        if INSTANCES_DIR.exists():
            for d in sorted(INSTANCES_DIR.iterdir()):
                if d.is_dir() and d.name not in names:
                    names.append(d.name)
        return names

    def _refresh_instance_list(self):
        self.instance_combo["values"] = self._get_instance_names()

    def _switch_instance(self, name):
        if name == self.active_instance:
            return
        if self.running:
            messagebox.showwarning("Server Running", "Stop the server before switching instances.")
            self.instance_var.set(self.active_instance)
            return
        self._save_config()
        self._cancel_all_timers()
        self._stop_resource_monitor()
        self.active_instance = name
        self.config = self._load_config()
        self._save_config()
        self._apply_config_to_ui()
        self._refresh_config_list()
        self._refresh_players()
        self._refresh_bans()
        self._load_player_stats()
        self._refresh_task_list()
        self._check_server_installed()
        self._log(f"Switched to instance: {name}", "success")

    def _create_instance(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("New Instance", "Instance name:", parent=self.root)
        if not name:
            return
        name = re.sub(r'[^a-zA-Z0-9_-]', '', name.strip())
        if not name or name == "default":
            messagebox.showwarning("Invalid Name", "Enter a valid instance name (alphanumeric, _, -).")
            return
        if (INSTANCES_DIR / name).exists():
            messagebox.showwarning("Exists", f"Instance '{name}' already exists.")
            return
        INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
        inst_dir = INSTANCES_DIR / name
        inst_dir.mkdir(parents=True, exist_ok=True)
        try:
            if CONFIG_FILE.exists():
                shutil.copy2(str(CONFIG_FILE), str(inst_dir / "config.json"))
        except Exception:
            pass
        self.active_instance = name
        self.config = self._load_config()
        self._save_config()
        self.instance_combo["values"] = self._get_instance_names()
        self.instance_var.set(name)
        self._apply_config_to_ui()
        self._log(f"Created instance: {name}", "success")

    def _delete_instance(self):
        if self.active_instance == "default":
            messagebox.showwarning("Cannot Delete", "Cannot delete the default instance.")
            return
        name = self.active_instance
        if not messagebox.askyesno("Delete Instance",
                                   f"Delete instance '{name}'?\nAll data in this instance will be permanently removed."):
            return
        inst_dir = INSTANCES_DIR / name
        if inst_dir.exists():
            try:
                shutil.rmtree(str(inst_dir))
            except Exception as e:
                self._log(f"Failed to delete instance: {e}", "error")
                return
        self.active_instance = "default"
        self.config = self._load_config()
        self._save_config()
        self.instance_combo["values"] = self._get_instance_names()
        self.instance_var.set("default")
        self._apply_config_to_ui()
        self._refresh_config_list()
        self._refresh_players()
        self._refresh_bans()
        self._log(f"Deleted instance: {name}", "success")

    def _check_rclone(self):
        try:
            r = subprocess.run(["rclone", "version"], capture_output=True, text=True, timeout=10)
            return r.returncode == 0
        except Exception:
            return False

    def _cloud_backup(self):
        remote = self.cloud_remote_var.get().strip()
        if not remote:
            messagebox.showwarning("No Remote", "Enter an rclone remote path (e.g., gdrive:MCServerHost/backups).")
            return
        sd = self._server_dir()
        backups_dir = sd / "backups"
        if not backups_dir.exists():
            messagebox.showwarning("No Backups", "No local backups found to sync.")
            return
        self.cloud_status.configure(text="Syncing to cloud...")
        self.cloud_sync_btn.configure(state="disabled")

        def _do():
            try:
                r = subprocess.run(
                    ["rclone", "sync", str(backups_dir), remote],
                    capture_output=True, text=True, timeout=600
                )
                if r.returncode == 0:
                    self._log("Cloud backup sync complete", "success")
                    self.root.after(0, lambda: self.cloud_status.configure(text="Sync complete!"))
                else:
                    err = r.stderr.strip()[:200] if r.stderr else "Unknown error"
                    self._log(f"Cloud sync failed: {err}", "error")
                    self.root.after(0, lambda: self.cloud_status.configure(text="Sync failed"))
            except Exception as e:
                self._log(f"Cloud sync error: {e}", "error")
                self.root.after(0, lambda: self.cloud_status.configure(text="Sync failed"))
            self.root.after(0, lambda: self.cloud_sync_btn.configure(state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    def _build_cloud_backup_section(self, parent):
        cloud_frame = ttk.Frame(parent)
        cloud_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(cloud_frame, text="Cloud Backup", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        has_rclone = self._check_rclone()
        if has_rclone:
            cr_row = ttk.Frame(cloud_frame)
            cr_row.pack(fill=tk.X)
            ttk.Label(cr_row, text="Remote:", style="Dim.TLabel").pack(side=tk.LEFT)
            self.cloud_remote_var = tk.StringVar(value=self.config.get("cloud_backup_remote", ""))
            ttk.Entry(cr_row, textvariable=self.cloud_remote_var, width=40).pack(side=tk.LEFT, padx=(4, 8))
            self.cloud_sync_btn = ttk.Button(cr_row, text="Sync Backups to Cloud", style="Blue.TButton",
                                              command=self._cloud_backup)
            self.cloud_sync_btn.pack(side=tk.LEFT)
            self.cloud_status = ttk.Label(cr_row, text="", style="Dim.TLabel")
            self.cloud_status.pack(side=tk.LEFT, padx=8)
        else:
            ttk.Label(cloud_frame,
                      text="rclone not found. Install it: curl https://rclone.org/install.sh | sudo bash",
                      style="Err.TLabel", wraplength=600).pack(anchor="w")

    def _migrate_server(self):
        sd = self._server_dir()
        if not sd.exists():
            messagebox.showwarning("No Server", "Server directory not found.")
            return
        ts = datetime.datetime.now().strftime("%Y-%m-%d")
        default_name = f"MCServerHost_{self.active_instance}_{ts}.tar.gz"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".tar.gz",
            filetypes=[("Gzip tar files", "*.tar.gz"), ("All files", "*.*")],
            initialfile=default_name,
            title="Save Server Package As"
        )
        if not save_path:
            return
        self.migrate_status.configure(text="Packaging server...")
        self.migrate_btn.configure(state="disabled")

        exclude_prefixes = ("logs/", "cache/", "crash-reports/", "__pycache__/")
        exclude_suffixes = (".tmp",)
        exclude_globs = ("playit*",)

        def _do():
            try:
                with tarfile.open(save_path, "w:gz") as tar:
                    for item in sd.iterdir():
                        rel = item.name
                        if any(rel.startswith(p.rstrip("/")) or rel == p.rstrip("/") for p in exclude_prefixes):
                            continue
                        if any(rel.endswith(s) for s in exclude_suffixes):
                            continue
                        if any(re.match(g.replace("*", ".*"), rel) for g in exclude_globs):
                            continue
                        tar.add(str(item), arcname=item.name)
                self._log(f"Server packaged to {save_path}", "success")
                self.root.after(0, lambda: self.migrate_status.configure(text="Done!"))
            except Exception as e:
                self._log(f"Package failed: {e}", "error")
                self.root.after(0, lambda: self.migrate_status.configure(text="Failed"))
            self.root.after(0, lambda: self.migrate_btn.configure(state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    def _import_server(self):
        tar_path = filedialog.askopenfilename(
            filetypes=[("Gzip tar files", "*.tar.gz"), ("All files", "*.*")],
            title="Select Server Archive"
        )
        if not tar_path:
            return
        from tkinter import simpledialog
        name = simpledialog.askstring("Import Server", "Instance name for imported server:", parent=self.root)
        if not name:
            return
        name = re.sub(r'[^a-zA-Z0-9_-]', '', name.strip())
        if not name or name == "default":
            messagebox.showwarning("Invalid Name", "Enter a valid instance name.")
            return
        if (INSTANCES_DIR / name).exists():
            messagebox.showwarning("Exists", f"Instance '{name}' already exists.")
            return
        INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
        inst_dir = INSTANCES_DIR / name
        inst_dir.mkdir(parents=True, exist_ok=True)
        self.migrate_status.configure(text="Importing server...")
        self.migrate_import_btn.configure(state="disabled")

        def _do():
            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    tar.extractall(str(inst_dir))
                self._log(f"Server imported to instance '{name}'", "success")
                self.root.after(0, lambda: self.migrate_status.configure(text="Import complete!"))
                self.root.after(0, lambda: self._refresh_instance_list())
            except Exception as e:
                self._log(f"Import failed: {e}", "error")
                self.root.after(0, lambda: self.migrate_status.configure(text="Import failed"))
            self.root.after(0, lambda: self.migrate_import_btn.configure(state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        FONT_UI = ("Segoe UI", 10)
        FONT_BOLD = ("Segoe UI", 10, "bold")
        FONT_HEADER = ("Segoe UI", 16, "bold")
        FONT_SUB = ("Segoe UI", 11, "bold")
        FONT_MONO = ("Cascadia Code", 10)

        s.configure(".", background=BG_DARK, foreground=FG_MAIN, font=FONT_UI)
        s.configure("TFrame", background=BG_DARK)
        s.configure("TLabel", background=BG_DARK, foreground=FG_MAIN, font=FONT_UI)
        s.configure("Card.TFrame", background=BG_MID, relief="flat")
        s.configure("Card.TLabel", background=BG_MID, foreground=FG_MAIN, font=FONT_UI)
        s.configure("Header.TLabel", background=BG_DARK, foreground=FG_BRIGHT, font=FONT_HEADER)
        s.configure("SubHeader.TLabel", background=BG_MID, foreground=FG_BRIGHT, font=FONT_SUB)
        s.configure("Status.TLabel", background=BG_DARK, foreground=FG_GREEN, font=FONT_SUB)
        s.configure("Off.TLabel", background=BG_DARK, foreground=FG_RED, font=FONT_SUB)
        s.configure("Dim.TLabel", background=BG_DARK, foreground=FG_DIM, font=FONT_UI)
        s.configure("CardDim.TLabel", background=BG_MID, foreground=FG_DIM, font=FONT_UI)
        s.configure("Ok.TLabel", background=BG_MID, foreground=FG_GREEN, font=FONT_UI)
        s.configure("Err.TLabel", background=BG_MID, foreground=FG_RED, font=FONT_UI)
        s.configure("Addr.TLabel", background=BG_MID, foreground=FG_GREEN, font=("Cascadia Code", 13, "bold"))

        s.configure("TButton", background=BG_LIGHT, foreground=FG_MAIN, padding=(14, 7),
                     font=FONT_UI, relief="flat", borderwidth=0)
        s.map("TButton", background=[("active", BG_HOVER), ("pressed", BG_HOVER)],
              foreground=[("active", FG_BRIGHT)])
        s.configure("Green.TButton", background=FG_GREEN, foreground="#0a0a1a",
                     font=FONT_BOLD, relief="flat", borderwidth=0, padding=(14, 7))
        s.map("Green.TButton", background=[("active", "#36c772"), ("pressed", "#36c772")])
        s.configure("Red.TButton", background=FG_RED, foreground="#0a0a1a",
                     font=FONT_BOLD, relief="flat", borderwidth=0, padding=(14, 7))
        s.map("Red.TButton", background=[("active", "#dc5050"), ("pressed", "#dc5050")])
        s.configure("Blue.TButton", background=FG_ACCENT, foreground="#0a0a1a",
                     font=FONT_BOLD, relief="flat", borderwidth=0, padding=(14, 7))
        s.map("Blue.TButton", background=[("active", "#6270e0"), ("pressed", "#6270e0")])

        s.configure("TNotebook", background=BG_DARK, borderwidth=0, padding=0)
        s.configure("TNotebook.Tab", background=BG_MID, foreground=FG_DIM, padding=(18, 9),
                     font=FONT_UI, borderwidth=0, relief="flat")
        s.map("TNotebook.Tab",
              background=[("selected", BG_LIGHT), ("active", BG_HOVER)],
              foreground=[("selected", FG_BRIGHT), ("active", FG_MAIN)],
              padding=[("selected", (18, 9)), ("!selected", (18, 9))])

        s.configure("TCheckbutton", background=BG_DARK, foreground=FG_MAIN, font=FONT_UI)
        s.configure("TEntry", fieldbackground=BG_ENTRY, foreground=FG_MAIN, insertcolor=FG_ACCENT,
                     borderwidth=0, relief="flat", font=FONT_UI, padding=6)
        s.configure("TSpinbox", fieldbackground=BG_ENTRY, foreground=FG_MAIN, borderwidth=0,
                     font=FONT_UI, padding=4)
        s.configure("TCombobox", fieldbackground=BG_ENTRY, foreground=FG_MAIN, borderwidth=0,
                     font=FONT_UI, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", BG_ENTRY)],
              foreground=[("readonly", FG_MAIN)])
        s.configure("Horizontal.TProgressbar", background=FG_ACCENT, troughcolor=BG_ENTRY,
                     borderwidth=0, relief="flat")
        s.configure("TRadiobutton", background=BG_DARK, foreground=FG_MAIN, font=FONT_UI)
        s.configure("TSeparator", background=BG_LIGHT)

        s.configure("Treeview", background=BG_ENTRY, foreground=FG_MAIN, fieldbackground=BG_ENTRY,
                     borderwidth=0, relief="flat", font=FONT_UI, rowheight=28)
        s.configure("Treeview.Heading", background=BG_MID, foreground=FG_BRIGHT, font=FONT_BOLD,
                     relief="flat", borderwidth=0)
        s.map("Treeview", background=[("selected", BG_HOVER)], foreground=[("selected", FG_BRIGHT)])
        s.map("Treeview.Heading", background=[("active", BG_LIGHT)])
        s.configure("Treeview", indent=12)

        s.configure("Vertical.TScrollbar", background=BG_MID, troughcolor=BG_ENTRY,
                     borderwidth=0, relief="flat", arrowsize=12)
        s.map("Vertical.TScrollbar",
              background=[("active", BG_HOVER), ("pressed", BG_HOVER)])
        s.configure("Horizontal.TScrollbar", background=BG_MID, troughcolor=BG_ENTRY,
                     borderwidth=0, relief="flat", arrowsize=12)
        s.map("Horizontal.TScrollbar",
              background=[("active", BG_HOVER), ("pressed", BG_HOVER)])

    def _build_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        hdr = ttk.Frame(main)
        hdr.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(hdr, text=APP_NAME, style="Header.TLabel").pack(side=tk.LEFT)
        self.hdr_instance_frame = ttk.Frame(hdr)
        self.hdr_instance_frame.pack(side=tk.LEFT, padx=(10, 0))
        self._build_instance_selector()
        self.res_lbl = ttk.Label(hdr, text="", style="Dim.TLabel")
        self.res_lbl.pack(side=tk.LEFT, padx=14)
        self.status_lbl = ttk.Label(hdr, text="  Offline", style="Off.TLabel")
        self.status_lbl.pack(side=tk.RIGHT, padx=4)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self._build_setup_tab()
        self._build_server_tab()
        self._build_console_tab()
        self._build_plugins_tab()
        self._build_mods_tab()
        self._build_players_tab()
        self._build_bans_tab()
        self._build_network_tab()
        self._build_configs_tab()
        self._build_stats_tab()

    # ── Setup Tab ───────────────────────────────────────────
    def _build_setup_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Setup  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Prerequisites", style="SubHeader.TLabel").pack(anchor="w")
        self.java_card = self._info_card(frm)
        self.java_card.pack(fill=tk.X, pady=(6, 4))
        self.paper_card = self._info_card(frm)
        self.paper_card.pack(fill=tk.X, pady=4)
        self.playit_card = self._info_card(frm)
        self.playit_card.pack(fill=tk.X, pady=4)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)

        ttk.Label(frm, text="Server Type", style="SubHeader.TLabel").pack(anchor="w")
        type_row = ttk.Frame(frm)
        type_row.pack(fill=tk.X, pady=(6, 4))
        self.server_type_var = tk.StringVar(value=self.config.get("server_type", "paper"))
        ttk.Radiobutton(type_row, text="Paper MC (Recommended - optimized)",
                        variable=self.server_type_var, value="paper",
                        command=self._on_server_type_change).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(type_row, text="Vanilla",
                        variable=self.server_type_var, value="vanilla",
                        command=self._on_server_type_change).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(type_row, text="Fabric (Mod loader)",
                        variable=self.server_type_var, value="fabric",
                        command=self._on_server_type_change).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(type_row, text="Forge (Mod loader)",
                        variable=self.server_type_var, value="forge",
                        command=self._on_server_type_change).pack(side=tk.LEFT)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)

        ttk.Label(frm, text="Quick Presets", style="SubHeader.TLabel").pack(anchor="w")
        preset_row = ttk.Frame(frm)
        preset_row.pack(fill=tk.X, pady=(6, 4))
        self.preset_var = tk.StringVar(value="Custom")
        ttk.Combobox(preset_row, textvariable=self.preset_var, state="readonly", width=22,
                     values=["Custom"] + list(SERVER_PRESETS.keys())).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(preset_row, text="Apply Preset", command=self._apply_preset).pack(side=tk.LEFT)
        self.preset_status = ttk.Label(preset_row, text="", style="Dim.TLabel")
        self.preset_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)

        self.version_label = ttk.Label(frm, text="Paper MC Version", style="SubHeader.TLabel")
        self.version_label.pack(anchor="w")
        ver_row = ttk.Frame(frm)
        ver_row.pack(fill=tk.X, pady=(6, 4))
        self.version_var = tk.StringVar()
        self.version_combo = ttk.Combobox(ver_row, textvariable=self.version_var, state="readonly", width=20)
        self.version_combo.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(ver_row, text="Refresh Versions", command=self._fetch_versions).pack(side=tk.LEFT)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        dl_row = ttk.Frame(frm)
        dl_row.pack(fill=tk.X)
        self.dl_btn = ttk.Button(dl_row, text="Download / Update Server", style="Blue.TButton", command=self._download_server)
        self.dl_btn.pack(side=tk.LEFT)
        self.dl_progress = ttk.Progressbar(dl_row, mode="determinate", length=300)
        self.dl_progress.pack(side=tk.LEFT, padx=10)
        self.dl_status = ttk.Label(dl_row, text="", style="Dim.TLabel")
        self.dl_status.pack(side=tk.LEFT, padx=4)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        script_row = ttk.Frame(frm)
        script_row.pack(fill=tk.X)
        ttk.Button(script_row, text="Generate Startup Script",
                   command=self._generate_startup_script).pack(side=tk.LEFT)
        self.script_status = ttk.Label(script_row, text="", style="Dim.TLabel")
        self.script_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        ram_row = ttk.Frame(frm)
        ram_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(ram_row, text="RAM:").pack(side=tk.LEFT)
        ttk.Label(ram_row, text="  Min:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(10, 2))
        self.ram_min_var = tk.StringVar(value=self.config.get("ram_min", "1G"))
        ttk.Combobox(ram_row, textvariable=self.ram_min_var, width=6,
                     values=["512M", "1G", "1.5G", "2G", "3G", "4G", "6G", "8G"]).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(ram_row, text="Max:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(10, 2))
        self.ram_max_var = tk.StringVar(value=self.config.get("ram_max", "2G"))
        ttk.Combobox(ram_row, textvariable=self.ram_max_var, width=6,
                     values=["1G", "1.5G", "2G", "3G", "4G", "6G", "8G", "12G", "16G"]).pack(side=tk.LEFT, padx=(0, 6))

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        self.eula_var = tk.BooleanVar(value=self.config.get("accepted_eula", False))
        ttk.Checkbutton(frm, text="I accept the Minecraft EULA (eula.txt)",
                        variable=self.eula_var, command=self._on_eula_toggle).pack(anchor="w")
        eula_link = tk.Label(frm, text="https://aka.ms/MinecraftEULA", fg=FG_ACCENT, bg=BG_DARK,
                              cursor="hand2", font=("Segoe UI", 9, "underline"))
        eula_link.pack(anchor="w", padx=24)
        eula_link.bind("<Button-1>", lambda e: webbrowser.open("https://aka.ms/MinecraftEULA"))

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        prof_frame = ttk.Frame(frm)
        prof_frame.pack(fill=tk.X)
        ttk.Label(prof_frame, text="Server Profiles", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        prof_row = ttk.Frame(prof_frame)
        prof_row.pack(fill=tk.X)
        self.profile_var = tk.StringVar()
        ttk.Entry(prof_row, textvariable=self.profile_var, width=20).pack(side=tk.LEFT)
        ttk.Button(prof_row, text="Save Profile", command=self._save_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(prof_row, text="Load Profile", command=self._load_profile).pack(side=tk.LEFT, padx=4)
        ttk.Button(prof_row, text="Delete Profile", command=self._delete_profile).pack(side=tk.LEFT, padx=4)
        self.profile_status = ttk.Label(prof_row, text="", style="Dim.TLabel")
        self.profile_status.pack(side=tk.LEFT, padx=8)

    # ── Server Tab ──────────────────────────────────────────
    def _build_server_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Server  ")

        scroll_inner = self._scrollable_frame(tab)

        top = ttk.Frame(scroll_inner)
        top.pack(fill=tk.X, padx=14, pady=(12, 0))
        ctrl = ttk.Frame(top)
        ctrl.pack(fill=tk.X)
        self.start_btn = ttk.Button(ctrl, text="Start Server", style="Green.TButton", command=self._start_server)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.stop_btn = ttk.Button(ctrl, text="Stop Server", style="Red.TButton", command=self._stop_server, state="disabled")
        self.stop_btn.pack(side=tk.LEFT)

        restart_row = ttk.Frame(top)
        restart_row.pack(fill=tk.X, pady=(4, 0))
        self.auto_restart_var = tk.BooleanVar(value=self.config.get("auto_restart", False))
        ttk.Checkbutton(restart_row, text="Auto-restart on crash",
                        variable=self.auto_restart_var,
                        command=self._on_auto_restart_toggle).pack(side=tk.LEFT)
        ttk.Label(restart_row, text="  Delay:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(12, 2))
        self.restart_delay_var = tk.StringVar(value=str(self.config.get("restart_delay", 10)))
        ttk.Spinbox(restart_row, from_=3, to=60, width=4,
                    textvariable=self.restart_delay_var).pack(side=tk.LEFT)
        ttk.Label(restart_row, text="sec", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 0))

        notif_row = ttk.Frame(top)
        notif_row.pack(fill=tk.X, pady=(4, 0))
        self.notifications_var = tk.BooleanVar(value=self.config.get("notifications_enabled", True))
        ttk.Checkbutton(notif_row, text="Desktop notifications",
                        variable=self.notifications_var,
                        command=self._on_notifications_toggle).pack(side=tk.LEFT)

        players_row = ttk.Frame(top)
        players_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(players_row, text="Online Players:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.players_lbl = ttk.Label(players_row, text="None", style="CardDim.TLabel")
        self.players_lbl.pack(side=tk.LEFT, padx=8)

        btn_row = ttk.Frame(scroll_inner)
        btn_row.pack(fill=tk.X, padx=14, pady=(0, 10))
        ttk.Button(btn_row, text="Save Config", command=self._save_server_config).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Accept EULA", command=self._write_eula).pack(side=tk.LEFT, padx=6)

        props = ttk.Frame(scroll_inner)
        props.pack(fill=tk.X, padx=14, pady=(0, 10))
        col1 = ttk.Frame(props)
        col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        col2 = ttk.Frame(props)
        col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

        def _field(parent, label, key, values=None, width=12):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18, anchor="w").pack(side=tk.LEFT)
            raw = self.config.get(key, "")
            if isinstance(raw, bool):
                val = str(raw).lower()
            else:
                val = str(raw)
            var = tk.StringVar(value=val)
            if values:
                ttk.Combobox(row, textvariable=var, values=values, width=width, state="readonly").pack(side=tk.LEFT, padx=(4, 0))
            else:
                ttk.Entry(row, textvariable=var, width=width).pack(side=tk.LEFT, padx=(4, 0))
            return var

        self._cfg_vars = {}
        self._cfg_vars["server_port"] = _field(col1, "Port:", "server_port")
        self._cfg_vars["max_players"] = _field(col2, "Max Players:", "max_players")
        self._cfg_vars["motd"] = _field(col1, "MOTD:", "motd", width=24)
        self._cfg_vars["gamemode"] = _field(col2, "Gamemode:", "gamemode", values=["survival", "creative", "adventure", "spectator"])
        self._cfg_vars["difficulty"] = _field(col1, "Difficulty:", "difficulty", values=["peaceful", "easy", "normal", "hard"])
        self._cfg_vars["view_distance"] = _field(col2, "View Distance:", "view_distance")
        self._cfg_vars["online_mode"] = _field(col1, "Online Mode:", "online_mode", values=["true", "false"])
        self._cfg_vars["pvp"] = _field(col2, "PvP:", "pvp", values=["true", "false"])
        self._cfg_vars["spawn_protection"] = _field(col1, "Spawn Protection:", "spawn_protection")
        self._cfg_vars["level_seed"] = _field(col2, "Seed:", "level_seed", width=16)
        self._cfg_vars["white_list"] = _field(col1, "Whitelist:", "white_list", values=["true", "false"])
        self._cfg_vars["hardcore"] = _field(col2, "Hardcore:", "hardcore", values=["true", "false"])

        ttk.Separator(scroll_inner, orient="horizontal").pack(fill=tk.X, padx=14, pady=10)
        rp_header = ttk.Frame(scroll_inner)
        rp_header.pack(fill=tk.X, padx=14, pady=(0, 8))
        ttk.Label(rp_header, text="Resource Pack", style="SubHeader.TLabel").pack(anchor="w")

        rp_frame = ttk.Frame(scroll_inner)
        rp_frame.pack(fill=tk.X, padx=14, pady=(0, 10))
        rp_col1 = ttk.Frame(rp_frame)
        rp_col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        rp_col2 = ttk.Frame(rp_frame)
        rp_col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

        self._cfg_vars["resource_pack"] = _field(rp_col1, "Pack URL:", "resource_pack", width=30)
        self._cfg_vars["resource_pack_sha1"] = _field(rp_col2, "SHA1 Hash:", "resource_pack_sha1", width=30)
        self._cfg_vars["resource_pack_prompt"] = _field(rp_col1, "Prompt Message:", "resource_pack_prompt", width=26)
        self._cfg_vars["require_resource_pack"] = _field(rp_col2, "Require Pack:", "require_resource_pack", values=["true", "false"])

        ttk.Separator(scroll_inner, orient="horizontal").pack(fill=tk.X, padx=14, pady=10)
        motd_frame = ttk.Frame(scroll_inner)
        motd_frame.pack(fill=tk.X, padx=14, pady=(0, 10))
        ttk.Label(motd_frame, text="MOTD Editor", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(motd_frame, text="Message of the Day shown in the Minecraft server list. Use &-codes for color (e.g. &aGreen, &cRed, &lBold).",
                  style="Dim.TLabel", wraplength=600).pack(anchor="w", pady=(0, 4))
        motd_row = ttk.Frame(motd_frame)
        motd_row.pack(fill=tk.X)
        self.motd_entry_var = tk.StringVar(value=self.config.get("motd", "A Minecraft Server"))
        self.motd_entry = ttk.Entry(motd_row, textvariable=self.motd_entry_var, width=50)
        self.motd_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.motd_entry_var.trace_add("write", lambda *_: self._update_motd_preview())
        ttk.Button(motd_row, text="Apply MOTD", style="Green.TButton",
                   command=self._apply_motd).pack(side=tk.LEFT)
        self.motd_preview_var = tk.StringVar(value="")
        ttk.Label(motd_row, textvariable=self.motd_preview_var,
                  style="CardDim.TLabel", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=8)
        ttk.Label(motd_frame, text="Colors: &0=Black &1=DarkBlue &2=DarkGreen &3=DarkAqua &4=DarkRed &5=DarkPurple "
                  "&6=Gold &7=Gray &8=DarkGray &9=Blue &a=Green &b=Aqua &c=Red &d=LightPurple &e=Yellow &f=White "
                  "&l=Bold &n=Underline &o=Italic &r=Reset",
                  style="Dim.TLabel", wraplength=600).pack(anchor="w", pady=(4, 0))
        self._update_motd_preview()

        ttk.Separator(scroll_inner, orient="horizontal").pack(fill=tk.X, padx=14, pady=10)
        tools = ttk.Frame(scroll_inner)
        tools.pack(fill=tk.X, padx=14, pady=(0, 10))

        backup_frame = ttk.Frame(tools)
        backup_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(backup_frame, text="World Backup", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        bk_row = ttk.Frame(backup_frame)
        bk_row.pack(fill=tk.X)
        self.auto_backup_var = tk.BooleanVar(value=self.config.get("auto_backup", True))
        ttk.Checkbutton(bk_row, text="Auto-backup before start",
                        variable=self.auto_backup_var).pack(side=tk.LEFT)
        ttk.Button(bk_row, text="Backup Now", command=self._manual_backup_world).pack(side=tk.LEFT, padx=8)
        ttk.Button(bk_row, text="Restore Latest Backup", command=self._restore_world).pack(side=tk.LEFT)
        ttk.Button(bk_row, text="Download World", style="Blue.TButton",
                   command=self._download_world).pack(side=tk.LEFT, padx=8)
        self.world_download_status = ttk.Label(bk_row, text="", style="Dim.TLabel")
        self.world_download_status.pack(side=tk.LEFT, padx=8)
        self.backup_status = ttk.Label(bk_row, text="", style="Dim.TLabel")
        self.backup_status.pack(side=tk.LEFT, padx=8)

        rot_row = ttk.Frame(backup_frame)
        rot_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(rot_row, text="Rotation:", style="Dim.TLabel").pack(side=tk.LEFT)
        ttk.Label(rot_row, text="Max age:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(8, 2))
        self.backup_max_age_var = tk.StringVar(value=str(self.config.get("backup_max_age_days", 0)))
        ttk.Spinbox(rot_row, from_=0, to=365, width=4,
                    textvariable=self.backup_max_age_var).pack(side=tk.LEFT)
        ttk.Label(rot_row, text="days (0=off)", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 8))
        ttk.Label(rot_row, text="Max count:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.backup_max_count_var = tk.StringVar(value=str(self.config.get("backup_max_count", 0)))
        ttk.Spinbox(rot_row, from_=0, to=100, width=4,
                    textvariable=self.backup_max_count_var).pack(side=tk.LEFT)
        ttk.Label(rot_row, text=" (0=off)", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 0))

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        update_frame = ttk.Frame(tools)
        update_frame.pack(fill=tk.X)
        ttk.Label(update_frame, text="Server Update", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        upd_row = ttk.Frame(update_frame)
        upd_row.pack(fill=tk.X)
        ttk.Button(upd_row, text="Update to Latest Build", style="Blue.TButton",
                   command=self._auto_update_server).pack(side=tk.LEFT)
        self.update_status = ttk.Label(upd_row, text="", style="Dim.TLabel")
        self.update_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        sched_frame = ttk.Frame(tools)
        sched_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(sched_frame, text="Scheduled Restart", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        sched_row = ttk.Frame(sched_frame)
        sched_row.pack(fill=tk.X)
        self.sched_restart_var = tk.BooleanVar(value=self.config.get("scheduled_restart", False))
        ttk.Checkbutton(sched_row, text="Enable scheduled restart",
                        variable=self.sched_restart_var,
                        command=self._on_sched_restart_toggle).pack(side=tk.LEFT)
        ttk.Label(sched_row, text="  Every:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(12, 2))
        self.sched_hours_var = tk.StringVar(value=str(self.config.get("scheduled_restart_hours", 24)))
        ttk.Spinbox(sched_row, from_=1, to=168, width=4,
                    textvariable=self.sched_hours_var).pack(side=tk.LEFT)
        ttk.Label(sched_row, text="hours", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 0))
        self.sched_status = ttk.Label(sched_row, text="", style="Dim.TLabel")
        self.sched_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        pbackup_frame = ttk.Frame(tools)
        pbackup_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(pbackup_frame, text="Periodic Backup", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        pbackup_row = ttk.Frame(pbackup_frame)
        pbackup_row.pack(fill=tk.X)
        self.periodic_backup_var = tk.BooleanVar(value=self.config.get("periodic_backup", False))
        ttk.Checkbutton(pbackup_row, text="Enable periodic backups",
                        variable=self.periodic_backup_var,
                        command=self._on_periodic_backup_toggle).pack(side=tk.LEFT)
        ttk.Label(pbackup_row, text="  Every:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(12, 2))
        self.backup_interval_var = tk.StringVar(value=str(self.config.get("periodic_backup_interval", 30)))
        ttk.Spinbox(pbackup_row, from_=5, to=360, width=4,
                    textvariable=self.backup_interval_var).pack(side=tk.LEFT)
        ttk.Label(pbackup_row, text="min", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 0))
        self.pbackup_status = ttk.Label(pbackup_row, text="", style="Dim.TLabel")
        self.pbackup_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        self._build_cloud_backup_section(tools)

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        sched_tasks_frame = ttk.Frame(tools)
        sched_tasks_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(sched_tasks_frame, text="Scheduled Tasks", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(sched_tasks_frame, text="Schedule recurring commands (e.g. /save-all, /say Hello).",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 4))

        task_list_frame = ttk.Frame(sched_tasks_frame)
        task_list_frame.pack(fill=tk.X, pady=(0, 6))
        task_cols = ("Command", "Interval", "Enabled")
        self.task_tree = ttk.Treeview(task_list_frame, columns=task_cols, show="headings", selectmode="browse", height=4)
        self.task_tree.heading("Command", text="Command")
        self.task_tree.heading("Interval", text="Interval (min)")
        self.task_tree.heading("Enabled", text="Enabled")
        self.task_tree.column("Command", width=250)
        self.task_tree.column("Interval", width=120, anchor="e")
        self.task_tree.column("Enabled", width=80, anchor="center")
        task_scroll = ttk.Scrollbar(task_list_frame, orient="vertical", command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=task_scroll.set)
        self.task_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        task_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.task_tree.tag_configure("odd", background=BG_ENTRY)
        self.task_tree.tag_configure("even", background=BG_MID)

        task_add_row = ttk.Frame(sched_tasks_frame)
        task_add_row.pack(fill=tk.X, pady=(0, 4))
        self.task_cmd_var = tk.StringVar()
        ttk.Entry(task_add_row, textvariable=self.task_cmd_var, width=30).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(task_add_row, text="every", style="Dim.TLabel").pack(side=tk.LEFT, padx=(4, 2))
        self.task_interval_var = tk.StringVar(value="30")
        ttk.Spinbox(task_add_row, from_=1, to=1440, width=5, textvariable=self.task_interval_var).pack(side=tk.LEFT)
        ttk.Label(task_add_row, text="min", style="Dim.TLabel").pack(side=tk.LEFT, padx=(2, 8))
        ttk.Button(task_add_row, text="Add Task", style="Green.TButton",
                   command=self._add_scheduled_task).pack(side=tk.LEFT)
        ttk.Button(task_add_row, text="Remove Selected",
                   command=self._remove_scheduled_task).pack(side=tk.LEFT, padx=4)
        ttk.Button(task_add_row, text="Run Now",
                   command=self._run_selected_task).pack(side=tk.LEFT, padx=4)

        ttk.Separator(tools, orient="horizontal").pack(fill=tk.X, pady=6)
        migrate_frame = ttk.Frame(tools)
        migrate_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(migrate_frame, text="Migrate Server", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        mig_row = ttk.Frame(migrate_frame)
        mig_row.pack(fill=tk.X)
        self.migrate_btn = ttk.Button(mig_row, text="Package Server", style="Blue.TButton",
                                       command=self._migrate_server)
        self.migrate_btn.pack(side=tk.LEFT)
        self.migrate_import_btn = ttk.Button(mig_row, text="Import Server",
                                              command=self._import_server)
        self.migrate_import_btn.pack(side=tk.LEFT, padx=8)
        self.migrate_status = ttk.Label(mig_row, text="", style="Dim.TLabel")
        self.migrate_status.pack(side=tk.LEFT, padx=8)

    # ── Console Tab ──────────────────────────────────────────
    def _build_console_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Console  ")

        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, padx=14, pady=(12, 0))
        ttk.Label(ctrl, text="Command:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.cmd_entry = ttk.Entry(ctrl, width=60)
        self.cmd_entry.pack(side=tk.LEFT, padx=(6, 4), fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", lambda e: self._send_command())
        ttk.Button(ctrl, text="Send", style="Blue.TButton", command=self._send_command).pack(side=tk.LEFT)

        self.console = scrolledtext.ScrolledText(
            tab, wrap=tk.WORD, bg=BG_ENTRY, fg=FG_MAIN, insertbackground=FG_ACCENT,
            font=("Cascadia Code", 10), relief=tk.FLAT, borderwidth=0, state="disabled",
            selectbackground=BG_HOVER, selectforeground=FG_BRIGHT,
            padx=10, pady=6, spacing1=1
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 0))
        self.console.tag_config("info", foreground=FG_MAIN)
        self.console.tag_config("warn", foreground=FG_YELLOW)
        self.console.tag_config("error", foreground=FG_RED)
        self.console.tag_config("success", foreground=FG_GREEN)
        self.console.tag_config("cmd", foreground=FG_ACCENT)

        ttk.Separator(tab, orient="horizontal").pack(fill=tk.X, padx=14, pady=4)

        chat_label = ttk.Frame(tab)
        chat_label.pack(fill=tk.X, padx=14)
        ttk.Label(chat_label, text="Player Chat", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.chat_panel = scrolledtext.ScrolledText(
            tab, wrap=tk.WORD, bg="#12122a", fg=FG_MAIN, insertbackground=FG_ACCENT,
            font=("Cascadia Code", 10), relief=tk.FLAT, borderwidth=0, state="disabled",
            selectbackground=BG_HOVER, selectforeground=FG_BRIGHT,
            padx=10, pady=6, spacing1=1, height=8
        )
        self.chat_panel.pack(fill=tk.BOTH, expand=False, padx=14, pady=(2, 10))
        self.chat_panel.tag_config("chat_player", foreground=FG_ACCENT, font=("Cascadia Code", 10, "bold"))
        self.chat_panel.tag_config("chat_msg", foreground=FG_MAIN)
        self.chat_panel.tag_config("chat_server", foreground=FG_YELLOW)

        clear_row = ttk.Frame(tab)
        clear_row.pack(fill=tk.X, padx=14, pady=(0, 10))
        ttk.Button(clear_row, text="Clear Console", command=self._clear_console).pack(side=tk.LEFT)
        ttk.Button(clear_row, text="Clear Chat", command=self._clear_chat).pack(side=tk.LEFT, padx=8)
        ttk.Button(clear_row, text="Analyze Crash Reports", command=self._analyze_crash_reports).pack(side=tk.LEFT, padx=8)
        self.log_export_var = tk.BooleanVar(value=self.config.get("log_export", False))
        ttk.Checkbutton(clear_row, text="Export logs to file",
                        variable=self.log_export_var,
                        command=self._on_log_export_toggle).pack(side=tk.LEFT, padx=12)
        self.log_export_status = ttk.Label(clear_row, text="", style="Dim.TLabel")
        self.log_export_status.pack(side=tk.LEFT, padx=4)

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

    def _clear_chat(self):
        self.chat_panel.configure(state="normal")
        self.chat_panel.delete("1.0", tk.END)
        self.chat_panel.configure(state="disabled")

    def _parse_chat_message(self, line):
        m = re.search(r'<(\w+)>\s*(.*)', line)
        if m:
            return m.group(1), m.group(2)
        m2 = re.search(r'\[Server\]\s*<(\w+)>\s*(.*)', line)
        if m2:
            return m2.group(1), m2.group(2)
        return None, None

    def _display_chat(self, player, message):
        def _do():
            self.chat_panel.configure(state="normal")
            ts = time.strftime("%H:%M:%S")
            self.chat_panel.insert(tk.END, f"[{ts}] ", "chat_server")
            self.chat_panel.insert(tk.END, f"<{player}> ", "chat_player")
            self.chat_panel.insert(tk.END, f"{message}\n", "chat_msg")
            self.chat_panel.see(tk.END)
            self.chat_panel.configure(state="disabled")
        self.root.after(0, _do)

    # ── Plugins Tab ──────────────────────────────────────────
    def _build_plugins_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Plugins  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Plugin Manager (Modrinth)", style="SubHeader.TLabel").pack(anchor="w")
        ttk.Label(frm, text="Search and install plugins for Paper/Fabric servers.",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 8))

        search_row = ttk.Frame(frm)
        search_row.pack(fill=tk.X, pady=(0, 8))
        self.plugin_search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.plugin_search_var, width=40).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(search_row, text="Search", style="Blue.TButton",
                   command=self._search_plugins).pack(side=tk.LEFT)
        self.plugin_search_btn = search_row.winfo_children()[-1]
        self.plugin_status = ttk.Label(search_row, text="", style="Dim.TLabel")
        self.plugin_status.pack(side=tk.LEFT, padx=10)

        list_frame = ttk.Frame(frm)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("Name", "Downloads", "Description")
        self.plugin_tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.plugin_tree.heading("Name", text="Name")
        self.plugin_tree.heading("Downloads", text="Downloads")
        self.plugin_tree.heading("Description", text="Description")
        self.plugin_tree.column("Name", width=180, minwidth=120)
        self.plugin_tree.column("Downloads", width=90, minwidth=70, anchor="e")
        self.plugin_tree.column("Description", width=400, minwidth=200)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.plugin_tree.yview)
        self.plugin_tree.configure(yscrollcommand=scrollbar.set)
        self.plugin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))

        self.plugin_tree.tag_configure("odd", background=BG_ENTRY)
        self.plugin_tree.tag_configure("even", background=BG_MID)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Install Selected", style="Green.TButton",
                   command=self._install_plugin).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Open Plugins Folder",
                   command=self._open_plugins_folder).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="Check for Updates", style="Blue.TButton",
                   command=self._check_plugin_updates).pack(side=tk.LEFT, padx=8)
        self.plugin_install_status = ttk.Label(btn_row, text="", style="Dim.TLabel")
        self.plugin_install_status.pack(side=tk.LEFT, padx=8)

        self._plugin_results = []

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        update_frame = ttk.Frame(frm)
        update_frame.pack(fill=tk.X)
        ttk.Label(update_frame, text="Installed Plugins", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))

        self.plugin_update_status = ttk.Label(update_frame, text="Click 'Check for Updates' to scan installed plugins",
                                              style="Dim.TLabel")
        self.plugin_update_status.pack(anchor="w", pady=(0, 4))

        plugin_update_cols = ("Plugin", "Installed", "Latest", "Status")
        self.plugin_update_tree = ttk.Treeview(update_frame, columns=plugin_update_cols, show="headings",
                                               selectmode="browse", height=4)
        self.plugin_update_tree.heading("Plugin", text="Plugin")
        self.plugin_update_tree.heading("Installed", text="Installed")
        self.plugin_update_tree.heading("Latest", text="Latest")
        self.plugin_update_tree.heading("Status", text="Status")
        self.plugin_update_tree.column("Plugin", width=180)
        self.plugin_update_tree.column("Installed", width=100)
        self.plugin_update_tree.column("Latest", width=100)
        self.plugin_update_tree.column("Status", width=120)
        self.plugin_update_tree.tag_configure("up_to_date", foreground=FG_GREEN)
        self.plugin_update_tree.tag_configure("has_update", foreground=FG_YELLOW)
        self.plugin_update_tree.tag_configure("error", foreground=FG_RED)
        self.plugin_update_tree.tag_configure("odd", background=BG_ENTRY)
        self.plugin_update_tree.tag_configure("even", background=BG_MID)

        plugin_update_scroll = ttk.Scrollbar(update_frame, orient="vertical", command=self.plugin_update_tree.yview)
        self.plugin_update_tree.configure(yscrollcommand=plugin_update_scroll.set)
        self.plugin_update_tree.pack(fill=tk.X)
        plugin_update_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _search_plugins(self):
        query = self.plugin_search_var.get().strip()
        if not query:
            return
        mc_ver = self.config.get("mc_version", "")
        stype = self.config.get("server_type", "paper")
        self.plugin_status.configure(text="Searching...")
        self.plugin_search_btn.configure(state="disabled")

        def _do():
            facets = [["project_type:plugin"]]
            if stype == "paper":
                facets.append(["categories:paper"])
            elif stype == "fabric":
                facets.append(["categories:fabric"])
            facets_str = json.dumps(facets)
            url = f"{MODRINTH_API}/search?facets={urllib.parse.quote(facets_str)}&query={urllib.parse.quote(query)}&limit=20"
            if mc_ver:
                url += f"&game_versions={urllib.parse.quote(f'[{json.dumps(mc_ver)}]')}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                hits = data.get("hits", [])
                self._plugin_results = hits
                self.root.after(0, lambda: self._populate_plugin_results(hits))
            except Exception as e:
                self.root.after(0, lambda: self.plugin_status.configure(text=f"Search failed: {e}"))
            self.root.after(0, lambda: self.plugin_search_btn.configure(state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    def _populate_plugin_results(self, hits):
        for item in self.plugin_tree.get_children():
            self.plugin_tree.delete(item)
        if not hits:
            self.plugin_status.configure(text="No results found")
            return
        for i, h in enumerate(hits):
            name = h.get("title", "?")
            dl = h.get("downloads", 0)
            desc = (h.get("description") or "")[:80]
            tag = "even" if i % 2 == 0 else "odd"
            self.plugin_tree.insert("", "end", values=(name, f"{dl:,}", desc), tags=(tag,))
        self.plugin_status.configure(text=f"{len(hits)} results")

    def _install_plugin(self):
        sel = self.plugin_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a plugin to install.")
            return
        idx = self.plugin_tree.index(sel[0])
        if idx >= len(self._plugin_results):
            return
        plugin = self._plugin_results[idx]
        project_id = plugin.get("project_id") or plugin.get("slug")
        plugin_name = plugin.get("title", "plugin")
        mc_ver = self.config.get("mc_version", "")
        stype = self.config.get("server_type", "paper")
        loaders = ["paper"] if stype == "paper" else ["fabric"] if stype == "fabric" else ["forge", "neoforge"]

        self.plugin_install_status.configure(text=f"Installing {plugin_name}...")

        def _do():
            url = f"{MODRINTH_API}/project/{project_id}/version"
            params = []
            if mc_ver:
                params.append(f"game_versions=[{json.dumps(mc_ver)}]")
            if loaders:
                params.append(f"loaders=[{json.dumps(loaders[0])}]")
            if params:
                url += "?" + "&".join(params)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    versions = json.loads(resp.read())
                if not versions:
                    self.root.after(0, lambda: self.plugin_install_status.configure(text="No compatible version found"))
                    return
                ver = versions[0]
                files = ver.get("files", [])
                if not files:
                    self.root.after(0, lambda: self.plugin_install_status.configure(text="No download file found"))
                    return
                dl_url = files[0].get("url")
                fname = files[0].get("filename", "plugin.jar")
                plugins_dir = self._server_dir() / "plugins"
                plugins_dir.mkdir(parents=True, exist_ok=True)
                dest = str(plugins_dir / fname)
                ok = download_file(dl_url, dest)
                if ok:
                    self.root.after(0, lambda: self.plugin_install_status.configure(text=f"Installed {plugin_name}"))
                    self._log(f"Plugin installed: {plugin_name}", "success")
                else:
                    self.root.after(0, lambda: self.plugin_install_status.configure(text="Download failed"))
            except Exception as e:
                self.root.after(0, lambda: self.plugin_install_status.configure(text=f"Error: {e}"))

        threading.Thread(target=_do, daemon=True).start()

    def _open_plugins_folder(self):
        plugins_dir = self._server_dir() / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(plugins_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(plugins_dir)])
        else:
            subprocess.run(["xdg-open", str(plugins_dir)])

    # ── Mods Tab ──────────────────────────────────────────────
    def _build_mods_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Mods  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        self.mods_info_label = ttk.Label(frm, text="Mod Manager (Modrinth)", style="SubHeader.TLabel")
        self.mods_info_label.pack(anchor="w")
        self.mods_desc_label = ttk.Label(frm, text="Search and install mods for Fabric/Forge servers.",
                                         style="Dim.TLabel")
        self.mods_desc_label.pack(anchor="w", pady=(0, 8))

        self.mods_not_supported_label = ttk.Label(
            frm, text="Mod browser is only available for Fabric and Forge server types.",
            style="Dim.TLabel")

        self.mods_search_row = ttk.Frame(frm)
        self.mod_search_var = tk.StringVar()
        ttk.Entry(self.mods_search_row, textvariable=self.mod_search_var, width=40).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(self.mods_search_row, text="Search", style="Blue.TButton",
                   command=self._search_mods).pack(side=tk.LEFT)
        self.mod_search_btn = self.mods_search_row.winfo_children()[-1]
        self.mod_status = ttk.Label(self.mods_search_row, text="", style="Dim.TLabel")
        self.mod_status.pack(side=tk.LEFT, padx=10)

        self.mods_list_frame = ttk.Frame(frm)
        self.mods_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("Name", "Downloads", "Description")
        self.mod_tree = ttk.Treeview(self.mods_list_frame, columns=cols, show="headings", selectmode="browse")
        self.mod_tree.heading("Name", text="Name")
        self.mod_tree.heading("Downloads", text="Downloads")
        self.mod_tree.heading("Description", text="Description")
        self.mod_tree.column("Name", width=180, minwidth=120)
        self.mod_tree.column("Downloads", width=90, minwidth=70, anchor="e")
        self.mod_tree.column("Description", width=400, minwidth=200)
        scrollbar = ttk.Scrollbar(self.mods_list_frame, orient="vertical", command=self.mod_tree.yview)
        self.mod_tree.configure(yscrollcommand=scrollbar.set)
        self.mod_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))

        self.mod_tree.tag_configure("odd", background=BG_ENTRY)
        self.mod_tree.tag_configure("even", background=BG_MID)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Install Selected", style="Green.TButton",
                   command=self._install_mod).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Open Mods Folder",
                   command=self._open_mods_folder).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="Check for Updates", style="Blue.TButton",
                   command=self._check_mod_updates).pack(side=tk.LEFT, padx=8)
        self.mod_install_status = ttk.Label(btn_row, text="", style="Dim.TLabel")
        self.mod_install_status.pack(side=tk.LEFT, padx=8)

        self._mod_results = []

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        mod_update_frame = ttk.Frame(frm)
        mod_update_frame.pack(fill=tk.X)
        ttk.Label(mod_update_frame, text="Installed Mods", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))

        self.mod_update_status = ttk.Label(mod_update_frame, text="Click 'Check for Updates' to scan installed mods",
                                           style="Dim.TLabel")
        self.mod_update_status.pack(anchor="w", pady=(0, 4))

        mod_update_cols = ("Mod", "Installed", "Latest", "Status")
        self.mod_update_tree = ttk.Treeview(mod_update_frame, columns=mod_update_cols, show="headings",
                                            selectmode="browse", height=4)
        self.mod_update_tree.heading("Mod", text="Mod")
        self.mod_update_tree.heading("Installed", text="Installed")
        self.mod_update_tree.heading("Latest", text="Latest")
        self.mod_update_tree.heading("Status", text="Status")
        self.mod_update_tree.column("Mod", width=180)
        self.mod_update_tree.column("Installed", width=100)
        self.mod_update_tree.column("Latest", width=100)
        self.mod_update_tree.column("Status", width=120)
        self.mod_update_tree.tag_configure("up_to_date", foreground=FG_GREEN)
        self.mod_update_tree.tag_configure("has_update", foreground=FG_YELLOW)
        self.mod_update_tree.tag_configure("error", foreground=FG_RED)
        self.mod_update_tree.tag_configure("odd", background=BG_ENTRY)
        self.mod_update_tree.tag_configure("even", background=BG_MID)

        mod_update_scroll = ttk.Scrollbar(mod_update_frame, orient="vertical", command=self.mod_update_tree.yview)
        self.mod_update_tree.configure(yscrollcommand=mod_update_scroll.set)
        self.mod_update_tree.pack(fill=tk.X)
        mod_update_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _search_mods(self):
        stype = self.config.get("server_type", "paper")
        if stype not in ("fabric", "forge"):
            self.mod_not_supported_ui()
            return
        query = self.mod_search_var.get().strip()
        if not query:
            return
        mc_ver = self.config.get("mc_version", "")
        self.mod_status.configure(text="Searching...")
        self.mod_search_btn.configure(state="disabled")

        def _do():
            facets = [["project_type:mod"]]
            if stype == "fabric":
                facets.append(["categories:fabric"])
            elif stype == "forge":
                facets.append(["categories:forge"])
            facets_str = json.dumps(facets)
            url = f"{MODRINTH_API}/search?facets={urllib.parse.quote(facets_str)}&query={urllib.parse.quote(query)}&limit=20"
            if mc_ver:
                url += f"&game_versions={urllib.parse.quote(f'[{json.dumps(mc_ver)}]')}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                hits = data.get("hits", [])
                self._mod_results = hits
                self.root.after(0, lambda: self._populate_mod_results(hits))
            except Exception as e:
                self.root.after(0, lambda: self.mod_status.configure(text=f"Search failed: {e}"))
            self.root.after(0, lambda: self.mod_search_btn.configure(state="normal"))

        threading.Thread(target=_do, daemon=True).start()

    def _populate_mod_results(self, hits):
        for item in self.mod_tree.get_children():
            self.mod_tree.delete(item)
        if not hits:
            self.mod_status.configure(text="No results found")
            return
        for i, h in enumerate(hits):
            name = h.get("title", "?")
            dl = h.get("downloads", 0)
            desc = (h.get("description") or "")[:80]
            tag = "even" if i % 2 == 0 else "odd"
            self.mod_tree.insert("", "end", values=(name, f"{dl:,}", desc), tags=(tag,))
        self.mod_status.configure(text=f"{len(hits)} results")

    def _install_mod(self):
        sel = self.mod_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a mod to install.")
            return
        idx = self.mod_tree.index(sel[0])
        if idx >= len(self._mod_results):
            return
        mod = self._mod_results[idx]
        project_id = mod.get("project_id") or mod.get("slug")
        mod_name = mod.get("title", "mod")
        mc_ver = self.config.get("mc_version", "")
        stype = self.config.get("server_type", "fabric")
        loaders = ["fabric"] if stype == "fabric" else ["forge", "neoforge"]

        self.mod_install_status.configure(text=f"Installing {mod_name}...")

        def _do():
            url = f"{MODRINTH_API}/project/{project_id}/version"
            params = []
            if mc_ver:
                params.append(f"game_versions=[{json.dumps(mc_ver)}]")
            if loaders:
                params.append(f"loaders=[{json.dumps(loaders[0])}]")
            if params:
                url += "?" + "&".join(params)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    versions = json.loads(resp.read())
                if not versions:
                    self.root.after(0, lambda: self.mod_install_status.configure(text="No compatible version found"))
                    return
                ver = versions[0]
                files = ver.get("files", [])
                if not files:
                    self.root.after(0, lambda: self.mod_install_status.configure(text="No download file found"))
                    return
                dl_url = files[0].get("url")
                fname = files[0].get("filename", "mod.jar")
                mods_dir = self._server_dir() / "mods"
                mods_dir.mkdir(parents=True, exist_ok=True)
                dest = str(mods_dir / fname)
                ok = download_file(dl_url, dest)
                if ok:
                    self.root.after(0, lambda: self.mod_install_status.configure(text=f"Installed {mod_name}"))
                    self._log(f"Mod installed: {mod_name}", "success")
                else:
                    self.root.after(0, lambda: self.mod_install_status.configure(text="Download failed"))
            except Exception as e:
                self.root.after(0, lambda: self.mod_install_status.configure(text=f"Error: {e}"))

        threading.Thread(target=_do, daemon=True).start()

    def _open_mods_folder(self):
        mods_dir = self._server_dir() / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(mods_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(mods_dir)])
        else:
            subprocess.run(["xdg-open", str(mods_dir)])

    def mod_not_supported_ui(self):
        self.mod_status.configure(text="Mod browser requires Fabric or Forge server type")

    # ── Players Tab (Whitelist / OP) ────────────────────────
    def _build_players_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Players  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Whitelist & Operator Manager", style="SubHeader.TLabel").pack(anchor="w")
        ttk.Label(frm, text="Manage whitelisted players and server operators.",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 8))

        add_row = ttk.Frame(frm)
        add_row.pack(fill=tk.X, pady=(0, 8))
        self.wl_player_var = tk.StringVar()
        ttk.Entry(add_row, textvariable=self.wl_player_var, width=22).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(add_row, text="+ Whitelist", command=self._add_whitelist_player).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_row, text="- Whitelist", command=self._remove_whitelist_player).pack(side=tk.LEFT, padx=3)
        ttk.Separator(add_row, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(add_row, text="+ OP", command=self._add_op_player).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_row, text="- OP", command=self._remove_op_player).pack(side=tk.LEFT, padx=3)
        self.wl_status = ttk.Label(add_row, text="", style="Dim.TLabel")
        self.wl_status.pack(side=tk.LEFT, padx=10)

        lists = ttk.Frame(frm)
        lists.pack(fill=tk.BOTH, expand=True)

        wl_frame = ttk.Frame(lists)
        wl_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        ttk.Label(wl_frame, text="Whitelisted Players", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        wl_list_frame = ttk.Frame(wl_frame)
        wl_list_frame.pack(fill=tk.BOTH, expand=True)
        self.wl_tree = ttk.Treeview(wl_list_frame, columns=("Name",), show="headings", selectmode="browse")
        self.wl_tree.heading("Name", text="Player Name")
        self.wl_tree.column("Name", width=200)
        wl_scroll = ttk.Scrollbar(wl_list_frame, orient="vertical", command=self.wl_tree.yview)
        self.wl_tree.configure(yscrollcommand=wl_scroll.set)
        self.wl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        wl_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.wl_tree.tag_configure("odd", background=BG_ENTRY)
        self.wl_tree.tag_configure("even", background=BG_MID)

        op_frame = ttk.Frame(lists)
        op_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        ttk.Label(op_frame, text="Operators", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        op_list_frame = ttk.Frame(op_frame)
        op_list_frame.pack(fill=tk.BOTH, expand=True)
        self.op_tree = ttk.Treeview(op_list_frame, columns=("Name", "Level"), show="headings", selectmode="browse")
        self.op_tree.heading("Name", text="Player Name")
        self.op_tree.heading("Level", text="Level")
        self.op_tree.column("Name", width=160)
        self.op_tree.column("Level", width=60, anchor="center")
        op_scroll = ttk.Scrollbar(op_list_frame, orient="vertical", command=self.op_tree.yview)
        self.op_tree.configure(yscrollcommand=op_scroll.set)
        self.op_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        op_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.op_tree.tag_configure("odd", background=BG_ENTRY)
        self.op_tree.tag_configure("even", background=BG_MID)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=10)
        stats_frame = ttk.Frame(frm)
        stats_frame.pack(fill=tk.X)
        ttk.Label(stats_frame, text="Player Statistics", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(stats_frame, text="Tracks join count, playtime, and sessions for each player.",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 4))
        self.player_stats_status = ttk.Label(stats_frame, text="Click 'Refresh Stats' to load data",
                                             style="Dim.TLabel")
        self.player_stats_status.pack(anchor="w", pady=(0, 4))

        stats_cols = ("Player", "Joins", "Playtime", "Last Seen")
        self.player_stats_tree = ttk.Treeview(stats_frame, columns=stats_cols, show="headings",
                                              selectmode="browse", height=6)
        self.player_stats_tree.heading("Player", text="Player")
        self.player_stats_tree.heading("Joins", text="Joins")
        self.player_stats_tree.heading("Playtime", text="Playtime")
        self.player_stats_tree.heading("Last Seen", text="Last Seen")
        self.player_stats_tree.column("Player", width=150)
        self.player_stats_tree.column("Joins", width=80, anchor="e")
        self.player_stats_tree.column("Playtime", width=120)
        self.player_stats_tree.column("Last Seen", width=160)
        self.player_stats_tree.tag_configure("odd", background=BG_ENTRY)
        self.player_stats_tree.tag_configure("even", background=BG_MID)
        stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.player_stats_tree.yview)
        self.player_stats_tree.configure(yscrollcommand=stats_scroll.set)
        self.player_stats_tree.pack(fill=tk.X)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        stats_btn_row = ttk.Frame(stats_frame)
        stats_btn_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(stats_btn_row, text="Refresh Stats", command=self._refresh_player_stats).pack(side=tk.LEFT)
        ttk.Button(stats_btn_row, text="Clear Stats", command=self._clear_player_stats).pack(side=tk.LEFT, padx=8)

        self._load_player_stats()

    def _refresh_players(self):
        wl_file = self._server_dir() / "whitelist.json"
        wl_names = []
        if wl_file.exists():
            try:
                with open(wl_file) as f:
                    wl_data = json.load(f)
                wl_names = [e.get("name", "") for e in wl_data if e.get("name")]
            except Exception:
                pass
        for item in self.wl_tree.get_children():
            self.wl_tree.delete(item)
        for i, name in enumerate(wl_names):
            tag = "even" if i % 2 == 0 else "odd"
            self.wl_tree.insert("", "end", values=(name,), tags=(tag,))

        ops_file = self._server_dir() / "ops.json"
        ops_entries = []
        if ops_file.exists():
            try:
                with open(ops_file) as f:
                    ops_data = json.load(f)
                ops_entries = [(e.get("name", ""), e.get("level", 4)) for e in ops_data if e.get("name")]
            except Exception:
                pass
        for item in self.op_tree.get_children():
            self.op_tree.delete(item)
        for i, (name, level) in enumerate(ops_entries):
            tag = "even" if i % 2 == 0 else "odd"
            self.op_tree.insert("", "end", values=(name, level), tags=(tag,))

    # ── Bans Tab ────────────────────────────────────────────
    def _build_bans_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Bans  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Ban Manager", style="SubHeader.TLabel").pack(anchor="w")
        ttk.Label(frm, text="Manage player bans and IP bans.",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 8))

        add_row = ttk.Frame(frm)
        add_row.pack(fill=tk.X, pady=(0, 8))
        self.ban_player_var = tk.StringVar()
        ttk.Entry(add_row, textvariable=self.ban_player_var, width=22).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(add_row, text="Ban Player", style="Red.TButton",
                   command=self._ban_player).pack(side=tk.LEFT, padx=3)
        ttk.Button(add_row, text="Unban Player",
                   command=self._unban_player).pack(side=tk.LEFT, padx=3)
        self.ban_status = ttk.Label(add_row, text="", style="Dim.TLabel")
        self.ban_status.pack(side=tk.LEFT, padx=10)

        ip_row = ttk.Frame(frm)
        ip_row.pack(fill=tk.X, pady=(0, 10))
        self.ban_ip_var = tk.StringVar()
        ttk.Label(ip_row, text="IP:", style="Dim.TLabel").pack(side=tk.LEFT)
        ttk.Entry(ip_row, textvariable=self.ban_ip_var, width=18).pack(side=tk.LEFT, padx=(4, 6))
        ttk.Button(ip_row, text="Ban IP", style="Red.TButton",
                   command=self._ban_ip).pack(side=tk.LEFT, padx=3)
        ttk.Button(ip_row, text="Unban IP",
                   command=self._unban_ip).pack(side=tk.LEFT, padx=3)
        self.ban_ip_status = ttk.Label(ip_row, text="", style="Dim.TLabel")
        self.ban_ip_status.pack(side=tk.LEFT, padx=10)

        lists = ttk.Frame(frm)
        lists.pack(fill=tk.BOTH, expand=True)

        pban_frame = ttk.Frame(lists)
        pban_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        ttk.Label(pban_frame, text="Banned Players", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        pban_list_frame = ttk.Frame(pban_frame)
        pban_list_frame.pack(fill=tk.BOTH, expand=True)
        self.pban_tree = ttk.Treeview(pban_list_frame, columns=("Name", "Reason", "Date"),
                                       show="headings", selectmode="browse")
        self.pban_tree.heading("Name", text="Player")
        self.pban_tree.heading("Reason", text="Reason")
        self.pban_tree.heading("Date", text="Date")
        self.pban_tree.column("Name", width=140)
        self.pban_tree.column("Reason", width=180)
        self.pban_tree.column("Date", width=120)
        pban_scroll = ttk.Scrollbar(pban_list_frame, orient="vertical", command=self.pban_tree.yview)
        self.pban_tree.configure(yscrollcommand=pban_scroll.set)
        self.pban_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pban_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.pban_tree.tag_configure("odd", background=BG_ENTRY)
        self.pban_tree.tag_configure("even", background=BG_MID)

        iban_frame = ttk.Frame(lists)
        iban_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        ttk.Label(iban_frame, text="Banned IPs", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        iban_list_frame = ttk.Frame(iban_frame)
        iban_list_frame.pack(fill=tk.BOTH, expand=True)
        self.iban_tree = ttk.Treeview(iban_list_frame, columns=("IP", "Reason", "Date"),
                                       show="headings", selectmode="browse")
        self.iban_tree.heading("IP", text="IP Address")
        self.iban_tree.heading("Reason", text="Reason")
        self.iban_tree.heading("Date", text="Date")
        self.iban_tree.column("IP", width=140)
        self.iban_tree.column("Reason", width=180)
        self.iban_tree.column("Date", width=120)
        iban_scroll = ttk.Scrollbar(iban_list_frame, orient="vertical", command=self.iban_tree.yview)
        self.iban_tree.configure(yscrollcommand=iban_scroll.set)
        self.iban_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        iban_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0))
        self.iban_tree.tag_configure("odd", background=BG_ENTRY)
        self.iban_tree.tag_configure("even", background=BG_MID)

    def _refresh_bans(self):
        bans_file = self._server_dir() / "bans.json"
        pban_entries = []
        if bans_file.exists():
            try:
                with open(bans_file) as f:
                    bans_data = json.load(f)
                pban_entries = [(e.get("name", ""), e.get("reason", ""), e.get("created", ""))
                                for e in bans_data if e.get("name")]
            except Exception:
                pass
        for item in self.pban_tree.get_children():
            self.pban_tree.delete(item)
        for i, (name, reason, date) in enumerate(pban_entries):
            tag = "even" if i % 2 == 0 else "odd"
            self.pban_tree.insert("", "end", values=(name, reason, date), tags=(tag,))

        ibans_file = self._server_dir() / "ip-bans.json"
        iban_entries = []
        if ibans_file.exists():
            try:
                with open(ibans_file) as f:
                    ibans_data = json.load(f)
                iban_entries = [(e.get("ip", ""), e.get("reason", ""), e.get("created", ""))
                                for e in ibans_data if e.get("ip")]
            except Exception:
                pass
        for item in self.iban_tree.get_children():
            self.iban_tree.delete(item)
        for i, (ip, reason, date) in enumerate(iban_entries):
            tag = "even" if i % 2 == 0 else "odd"
            self.iban_tree.insert("", "end", values=(ip, reason, date), tags=(tag,))

    # ── Network Tab ─────────────────────────────────────────
    def _build_network_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Network  ")
        frm = ttk.Frame(tab)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Connection Mode", style="SubHeader.TLabel").pack(anchor="w")
        self.use_playit_var = tk.BooleanVar(value=self.config.get("use_playit", True))
        mode_frame = ttk.Frame(frm)
        mode_frame.pack(fill=tk.X, pady=(6, 10))
        ttk.Radiobutton(mode_frame, text="playit.gg (Recommended - No port forwarding)",
                        variable=self.use_playit_var, value=True).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Direct IP (Requires port forwarding)",
                        variable=self.use_playit_var, value=False).pack(side=tk.LEFT)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        addr_frame = ttk.Frame(frm)
        addr_frame.pack(fill=tk.X, pady=10)
        ttk.Label(addr_frame, text="Your Server Address:", style="SubHeader.TLabel").pack(anchor="w")
        self.addr_card = ttk.Frame(addr_frame, style="Card.TFrame")
        self.addr_card.pack(fill=tk.X, pady=(6, 4))
        self.addr_lbl = ttk.Label(self.addr_card, text="Start the server to see your address",
                                  style="CardDim.TLabel", wraplength=600)
        self.addr_lbl.pack(side=tk.LEFT, padx=12, pady=12)
        self.copy_btn = ttk.Button(self.addr_card, text="Copy", state="disabled", command=self._copy_address)
        self.copy_btn.pack(side=tk.RIGHT, padx=12, pady=12)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        self.playit_card_net = ttk.Frame(frm, style="Card.TFrame")
        self.playit_card_net.pack(fill=tk.X, pady=10)
        self.playit_info = ttk.Label(self.playit_card_net, text="", style="Card.TLabel", wraplength=700)
        self.playit_info.pack(side=tk.LEFT, padx=12, pady=12)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        self.playit_link_btn = ttk.Button(btn_row, text="Open playit.gg Dashboard",
                                          style="Blue.TButton", command=lambda: webbrowser.open("https://playit.gg"))
        self.playit_link_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Check Public IP", command=self._fetch_ip).pack(side=tk.LEFT, padx=8)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        ttk.Label(frm, text="How playit.gg works:", style="SubHeader.TLabel").pack(anchor="w", pady=(6, 2))
        ttk.Label(frm, text=(
            "1. playit.gg creates a free tunnel so your server is reachable from anywhere.\n"
            "2. First time: run the server, then click 'Claim Agent' to link to a free playit.gg account.\n"
            "3. In the playit.gg dashboard, add a Minecraft tunnel pointing to your local port.\n"
            "4. Share the public address shown above with your friends - they join in Minecraft Multiplayer."
        ), style="Dim.TLabel", wraplength=750, justify="left").pack(anchor="w", pady=4)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        fw_frame = ttk.Frame(frm)
        fw_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(fw_frame, text="Firewall", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        fw_row = ttk.Frame(fw_frame)
        fw_row.pack(fill=tk.X)
        ttk.Button(fw_row, text="Open Server Port (UFW/iptables)", command=self._configure_firewall).pack(side=tk.LEFT)
        self.fw_status = ttk.Label(fw_row, text="", style="Dim.TLabel")
        self.fw_status.pack(side=tk.LEFT, padx=8)

        ttk.Separator(frm, orient="horizontal").pack(fill=tk.X, pady=6)
        port_frame = ttk.Frame(frm)
        port_frame.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(port_frame, text="Port Accessibility", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        port_row = ttk.Frame(port_frame)
        port_row.pack(fill=tk.X)
        ttk.Button(port_row, text="Check Port Accessibility", style="Blue.TButton",
                   command=self._check_port_accessibility).pack(side=tk.LEFT)
        self.port_check_status = ttk.Label(port_row, text="", style="Dim.TLabel")
        self.port_check_status.pack(side=tk.LEFT, padx=8)

    # ── Stats Tab ─────────────────────────────────────────
    def _build_stats_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Stats  ")
        scroll_inner = self._scrollable_frame(tab)
        frm = ttk.Frame(scroll_inner)
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(frm, text="Performance Dashboard", style="SubHeader.TLabel").pack(anchor="w")

        widget_cfg = ttk.Frame(frm)
        widget_cfg.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(widget_cfg, text="Visible widgets:", style="Dim.TLabel").pack(side=tk.LEFT)
        self._widget_vis = {}
        for key, label in [("cards", "Stats Cards"), ("ram", "RAM Graph"),
                           ("tps", "TPS Graph")]:
            var = tk.BooleanVar(value=self.config.get(f"widget_visible_{key}", True))
            self._widget_vis[key] = var
            ttk.Checkbutton(widget_cfg, text=label, variable=var,
                            command=self._toggle_widget_visibility).pack(side=tk.LEFT, padx=8)

        self._stat_cards_frame = ttk.Frame(frm)
        self._stat_cards_frame.pack(fill=tk.X, pady=(8, 10))
        self._stat_cards = {}
        for key, label in [("ram", "Current RAM"), ("tps", "Current TPS"),
                           ("uptime", "Uptime"), ("players", "Players"), ("status", "Status")]:
            card = ttk.Frame(self._stat_cards_frame, style="Card.TFrame")
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            lbl = ttk.Label(card, text=label, style="CardDim.TLabel",
                            font=("Segoe UI", 9))
            lbl.pack(anchor="w", padx=10, pady=(8, 0))
            val = ttk.Label(card, text="--", style="Card.TLabel",
                            font=("Segoe UI", 14, "bold"))
            val.pack(anchor="w", padx=10, pady=(0, 8))
            self._stat_cards[key] = val

        self._ram_label = ttk.Label(frm, text="RAM Usage Over Time", style="Dim.TLabel",
                                    font=("Segoe UI", 9, "bold"))
        self._ram_label.pack(anchor="w", pady=(6, 2))
        self._ram_canvas = tk.Canvas(frm, bg=BG_ENTRY, highlightthickness=0, height=160)
        self._ram_canvas.pack(fill=tk.X, pady=(0, 6))

        self._tps_label = ttk.Label(frm, text="TPS Over Time", style="Dim.TLabel",
                                    font=("Segoe UI", 9, "bold"))
        self._tps_label.pack(anchor="w", pady=(6, 2))
        self._tps_canvas = tk.Canvas(frm, bg=BG_ENTRY, highlightthickness=0, height=160)
        self._tps_canvas.pack(fill=tk.X)

        self._toggle_widget_visibility()

    def _update_stats_display(self):
        if not self.running:
            return
        with self._players_lock:
            pcount = len(self.online_players)
        self._stat_cards["players"].configure(text=str(pcount))
        self._stat_cards["status"].configure(
            text="Ready" if self.server_ready else "Starting",
            foreground=FG_GREEN if self.server_ready else FG_YELLOW
        )
        if self._perf_start_time:
            elapsed = time.time() - self._perf_start_time
            h, rem = divmod(int(elapsed), 3600)
            m, s = divmod(rem, 60)
            self._stat_cards["uptime"].configure(text=f"{h}h {m}m {s}s")
        if self._perf_ram_history:
            self._stat_cards["ram"].configure(text=f"{self._perf_ram_history[-1][1]:.0f} MB")
        if self._perf_tps_history:
            tps = self._perf_tps_history[-1][1]
            color = FG_GREEN if tps >= 18 else (FG_YELLOW if tps >= 15 else FG_RED)
            self._stat_cards["tps"].configure(text=f"{tps:.1f}", foreground=color)
        self._draw_ram_graph()
        self._draw_tps_graph()

    def _draw_ram_graph(self):
        c = self._ram_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return
        pad_l, pad_r, pad_t, pad_b = 50, 10, 10, 25
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b
        data = self._perf_ram_history[-60:]
        if not data:
            c.create_text(w // 2, h // 2, text="Waiting for data...", fill=FG_DIM, font=("Segoe UI", 10))
            return
        max_y = max(v for _, v in data) * 1.15 or 100
        c.create_line(pad_l, pad_t, pad_l, pad_t + gh, fill=FG_DIM, width=1)
        c.create_line(pad_l, pad_t + gh, pad_l + gw, pad_t + gh, fill=FG_DIM, width=1)
        for i in range(5):
            y = pad_t + gh - (gh * i / 4)
            val = max_y * i / 4
            c.create_line(pad_l - 4, y, pad_l, y, fill=FG_DIM)
            c.create_text(pad_l - 6, y, text=f"{val:.0f}", anchor="e", fill=FG_DIM, font=("Segoe UI", 8))
            c.create_line(pad_l, y, pad_l + gw, y, fill="#2a2a44", dash=(2, 4))
        n = len(data)
        if n == 1:
            x = pad_l + gw // 2
            y = pad_t + gh - (data[0][1] / max_y * gh)
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill=FG_ACCENT, outline="")
        else:
            coords = []
            for i, (_, val) in enumerate(data):
                x = pad_l + (gw * i / (n - 1))
                y = pad_t + gh - (val / max_y * gh)
                coords.extend([x, y])
            c.create_line(*coords, fill=FG_ACCENT, width=2, smooth=True)
        c.create_text(pad_l + gw // 2, pad_t + gh + 16, text="Time", fill=FG_DIM, font=("Segoe UI", 8))

    def _draw_tps_graph(self):
        c = self._tps_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50 or h < 50:
            return
        pad_l, pad_r, pad_t, pad_b = 50, 10, 10, 25
        gw = w - pad_l - pad_r
        gh = h - pad_t - pad_b
        data = self._perf_tps_history[-60:]
        if not data:
            c.create_text(w // 2, h // 2, text="Waiting for data...", fill=FG_DIM, font=("Segoe UI", 10))
            return
        max_y = 20.0
        c.create_line(pad_l, pad_t, pad_l, pad_t + gh, fill=FG_DIM, width=1)
        c.create_line(pad_l, pad_t + gh, pad_l + gw, pad_t + gh, fill=FG_DIM, width=1)
        y_green = pad_t + gh - (18 / max_y * gh)
        y_yellow = pad_t + gh - (15 / max_y * gh)
        c.create_rectangle(pad_l, pad_t, pad_l + gw, y_green, fill="#0d2818", outline="")
        c.create_rectangle(pad_l, y_green, pad_l + gw, y_yellow, fill="#2a2000", outline="")
        c.create_rectangle(pad_l, y_yellow, pad_l + gw, pad_t + gh, fill="#2a0d0d", outline="")
        for val, label in [(20, "20"), (18, "18"), (15, "15"), (10, "10"), (5, "5"), (0, "0")]:
            y = pad_t + gh - (val / max_y * gh)
            c.create_line(pad_l - 4, y, pad_l, y, fill=FG_DIM)
            c.create_text(pad_l - 6, y, text=label, anchor="e", fill=FG_DIM, font=("Segoe UI", 8))
            c.create_line(pad_l, y, pad_l + gw, y, fill="#2a2a44", dash=(2, 4))
        n = len(data)
        if n == 1:
            x = pad_l + gw // 2
            val = data[0][1]
            y = pad_t + gh - (val / max_y * gh)
            color = FG_GREEN if val >= 18 else (FG_YELLOW if val >= 15 else FG_RED)
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
        else:
            for i in range(n - 1):
                x1 = pad_l + (gw * i / (n - 1))
                y1 = pad_t + gh - (data[i][1] / max_y * gh)
                x2 = pad_l + (gw * (i + 1) / (n - 1))
                y2 = pad_t + gh - (data[i + 1][1] / max_y * gh)
                color = FG_GREEN if data[i + 1][1] >= 18 else (FG_YELLOW if data[i + 1][1] >= 15 else FG_RED)
                c.create_line(x1, y1, x2, y2, fill=color, width=2)
        c.create_text(pad_l + gw // 2, pad_t + gh + 16, text="Time", fill=FG_DIM, font=("Segoe UI", 8))

    # ── Helpers ─────────────────────────────────────────────

    def _scrollable_frame(self, parent):
        canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw", tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas._is_scroll_canvas = True

        def _update_scrollregion(e=None):
            inner.update_idletasks()
            canvas.configure(scrollregion=(0, 0, canvas.winfo_width(), inner.winfo_reqheight()))
        inner.bind("<Configure>", _update_scrollregion)

        def _on_cfg(e):
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
            _update_scrollregion()
        canvas.bind("<Configure>", _on_cfg)

        return inner

    @staticmethod
    def _on_global_mousewheel(ev):
        widget = ev.widget
        skip_types = (tk.Text, ttk.Treeview, ttk.Combobox, ttk.Spinbox)
        while widget is not None:
            if isinstance(widget, skip_types):
                return
            if getattr(widget, "_is_scroll_canvas", False):
                if sys.platform == "darwin":
                    widget.yview_scroll(int(-1 * ev.delta), "units")
                elif sys.platform == "win32":
                    widget.yview_scroll(int(-1 * (ev.delta / 120)), "units")
                else:
                    if ev.num == 4:
                        widget.yview_scroll(-3, "units")
                    elif ev.num == 5:
                        widget.yview_scroll(3, "units")
                return
            widget = widget.master

    def _info_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=2)
        card.lbl = ttk.Label(card, text="Checking...", style="CardDim.TLabel")
        card.lbl.pack(side=tk.LEFT, padx=14, pady=10)
        return card

    def _set_card(self, card, text, ok=True):
        card.lbl.configure(text=text, style="Ok.TLabel" if ok else "Err.TLabel")

    def _schedule_ui(self, *fns):
        def _do():
            for fn in fns:
                try:
                    fn()
                except Exception:
                    pass
        self.root.after(0, _do)

    def _log(self, msg, tag="info"):
        with self._log_lock:
            self._log_queue.append((msg, tag))
            self._write_log_line(msg)
            if self._log_flush_id is None:
                self._log_flush_id = self.root.after(16, self._flush_log_queue)

    def _flush_log_queue(self):
        self._log_flush_id = None
        with self._log_lock:
            queue = self._log_queue[:]
            self._log_queue.clear()
        if not queue:
            return
        try:
            self.console.configure(state="normal")
            for msg, tag in queue:
                ts = time.strftime("%H:%M:%S")
                self.console.insert(tk.END, f"[{ts}] ", "info")
                self.console.insert(tk.END, f"{msg}\n", tag)
            self.console.see(tk.END)
            self.console.configure(state="disabled")
        except Exception:
            pass

    def _set_status(self, text, ok=True):
        self.status_lbl.configure(text=f"  {text}", style="Status.TLabel" if ok else "Off.TLabel")

    # ── Initial Checks ──────────────────────────────────────
    def _initial_checks(self):
        stype = self.server_type_var.get()
        threading.Thread(target=self._do_initial_checks, args=(stype,), daemon=True).start()

    def _do_initial_checks(self, stype):
        java_ver, java_desc = check_java()
        if java_ver and java_ver >= 21:
            self.root.after(0, lambda: self._set_card(self.java_card, f"Java: OK - {java_desc}", True))
        else:
            hint = get_java_install_hint()
            self.root.after(0, lambda: self._set_card(self.java_card, f"Java: MISSING - {hint}", False))
        self.java_ok = java_ver is not None and java_ver >= 21

        sd = self._server_dir()
        jar_map = {"paper": sd / "paper.jar", "vanilla": sd / "server.jar",
                   "fabric": sd / "fabric-server.jar", "forge": sd / "forge-server.jar"}
        jar = jar_map.get(stype, sd / "paper.jar")
        exists = jar.exists()
        label = f"{stype.title()}: Downloaded" if exists else f"{stype.title()}: Not downloaded"
        self.root.after(0, lambda: self._set_card(self.paper_card, label, exists))
        self.paper_ready = exists

        playit_path = sd / ("playit.exe" if sys.platform == "win32" else "playit")
        if playit_path.exists():
            self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Downloaded", True))
            self.playit_ready = True
        else:
            self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Not downloaded", False))
            self.playit_ready = False

        self._fetch_versions_for(stype)
        self._fetch_ip()

    def _fetch_versions(self):
        stype = self.server_type_var.get()
        self._fetch_versions_for(stype)

    def _fetch_versions_for(self, stype):
        def _do():
            if stype == "paper":
                versions = get_latest_paper_version()
            elif stype in ("fabric", "forge"):
                versions = get_vanilla_versions()
            else:
                versions = get_vanilla_versions()
            if versions:
                self.root.after(0, lambda: self._populate_versions(versions))
            else:
                self.root.after(0, lambda: self._log(f"Could not fetch {stype} versions", "error"))
        threading.Thread(target=_do, daemon=True).start()

    def _populate_versions(self, versions):
        self.version_combo["values"] = versions
        saved = self.config.get("mc_version", "")
        if saved and saved in versions:
            self.version_var.set(saved)
        elif versions:
            self.version_var.set(versions[0])

    def _fetch_ip(self):
        def _do():
            ip = get_public_ip()
            self.public_ip = ip
            if ip:
                self.root.after(0, self._update_address_display)
        threading.Thread(target=_do, daemon=True).start()

    def _update_address_display(self):
        use_playit = self.use_playit_var.get()
        if use_playit:
            if self.playit_address:
                self.addr_lbl.configure(text=self.playit_address, style="Addr.TLabel")
                self.copy_btn.configure(state="normal")
            else:
                self.addr_lbl.configure(text="Start the server to get your playit.gg address", style="CardDim.TLabel")
                self.copy_btn.configure(state="disabled")
        else:
            port = self.config.get("server_port", 25565)
            if self.public_ip:
                self.addr_lbl.configure(text=f"{self.public_ip}:{port}", style="Addr.TLabel")
                self.copy_btn.configure(state="normal")
            else:
                self.addr_lbl.configure(text="Could not detect public IP", style="CardDim.TLabel")
                self.copy_btn.configure(state="disabled")

    def _copy_address(self):
        text = self.addr_lbl.cget("text")
        if text and "Start the server" not in text and "Could not" not in text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._log("Address copied to clipboard!", "success")

    def _on_eula_toggle(self):
        self.config["accepted_eula"] = self.eula_var.get()
        self._save_config()

    def _on_server_type_change(self):
        stype = self.server_type_var.get()
        labels = {"paper": "Paper MC Version", "vanilla": "Vanilla Version",
                  "fabric": "Fabric MC Version", "forge": "Forge MC Version"}
        self.version_label.configure(text=labels.get(stype, "Version"))
        self._check_server_installed()
        self._fetch_versions()

    def _check_server_installed(self):
        stype = self.server_type_var.get()
        sd = self._server_dir()
        jar_map = {"paper": sd / "paper.jar", "vanilla": sd / "server.jar",
                   "fabric": sd / "fabric-server.jar", "forge": sd / "forge-server.jar"}
        jar = jar_map.get(stype, sd / "paper.jar")
        exists = jar.exists()
        label = f"{stype.title()}: Downloaded" if exists else f"{stype.title()}: Not downloaded"
        self.root.after(0, lambda: self._set_card(self.paper_card, label, exists))
        self.paper_ready = exists

    # ── Download Server ──────────────────────────────────────
    def _download_server(self):
        ver = self.version_var.get()
        if not ver:
            messagebox.showwarning("No Version", "Select a Minecraft version first.")
            return
        if not self.config.get("accepted_eula", False):
            messagebox.showwarning("EULA", "Accept the Minecraft EULA first (Setup tab).")
            self.notebook.select(0)
            return
        stype = self.server_type_var.get()
        self.dl_btn.configure(state="disabled")
        self.dl_status.configure(text="Fetching build info...")
        threading.Thread(target=self._do_download, args=(ver, stype), daemon=True).start()

    def _do_download(self, version, stype):
        sd = self._server_dir()
        if stype == "paper":
            url, build_id, fname = get_paper_build_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log("No stable Paper build found for this version", "error")
                return
            dest = str(sd / "paper.jar")
            label = f"Paper {version} build {build_id}"
        elif stype == "fabric":
            url, fname = get_fabric_server_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log(f"No Fabric server found for {version}", "error")
                return
            dest = str(sd / "fabric-server.jar")
            label = f"Fabric {version}"
        elif stype == "forge":
            url, fname, label_text = get_forge_server_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log(f"No Forge installer found for {version}", "error")
                return
            installer_dest = str(sd / "forge-installer.jar")
            sd.mkdir(parents=True, exist_ok=True)
            self._schedule_ui(
                lambda: self.dl_status.configure(text=f"Downloading {fname}..."),
                lambda: self.dl_progress.configure(value=0),
            )
            last_update_fg = [0]
            def progress(d, t):
                pct = (d / t) * 100
                now = time.monotonic()
                if pct - last_update_fg[0] >= 2 or now - getattr(progress, '_last_t', 0) >= 0.5:
                    last_update_fg[0] = pct
                    progress._last_t = now
                    self.root.after(0, lambda p=pct: self.dl_progress.configure(value=p))
            ok = download_file(url, installer_dest, progress_cb=progress)
            if ok:
                self._log(f"Running Forge installer for {version}...")
                self.root.after(0, lambda: self.dl_status.configure(text="Running Forge installer..."))
                try:
                    r = subprocess.run(
                        ["java", "-jar", installer_dest, "--installServer"],
                        cwd=str(sd), capture_output=True, text=True, timeout=600
                    )
                    if r.returncode == 0:
                        forge_jar = None
                        for f in sd.glob("forge-*server*.jar"):
                            forge_jar = f
                            break
                        if not forge_jar:
                            for f in sd.glob("forge-*.jar"):
                                if "installer" not in f.name:
                                    forge_jar = f
                                    break
                        if forge_jar:
                            shutil.copy2(str(forge_jar), str(sd / "forge-server.jar"))
                            self.config["mc_version"] = version
                            self.config["server_type"] = stype
                            self._save_config()
                            self.paper_ready = True
                            self._schedule_ui(
                                lambda: self.dl_progress.configure(value=100),
                                lambda: self.dl_status.configure(text=f"{label_text} ready!"),
                                lambda: self._set_card(self.paper_card, label_text, True),
                                lambda: self.dl_btn.configure(state="normal"),
                            )
                            self._log(f"{label_text} installed", "success")
                        else:
                            self._schedule_ui(
                                lambda: self.dl_status.configure(text="Install failed"),
                                lambda: self.dl_btn.configure(state="normal"),
                            )
                            self._log("Forge installer completed but jar not found", "error")
                    else:
                        self._schedule_ui(
                            lambda: self.dl_status.configure(text="Install failed"),
                            lambda: self.dl_btn.configure(state="normal"),
                        )
                        self._log(f"Forge install error: {r.stderr[:200]}", "error")
                except Exception as e:
                    self._schedule_ui(
                        lambda: self.dl_status.configure(text="Install failed"),
                        lambda: self.dl_btn.configure(state="normal"),
                    )
                    self._log(f"Forge install failed: {e}", "error")
            else:
                self._schedule_ui(
                    lambda: self.dl_status.configure(text="Download failed!"),
                    lambda: self.dl_btn.configure(state="normal"),
                )
                self._log("Failed to download Forge installer", "error")
            self.root.after(0, lambda: self.dl_btn.configure(state="normal"))
            return
        else:
            url = get_vanilla_download_url(version)
            if not url:
                self.root.after(0, lambda: self._log(f"No vanilla server found for {version}", "error"))
                self.root.after(0, lambda: self.dl_btn.configure(state="normal"))
                return
            dest = str(sd / "server.jar")
            fname = "server.jar"
            label = f"Vanilla {version}"

        sd.mkdir(parents=True, exist_ok=True)
        self.root.after(0, lambda: self.dl_status.configure(text=f"Downloading {fname}..."))
        self.root.after(0, lambda: self.dl_progress.configure(value=0))

        last_update = [0]
        def progress(done, total):
            pct = (done / total) * 100
            now = time.monotonic()
            if pct - last_update[0] >= 2 or now - getattr(progress, '_last_t', 0) >= 0.5:
                last_update[0] = pct
                progress._last_t = now
                self.root.after(0, lambda p=pct: self.dl_progress.configure(value=p))

        ok = download_file(url, dest, progress_cb=progress)
        if ok:
            self.config["mc_version"] = version
            self.config["server_type"] = stype
            self._save_config()
            self.paper_ready = True
            self._schedule_ui(
                lambda: self.dl_progress.configure(value=100),
                lambda: self.dl_status.configure(text=f"{label} ready!"),
                lambda: self._set_card(self.paper_card, f"{label}", True),
                lambda: self.dl_btn.configure(state="normal"),
            )
            self._log(f"{label} downloaded", "success")
        else:
            self._schedule_ui(
                lambda: self.dl_status.configure(text="Download failed!"),
                lambda: self.dl_btn.configure(state="normal"),
            )
            self._log(f"Failed to download {stype} server", "error")

    # ── Download playit ─────────────────────────────────────
    def _download_playit(self, callback=None):
        url = get_playit_url()
        if not url:
            self._log("playit.gg not available on this platform", "error")
            return
        self._log("Downloading playit.gg agent...")
        self._set_card(self.playit_card, "playit.gg: Downloading...", True)

        def _do():
            playit_bin = self._server_dir() / ("playit.exe" if sys.platform == "win32" else "playit")
            ok = download_file(url, str(playit_bin))
            if ok:
                sha_url = url + ".sha256"
                try:
                    req = urllib.request.Request(sha_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        expected = resp.read().decode().strip().split()[0]
                    h = hashlib.sha256(playit_bin.read_bytes()).hexdigest()
                    if h != expected:
                        self.root.after(0, lambda: self._log(
                            "playit.gg hash mismatch - download may be corrupted", "error"))
                        self.root.after(0, lambda: self._set_card(
                            self.playit_card, "playit.gg: Hash mismatch", False))
                        return
                except Exception:
                    pass
                if sys.platform != "win32":
                    os.chmod(str(playit_bin), 0o755)
                self.playit_ready = True
                self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Downloaded", True))
                self.root.after(0, lambda: self._log("playit.gg agent downloaded", "success"))
                if callback:
                    callback()
            else:
                self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Download failed", False))
                self.root.after(0, lambda: self._log("Failed to download playit.gg agent", "error"))
        threading.Thread(target=_do, daemon=True).start()

    # ── Server Control ──────────────────────────────────────
    def _start_server(self):
        if self.running:
            return
        stype = self.config.get("server_type", "paper")
        sd = self._server_dir()
        jar_map = {"paper": sd / "paper.jar", "vanilla": sd / "server.jar",
                   "fabric": sd / "fabric-server.jar", "forge": sd / "forge-server.jar"}
        jar = jar_map.get(stype, sd / "paper.jar")
        if not jar.exists():
            messagebox.showwarning("Not Ready", f"Download the server first (Setup tab).")
            self.notebook.select(0)
            return
        if not self.config.get("accepted_eula", False):
            messagebox.showwarning("EULA", "Accept the Minecraft EULA first (Setup tab).")
            self.notebook.select(0)
            return

        self.config["ram_min"] = self.ram_min_var.get()
        self.config["ram_max"] = self.ram_max_var.get()
        self._save_server_config()
        self._write_eula()

        sd = self._server_dir()
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "server.properties").write_text(generate_server_properties(self.config))

        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

        self._log(f"Starting {stype.title()} server...", "info")

        if self.auto_backup_var.get():
            self._auto_backup_world()

        if not getattr(self, 'java_ok', False):
            self._log("Java 21+ not found. Attempting to install Java...", "warn")
            self.root.after(0, lambda: self._set_status("Installing Java...", True))
            install_ok = False
            try:
                install_ok = _install_java()
            except Exception as ie:
                self._log(f"Java install failed: {ie}", "error")
            if not install_ok:
                self._log("Java installation failed.", "error")
                self._log(get_java_install_hint(), "info")
                self.root.after(0, lambda: self._set_status("Java install failed", False))
                return
            ver, info = check_java()
            if ver is None or ver < 21:
                self._log(f"Java installed but version {info} is too old. Need 21+.", "error")
                self._log(get_java_install_hint(), "info")
                self.root.after(0, lambda: self._set_status("Java too old", False))
                return
            self.java_ok = True
            self._log(f"Java installed: {info}", "success")
            self.root.after(0, lambda: self._set_status("Java ready", True))

        xms = self.config.get("ram_min", "1G")
        xmx = self.config.get("ram_max", "2G")
        cmd = ["java", f"-Xms{xms}", f"-Xmx{xmx}", "-jar", str(jar), "nogui"]

        try:
            self.server_process = subprocess.Popen(
                cmd, cwd=str(self._server_dir()), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            self.running = True
            self.server_ready = False
            self.stopped_manually = False
            self._perf_ram_history = []
            self._perf_tps_history = []
            self._perf_player_history = []
            self._perf_start_time = time.time()
            with self._players_lock:
                self.online_players.clear()
            self.root.after(0, self._update_players_display)
            self.root.after(0, lambda: self.start_btn.configure(state="disabled"))
            self.root.after(0, lambda: self.stop_btn.configure(state="normal"))
            self.root.after(0, lambda: self._set_status("Starting...", True))
            threading.Thread(target=self._read_server_output, daemon=True).start()
            self._send_notification("MCServerHost", "Server Started")
            self._start_resource_monitor()
            if self.sched_restart_var.get():
                self.root.after(2000, self._start_scheduled_restart_timer)
            if self.periodic_backup_var.get():
                self.root.after(2000, self._start_periodic_backup_timer)
            if self._load_scheduled_tasks():
                self.root.after(2000, self._start_scheduled_tasks_timer)
            if self.use_playit_var.get():
                self.root.after(2000, self._start_playit)
        except Exception as e:
            self._log(f"Failed to start server: {e}", "error")
            self.running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self._set_status("Offline", False)
            self.running = False

    def _parse_tps(self, line):
        m = re.search(r'Ticks per second:\s*([\d.]+)', line)
        if m:
            self._perf_tps_history.append((time.time(), min(float(m.group(1)), 20.0)))
            if len(self._perf_tps_history) > 60:
                self._perf_tps_history = self._perf_tps_history[-60:]
            return
        m = re.search(r'Average:\s*([\d.]+)\s*tick', line)
        if m:
            avg = float(m.group(1))
            tps = min(20.0, 20.0 / avg) if avg > 0 else 20.0
            self._perf_tps_history.append((time.time(), tps))
            if len(self._perf_tps_history) > 60:
                self._perf_tps_history = self._perf_tps_history[-60:]
            return
        if "Can't keep up" in line:
            self._perf_tps_history.append((time.time(), 10.0))
            if len(self._perf_tps_history) > 60:
                self._perf_tps_history = self._perf_tps_history[-60:]

    def _read_server_output(self):
        proc = self.server_process
        if not proc or not proc.stdout:
            return
        start_time = time.time()
        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line:
                    continue
                tag = "info"
                if "[ERROR]" in line or "[error]" in line.lower() or "SEVERE" in line:
                    tag = "error"
                elif "[WARN]" in line or "[warning]" in line.lower():
                    tag = "warn"
                elif "Done" in line and "For help" in line:
                    tag = "success"
                    self.server_ready = True
                self._parse_player_event(line)
                self._parse_tps(line)
                self._log(line, tag)
        except (ValueError, OSError):
            pass
        rc = proc.wait()
        uptime = time.time() - start_time
        self._log(f"Server stopped (exit code {rc})", "warn" if rc == 0 else "error")
        self.running = False
        self.server_ready = False
        with self._players_lock:
            self.online_players.clear()
        self.root.after(0, self._update_players_display)
        if not self.stopped_manually and self.auto_restart_var.get() and uptime > 5:
            delay = int(self.restart_delay_var.get())
            self._log(f"Auto-restarting in {delay} seconds...", "warn")
            self.root.after(delay * 1000, self._auto_restart_server)
        else:
            self.root.after(0, self._on_server_stopped)

    def _on_server_stopped(self):
        self._cancel_all_timers()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._set_status("Offline", False)
        self.addr_lbl.configure(text="Server stopped", style="CardDim.TLabel")
        self.copy_btn.configure(state="disabled")
        self._stop_playit()
        self._stop_resource_monitor()
        if not self.stopped_manually:
            self._send_notification("MCServerHost", "Server Stopped")
            self._analyze_crash_reports()

    CRASH_PATTERNS = [
        (r"java\.lang\.OutOfMemoryError", "Out of Memory", "Increase RAM allocation in Setup tab (e.g. -Xmx4G)."),
        (r"java\.lang\.ClassCastException", "Mod/Plugin Conflict", "A mod or plugin has a class incompatibility. Remove recently added mods/plugins."),
        (r"Could not find or load main class (\S+)", "Missing Dependency", "The server jar may be corrupted. Re-download it, or ensure the correct server type is selected."),
        (r"Failed to load (\S+\.jar)", "Mod/Plugin Load Failure", "A required dependency is missing. Install the required mod/plugin version."),
        (r"NoSuchFileException|FileNotFoundException", "Missing File", "A required file is missing. Check config files and world data."),
        (r"Port (\d+) is already in use", "Port Conflict", "Another process is using this port. Stop the other process or change the server port."),
        (r"Invalid or corrupt jar file", "Corrupt Jar", "The server jar is corrupted. Re-download it from the Setup tab."),
        (r"Failed to bind to port", "Bind Failure", "Could not bind to the server port. Check if another server is already running."),
        (r"UnsupportedClassVersionError", "Java Version Too Old", "Your Java version is too old. Install Java 17 or newer."),
        (r"ConfigException|Configuration error", "Config Error", "A configuration file is invalid. Check server.properties and plugin configs."),
        (r"TicksPerSecond|Can't keep up", "Server Overloaded", "The server can't keep up with the tick rate. Reduce view-distance, increase RAM, or reduce entity counts."),
        (r"RegionFileCorrupt|Corrupted region file", "World Corruption", "The world data is corrupted. Restore from a backup."),
        (r"java\.net\.ConnectException|java\.nio\.channels\.ClosedChannelException", "Network Error", "A network connection failed. Check firewall settings and network configuration."),
    ]

    def _analyze_crash_reports(self):
        crash_dir = self._server_dir() / "crash-reports"
        if not crash_dir.exists():
            return
        crash_files = sorted(crash_dir.glob("crash-*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not crash_files:
            return
        latest = crash_files[0]
        if (time.time() - latest.stat().st_mtime) > 300:
            return
        try:
            content = latest.read_text(errors="replace")
        except Exception:
            return
        self._log(f"─── Crash Report: {latest.name} ───", "error")
        findings = []
        for pattern, title, fix in self.CRASH_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append((title, fix))
        if findings:
            for title, fix in findings:
                self._log(f"  [!] {title}: {fix}", "warn")
        else:
            self._log("  No known patterns matched. Check the crash report for details:", "warn")
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")][:10]
            for line in lines:
                self._log(f"  {line}", "error")
        self._log(f"  Full report: {latest}", "info")

    def _stop_server(self):
        if not self.running or not self.server_process:
            return
        self.stopped_manually = True
        self._log("Stopping server...", "info")
        def _do():
            try:
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
            except Exception:
                try:
                    self.server_process.terminate()
                except Exception:
                    pass
        threading.Thread(target=_do, daemon=True).start()

    def _send_command(self):
        if not self.running or not self.server_process:
            return
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        try:
            self.server_process.stdin.write(cmd + "\n")
            self.server_process.stdin.flush()
            self._log(f"> {cmd}", "cmd")
            self.cmd_entry.delete(0, tk.END)
        except Exception as e:
            self._log(f"Failed to send command: {e}", "error")

    def _send_server_command(self, cmd):
        if not self.running or not self.server_process:
            return
        try:
            self.server_process.stdin.write(cmd + "\n")
            self.server_process.stdin.flush()
            self._log(f"> {cmd}", "cmd")
        except Exception as e:
            self._log(f"Failed to send command: {e}", "error")

    # ── playit.gg ───────────────────────────────────────────
    def _start_playit(self):
        if not self.playit_ready:
            self._download_playit(callback=self._start_playit)
            return
        if self.playit_process:
            return
        self._log("Starting playit.gg agent...")
        try:
            self.playit_process = subprocess.Popen(
                [str(self._server_dir() / ("playit.exe" if sys.platform == "win32" else "playit"))],
                cwd=str(self._server_dir()), stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            threading.Thread(target=self._read_playit_output, daemon=True).start()
            self.playit_info.configure(text="Connecting to playit.gg...")
        except Exception as e:
            self._log(f"Failed to start playit.gg: {e}", "error")

    def _read_playit_output(self):
        proc = self.playit_process
        if not proc or not proc.stdout:
            return
        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            self._log(f"[playit] {line}", "info")

            claim_match = re.search(r'(https?://[^\s]*claim[^\s]*)', line)
            if claim_match:
                self.playit_claim_url = claim_match.group(1)
                self.root.after(0, self._show_claim_url)

            for pattern in [r'(\w[\w-]+\.joinplayit\.gg):(\d+)', r'([\w.-]+\.playit\.gg):(\d+)']:
                addr_match = re.search(pattern, line)
                if addr_match:
                    self.playit_address = f"{addr_match.group(1)}:{addr_match.group(2)}"
                    self.root.after(0, self._update_address_display)
                    break

        rc = proc.wait()
        self._log(f"playit.gg agent stopped (exit code {rc})", "warn")
        self.playit_process = None

    def _show_claim_url(self):
        if self.playit_claim_url:
            self.playit_info.configure(
                text=f"Claim this agent to link to your playit.gg account:\n{self.playit_claim_url}\n\n"
                     "Click the link or use the button below. Then create a Minecraft tunnel in your dashboard."
            )
            self.playit_link_btn.configure(
                text="Open Claim URL",
                command=lambda: webbrowser.open(self.playit_claim_url)
            )

    def _stop_playit(self):
        if self.playit_process:
            try:
                self.playit_process.terminate()
            except Exception:
                pass
            self.playit_process = None
            self.playit_address = None

    # ── Config Save ─────────────────────────────────────────
    def _save_server_config(self):
        BOOL_KEYS = {"online_mode", "pvp", "white_list", "hardcore", "require_resource_pack"}
        for key, var in self._cfg_vars.items():
            val = var.get()
            if key in BOOL_KEYS:
                val = val == "true"
            elif key in ("server_port", "max_players", "view_distance", "spawn_protection"):
                try:
                    val = int(val)
                except ValueError:
                    continue
            self.config[key] = val
        self.config["ram_min"] = self.ram_min_var.get()
        self.config["ram_max"] = self.ram_max_var.get()
        self.config["use_playit"] = self.use_playit_var.get()
        self.config["server_type"] = self.server_type_var.get()
        if hasattr(self, 'auto_restart_var'):
            self.config["auto_restart"] = self.auto_restart_var.get()
        if hasattr(self, 'restart_delay_var'):
            try:
                self.config["restart_delay"] = int(self.restart_delay_var.get())
            except ValueError:
                pass
        if hasattr(self, 'auto_backup_var'):
            self.config["auto_backup"] = self.auto_backup_var.get()
        if hasattr(self, 'sched_restart_var'):
            self.config["scheduled_restart"] = self.sched_restart_var.get()
        if hasattr(self, 'sched_hours_var'):
            try:
                self.config["scheduled_restart_hours"] = float(self.sched_hours_var.get())
            except ValueError:
                pass
        if hasattr(self, 'periodic_backup_var'):
            self.config["periodic_backup"] = self.periodic_backup_var.get()
        if hasattr(self, 'backup_interval_var'):
            try:
                self.config["periodic_backup_interval"] = int(self.backup_interval_var.get())
            except ValueError:
                pass
        if hasattr(self, 'log_export_var'):
            self.config["log_export"] = self.log_export_var.get()
        if hasattr(self, 'backup_max_age_var'):
            try:
                self.config["backup_max_age_days"] = int(self.backup_max_age_var.get())
            except ValueError:
                pass
        if hasattr(self, 'backup_max_count_var'):
            try:
                self.config["backup_max_count"] = int(self.backup_max_count_var.get())
            except ValueError:
                pass
        self._save_config()

    def _on_auto_restart_toggle(self):
        self.config["auto_restart"] = self.auto_restart_var.get()
        self._save_config()

    def _auto_restart_server(self):
        if self.stopped_manually or not self.auto_restart_var.get():
            self.root.after(0, self._on_server_stopped)
            return
        self._log("Auto-restarting server...", "info")
        self._start_server()

    def _parse_player_event(self, line):
        join_match = re.search(r'(\w+)\s+joined the game', line)
        leave_match = re.search(r'(\w+)\s+left the game', line)
        if join_match:
            player = join_match.group(1)
            with self._players_lock:
                self.online_players.add(player)
            self.root.after(0, self._update_players_display)
            self._notify_player_join(player)
            self._track_player_join(player)
        elif leave_match:
            player = leave_match.group(1)
            with self._players_lock:
                self.online_players.discard(player)
            self.root.after(0, self._update_players_display)
            self._notify_player_leave(player)
            self._track_player_leave(player)
        player, message = self._parse_chat_message(line)
        if player is not None:
            self._display_chat(player, message)

    def _update_players_display(self):
        with self._players_lock:
            players = sorted(self.online_players)
        if players:
            self.players_lbl.configure(text=", ".join(players))
        else:
            self.players_lbl.configure(text="None")

    def _auto_backup_world(self):
        sd = self._server_dir()
        world_dir = sd / self.config.get("level_name", "world")
        if not world_dir.exists():
            return
        threading.Thread(target=self._do_backup_world, daemon=True).start()

    def _do_backup_world(self):
        sd = self._server_dir()
        world_dir = sd / self.config.get("level_name", "world")
        if not world_dir.exists():
            return
        backups_dir = sd / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = backups_dir / f"world_backup_{ts}.zip"
        try:
            with zipfile.ZipFile(str(zip_name), 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(str(world_dir)):
                    for file in files:
                        fp = os.path.join(root, file)
                        arcname = os.path.relpath(fp, str(world_dir))
                        zf.write(fp, arcname)
            self._log(f"World backed up to {zip_name.name}", "success")
            ok, msg = self._verify_backup(zip_name)
            if ok:
                self._log(f"Backup verified: {msg}", "success")
            else:
                self._log(f"Backup verification FAILED: {msg}", "error")
            self.root.after(0, lambda: self.backup_status.configure(text=f"Last backup: {ts}"))
            self._rotate_backups()
        except Exception as e:
            self._log(f"Backup failed: {e}", "error")

    def _rotate_backups(self):
        backups_dir = self._server_dir() / "backups"
        if not backups_dir.exists():
            return
        backups = sorted(backups_dir.glob("world_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            return
        max_age_days = int(self.config.get("backup_max_age_days", 0))
        max_count = int(self.config.get("backup_max_count", 0))
        now = time.time()
        removed = 0
        for idx, bp in enumerate(backups):
            should_remove = False
            if max_age_days > 0:
                age_days = (now - bp.stat().st_mtime) / 86400
                if age_days > max_age_days:
                    should_remove = True
            if max_count > 0 and idx >= max_count:
                should_remove = True
            if should_remove:
                try:
                    bp.unlink()
                    removed += 1
                except Exception:
                    pass
        if removed:
            self._log(f"Backup rotation: removed {removed} old backup(s)", "info")

    def _manual_backup_world(self):
        self._auto_backup_world()

    def _restore_world(self):
        backups_dir = self._server_dir() / "backups"
        if not backups_dir.exists():
            messagebox.showinfo("No Backups", "No backups found.")
            return
        backups = sorted(backups_dir.glob("world_backup_*.zip"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            messagebox.showinfo("No Backups", "No backups found.")
            return
        if self.running:
            messagebox.showwarning("Server Running", "Stop the server before restoring a backup.")
            return
        latest = backups[0]
        if not messagebox.askyesno("Restore Backup",
                                   f"Restore from {latest.name}?\nCurrent world will be replaced."):
            return
        world_name = self.config.get("level_name", "world")
        world_dir = self._server_dir() / world_name
        try:
            if world_dir.exists():
                shutil.rmtree(str(world_dir))
            with zipfile.ZipFile(str(latest), 'r') as zf:
                zf.extractall(str(world_dir))
            self._log(f"World restored from {latest.name}", "success")
            self.root.after(0, lambda: self.backup_status.configure(text=f"Restored: {latest.name}"))
        except Exception as e:
            self._log(f"Restore failed: {e}", "error")

    def _add_whitelist_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        wl_file = self._server_dir() / "whitelist.json"
        wl = []
        if wl_file.exists():
            try:
                with open(wl_file) as f:
                    wl = json.load(f)
            except Exception:
                wl = []
        if any(e.get("name", "").lower() == name.lower() for e in wl):
            self.root.after(0, lambda: self.wl_status.configure(text=f"{name} already whitelisted"))
            return
        wl.append({"name": name})
        with open(wl_file, "w") as f:
            json.dump(wl, f, indent=2)
        self.root.after(0, lambda: self.wl_status.configure(text=f"Added {name} to whitelist"))
        self.wl_player_var.set("")
        self.root.after(0, self._refresh_players)

    def _remove_whitelist_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        wl_file = self._server_dir() / "whitelist.json"
        if not wl_file.exists():
            self.root.after(0, lambda: self.wl_status.configure(text="No whitelist file"))
            return
        try:
            with open(wl_file) as f:
                wl = json.load(f)
            wl = [e for e in wl if e.get("name", "").lower() != name.lower()]
            with open(wl_file, "w") as f:
                json.dump(wl, f, indent=2)
            self.root.after(0, lambda: self.wl_status.configure(text=f"Removed {name} from whitelist"))
        except Exception as e:
            self.root.after(0, lambda: self.wl_status.configure(text=f"Error: {e}"))
        self.wl_player_var.set("")
        self.root.after(0, self._refresh_players)

    def _add_op_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        ops_file = self._server_dir() / "ops.json"
        ops = []
        if ops_file.exists():
            try:
                with open(ops_file) as f:
                    ops = json.load(f)
            except Exception:
                ops = []
        if any(e.get("name", "").lower() == name.lower() for e in ops):
            self.root.after(0, lambda: self.wl_status.configure(text=f"{name} is already an operator"))
            return
        ops.append({"name": name, "level": 4, "bypassesPlayerLimit": True})
        with open(ops_file, "w") as f:
            json.dump(ops, f, indent=2)
        self.root.after(0, lambda: self.wl_status.configure(text=f"Added {name} as operator"))
        self.wl_player_var.set("")
        self.root.after(0, self._refresh_players)

    def _remove_op_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        ops_file = self._server_dir() / "ops.json"
        if not ops_file.exists():
            self.root.after(0, lambda: self.wl_status.configure(text="No ops file"))
            return
        try:
            with open(ops_file) as f:
                ops = json.load(f)
            ops = [e for e in ops if e.get("name", "").lower() != name.lower()]
            with open(ops_file, "w") as f:
                json.dump(ops, f, indent=2)
            self.root.after(0, lambda: self.wl_status.configure(text=f"Removed {name} from operators"))
        except Exception as e:
            self.root.after(0, lambda: self.wl_status.configure(text=f"Error: {e}"))
        self.wl_player_var.set("")
        self.root.after(0, self._refresh_players)

    def _configure_firewall(self):
        port = self.config.get("server_port", 25565)
        if sys.platform == "win32":
            rule_name = f"MCServerHost Port {port}"
            cmd = ["netsh", "advfirewall", "firewall", "add", "rule",
                   f"name={rule_name}", "dir=in", "action=allow",
                   "protocol=TCP", f"localport={port}"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    self._log(f"Firewall: opened port {port}/tcp (Windows Defender)", "success")
                    self.root.after(0, lambda: self.fw_status.configure(text=f"Port {port} opened"))
                else:
                    self._log(f"Windows Firewall error: {r.stderr.strip()}", "error")
            except Exception as e:
                self._log(f"Firewall config failed: {e}", "error")
        elif sys.platform == "darwin":
            cmd = ["/usr/libexec/ApplicationFirewall/socketfilterfw",
                   "--addport", str(port), "--setblockall", "off"]
            try:
                r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    self._log(f"Firewall: opened port {port}/tcp (macOS)", "success")
                    self.root.after(0, lambda: self.fw_status.configure(text=f"Port {port} opened"))
                else:
                    self._log(f"macOS firewall error: {r.stderr.strip()}", "error")
            except Exception as e:
                self._log(f"Firewall config failed: {e}", "error")
        elif shutil.which("ufw"):
            try:
                r = subprocess.run(["sudo", "ufw", "allow", f"{port}/tcp"],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    self._log(f"Firewall: opened port {port}/tcp (UFW)", "success")
                    self.root.after(0, lambda: self.fw_status.configure(text=f"Port {port} opened"))
                else:
                    self._log(f"UFW error: {r.stderr.strip()}", "error")
            except Exception as e:
                self._log(f"Firewall config failed: {e}", "error")
        elif shutil.which("iptables"):
            try:
                r = subprocess.run(["sudo", "iptables", "-A", "INPUT", "-p", "tcp",
                                    "--dport", str(port), "-j", "ACCEPT"],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    self._log(f"Firewall: opened port {port}/tcp (iptables)", "success")
                    self.root.after(0, lambda: self.fw_status.configure(text=f"Port {port} opened"))
                else:
                    self._log(f"iptables error: {r.stderr.strip()}", "error")
            except Exception as e:
                self._log(f"Firewall config failed: {e}", "error")
        else:
            self._log("No firewall tool found", "warn")

    def _check_port_accessibility(self):
        port = self.config.get("server_port", 25565)
        self._log(f"Checking port {port} accessibility...", "info")
        self.root.after(0, lambda: self.port_check_status.configure(text="Checking..."))

        def _do():
            results = []
            local_ok = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex(("127.0.0.1", port))
                local_ok = (result == 0)
                s.close()
            except Exception:
                pass
            results.append(("Local port", local_ok))

            public_ip = None
            try:
                resp = urllib.request.urlopen("https://api.ipify.org", timeout=5)
                public_ip = resp.read().decode().strip()
            except Exception:
                pass

            ext_ok = None
            if public_ip:
                try:
                    check_url = f"https://portchecker.co/check?host={public_ip}&ports={port}"
                    req = urllib.request.Request(check_url, headers={"User-Agent": USER_AGENT})
                    resp = urllib.request.urlopen(req, timeout=10)
                    body = resp.read().decode().lower()
                    ext_ok = "open" in body or "status: open" in body
                except Exception:
                    pass
                if ext_ok is None:
                    try:
                        check_url = f"https://check-host.net/check-tcp?host={public_ip}:{port}"
                        req = urllib.request.Request(check_url, headers={"User-Agent": USER_AGENT})
                        resp = urllib.request.urlopen(req, timeout=10)
                        body = resp.read().decode().lower()
                        ext_ok = "ok" in body or "status: open" in body or '"1"' in body
                    except Exception:
                        pass
            results.append(("External port", ext_ok))

            for label, ok in results:
                if ok is None:
                    msg = f"  {label}: could not determine"
                    tag = "warn"
                elif ok:
                    msg = f"  {label}: OPEN"
                    tag = "success"
                else:
                    msg = f"  {label}: CLOSED/FILTERED"
                    tag = "error"
                self._log(msg, tag)

            if not local_ok:
                self._log("  Tip: The server might not be running, or the port is in use.", "warn")
            elif ext_ok is False:
                self._log("  Tip: Port is open locally but not reachable externally.", "warn")
                self._log("  Try: 1) Enable port forwarding on your router  2) Use playit.gg instead", "warn")

            status_parts = []
            for label, ok in results:
                if ok is True:
                    status_parts.append(f"{label}: OPEN")
                elif ok is False:
                    status_parts.append(f"{label}: CLOSED")
            status_text = " | ".join(status_parts) if status_parts else "Check complete"
            self.root.after(0, lambda t=status_text: self.port_check_status.configure(text=t))

        threading.Thread(target=_do, daemon=True).start()

    def _auto_update_server(self):
        stype = self.config.get("server_type", "paper")
        ver = self.config.get("mc_version", "")
        if not ver:
            messagebox.showinfo("No Version", "No server version configured.")
            return
        if self.running:
            messagebox.showwarning("Server Running", "Stop the server before updating.")
            return

        def _do():
            sd = self._server_dir()
            if stype == "paper":
                url, build_id, fname = get_paper_build_url(ver)
                if not url:
                    self._log("No stable Paper build found", "error")
                    return
                dest = str(sd / "paper.jar")
                label = f"Paper {ver} build {build_id}"
            elif stype == "fabric":
                url, fname = get_fabric_server_url(ver)
                if not url:
                    self._log(f"No Fabric server found for {ver}", "error")
                    return
                dest = str(sd / "fabric-server.jar")
                label = f"Fabric {ver}"
            elif stype == "forge":
                url, fname, _ = get_forge_server_url(ver)
                if not url:
                    self._log(f"No Forge installer found for {ver}", "error")
                    return
                dest = str(sd / "forge-server.jar")
                label = f"Forge {ver}"
            else:
                url = get_vanilla_download_url(ver)
                if not url:
                    self._log(f"No vanilla server found for {ver}", "error")
                    return
                dest = str(sd / "server.jar")
                label = f"Vanilla {ver}"
            if os.path.exists(dest):
                shutil.copy2(dest, dest + ".old")
            self._log(f"Downloading {label}...")
            ok = download_file(url, dest)
            if ok:
                self._log(f"{label} updated!", "success")
                self.root.after(0, lambda: self.update_status.configure(text="Update complete"))
            else:
                self._log(f"Update failed for {label}", "error")
                backup = dest + ".old"
                if os.path.exists(backup):
                    shutil.move(backup, dest)

        threading.Thread(target=_do, daemon=True).start()

    # ── Scheduled Restarts ──────────────────────────────────
    def _on_sched_restart_toggle(self):
        self.config["scheduled_restart"] = self.sched_restart_var.get()
        self._save_config()
        if self.sched_restart_var.get() and self.running:
            self._start_scheduled_restart_timer()
        else:
            self._stop_scheduled_restart_timer()

    def _start_scheduled_restart_timer(self):
        self._stop_scheduled_restart_timer()
        if not self.sched_restart_var.get() or not self.running:
            return
        try:
            hours = float(self.sched_hours_var.get())
        except ValueError:
            hours = 24
        ms = int(hours * 3600 * 1000)
        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + hours))
        self.root.after(0, lambda: self.sched_status.configure(text=f"Next restart: {next_time}"))
        self.scheduled_restart_timer = self.root.after(ms, self._do_scheduled_restart)

    def _cancel_all_timers(self):
        self._stop_scheduled_restart_timer()
        self._stop_periodic_backup_timer()
        self._stop_scheduled_tasks_timer()

    def _stop_scheduled_restart_timer(self):
        if self.scheduled_restart_timer:
            self.root.after_cancel(self.scheduled_restart_timer)
            self.scheduled_restart_timer = None
        self.root.after(0, lambda: self.sched_status.configure(text=""))

    def _do_scheduled_restart(self):
        if not self.running or self.stopped_manually:
            return
        self._log("Scheduled restart triggered!", "warn")
        self.stopped_manually = True
        self._stop_playit()

        def _do():
            try:
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
            except Exception:
                try:
                    self.server_process.terminate()
                except Exception:
                    pass
        threading.Thread(target=_do, daemon=True).start()
        self.root.after(3000, self._do_scheduled_restart_continue)

    def _do_scheduled_restart_continue(self):
        if self.running:
            self.root.after(2000, self._do_scheduled_restart_continue)
            return
        self.stopped_manually = False
        self._start_server()
        self.root.after(5000, self._start_scheduled_restart_timer)

    # ── Periodic Backups ─────────────────────────────────────
    def _on_periodic_backup_toggle(self):
        self.config["periodic_backup"] = self.periodic_backup_var.get()
        self._save_config()
        if self.periodic_backup_var.get() and self.running:
            self._start_periodic_backup_timer()
        else:
            self._stop_periodic_backup_timer()

    def _start_periodic_backup_timer(self):
        self._stop_periodic_backup_timer()
        if not self.periodic_backup_var.get() or not self.running:
            return
        try:
            interval = int(self.backup_interval_var.get())
        except ValueError:
            interval = 30
        ms = interval * 60 * 1000
        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + interval * 60))
        self.root.after(0, lambda: self.pbackup_status.configure(text=f"Next: {next_time}"))
        self.periodic_backup_timer = self.root.after(ms, self._do_periodic_backup)

    def _stop_periodic_backup_timer(self):
        if self.periodic_backup_timer:
            self.root.after_cancel(self.periodic_backup_timer)
            self.periodic_backup_timer = None
        self.root.after(0, lambda: self.pbackup_status.configure(text=""))

    def _do_periodic_backup(self):
        if not self.running:
            return
        self._auto_backup_world()
        self._start_periodic_backup_timer()

    # ── Ban Manager ──────────────────────────────────────────
    def _ban_player(self):
        name = self.ban_player_var.get().strip()
        if not name:
            return
        bans_file = self._server_dir() / "bans.json"
        bans = []
        if bans_file.exists():
            try:
                with open(bans_file) as f:
                    bans = json.load(f)
            except Exception:
                bans = []
        if any(e.get("name", "").lower() == name.lower() for e in bans):
            self.root.after(0, lambda: self.ban_status.configure(text=f"{name} already banned"))
            return
        bans.append({"name": name, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "source": "MCServerHost", "reason": "Banned via GUI", "expires": "forever"})
        with open(bans_file, "w") as f:
            json.dump(bans, f, indent=2)
        self.root.after(0, lambda: self.ban_status.configure(text=f"Banned {name}"))
        self.ban_player_var.set("")
        self._log(f"Player banned: {name}", "warn")
        self.root.after(0, self._refresh_bans)

    def _unban_player(self):
        name = self.ban_player_var.get().strip()
        if not name:
            return
        bans_file = self._server_dir() / "bans.json"
        if not bans_file.exists():
            self.root.after(0, lambda: self.ban_status.configure(text="No bans file"))
            return
        try:
            with open(bans_file) as f:
                bans = json.load(f)
            before = len(bans)
            bans = [e for e in bans if e.get("name", "").lower() != name.lower()]
            with open(bans_file, "w") as f:
                json.dump(bans, f, indent=2)
            if len(bans) < before:
                self.root.after(0, lambda: self.ban_status.configure(text=f"Unbanned {name}"))
                self._log(f"Player unbanned: {name}", "success")
            else:
                self.root.after(0, lambda: self.ban_status.configure(text=f"{name} not found in bans"))
        except Exception as e:
            self.root.after(0, lambda: self.ban_status.configure(text=f"Error: {e}"))
        self.ban_player_var.set("")
        self.root.after(0, self._refresh_bans)

    def _ban_ip(self):
        ip = self.ban_ip_var.get().strip()
        if not ip:
            return
        bans_file = self._server_dir() / "ip-bans.json"
        bans = []
        if bans_file.exists():
            try:
                with open(bans_file) as f:
                    bans = json.load(f)
            except Exception:
                bans = []
        if any(e.get("ip", "") == ip for e in bans):
            self.root.after(0, lambda: self.ban_ip_status.configure(text=f"{ip} already banned"))
            return
        bans.append({"ip": ip, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "source": "MCServerHost", "reason": "IP banned via GUI", "expires": "forever"})
        with open(bans_file, "w") as f:
            json.dump(bans, f, indent=2)
        self.root.after(0, lambda: self.ban_ip_status.configure(text=f"Banned IP {ip}"))
        self.ban_ip_var.set("")
        self._log(f"IP banned: {ip}", "warn")
        self.root.after(0, self._refresh_bans)

    def _unban_ip(self):
        ip = self.ban_ip_var.get().strip()
        if not ip:
            return
        bans_file = self._server_dir() / "ip-bans.json"
        if not bans_file.exists():
            self.root.after(0, lambda: self.ban_ip_status.configure(text="No IP bans file"))
            return
        try:
            with open(bans_file) as f:
                bans = json.load(f)
            before = len(bans)
            bans = [e for e in bans if e.get("ip", "") != ip]
            with open(bans_file, "w") as f:
                json.dump(bans, f, indent=2)
            if len(bans) < before:
                self.root.after(0, lambda: self.ban_ip_status.configure(text=f"Unbanned IP {ip}"))
                self._log(f"IP unbanned: {ip}", "success")
            else:
                self.root.after(0, lambda: self.ban_ip_status.configure(text=f"{ip} not found in IP bans"))
        except Exception as e:
            self.root.after(0, lambda: self.ban_ip_status.configure(text=f"Error: {e}"))
        self.ban_ip_var.set("")
        self.root.after(0, self._refresh_bans)

    # ── Log Export ───────────────────────────────────────────
    def _on_log_export_toggle(self):
        self.config["log_export"] = self.log_export_var.get()
        self._save_config()
        if self.log_export_var.get():
            self._open_log_file()
        else:
            self._close_log_file()

    def _open_log_file(self):
        logs_dir = self._server_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d")
        log_path = logs_dir / f"server_{ts}.log"
        try:
            self.log_file = open(str(log_path), "a", encoding="utf-8")
            self.root.after(0, lambda: self.log_export_status.configure(text=f"Logging to {log_path.name}"))
        except Exception as e:
            self.root.after(0, lambda: self.log_export_status.configure(text=f"Error: {e}"))

    def _close_log_file(self):
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None
        self.root.after(0, lambda: self.log_export_status.configure(text=""))

    def _write_log_line(self, msg):
        if self.log_file and not self.log_file.closed:
            try:
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                self.log_file.write(f"[{ts}] {msg}\n")
                self.log_file.flush()
                log_path = Path(self.log_file.name)
                if log_path.exists() and log_path.stat().st_size > 10 * 1024 * 1024:
                    self.log_file.close()
                    self._open_log_file()
            except Exception:
                pass

    # ── Resource Monitor ─────────────────────────────────────
    def _start_resource_monitor(self):
        self._stop_resource_monitor()
        self._update_resource_display()

    def _stop_resource_monitor(self):
        if self.resource_monitor_id:
            self.root.after_cancel(self.resource_monitor_id)
            self.resource_monitor_id = None
        self.root.after(0, lambda: self.res_lbl.configure(text=""))

    def _update_resource_display(self):
        if not self.running:
            self.root.after(0, lambda: self.res_lbl.configure(text=""))
            return
        ram_mb = self._get_server_ram()
        if ram_mb is not None:
            text = f"RAM: {ram_mb:.0f} MB"
            self.root.after(0, lambda t=text: self.res_lbl.configure(text=t))
            self._perf_ram_history.append((time.time(), ram_mb))
            if len(self._perf_ram_history) > 60:
                self._perf_ram_history = self._perf_ram_history[-60:]
        else:
            self.root.after(0, lambda: self.res_lbl.configure(text=""))
        with self._players_lock:
            pcount = len(self.online_players)
        self._perf_player_history.append((time.time(), pcount))
        if len(self._perf_player_history) > 60:
            self._perf_player_history = self._perf_player_history[-60:]
        self.root.after(0, self._update_stats_display)
        self.resource_monitor_id = self.root.after(3000, self._update_resource_display)

    def _get_server_ram(self):
        if not self.server_process or not self.running:
            return None
        pid = self.server_process.pid
        try:
            if sys.platform == "linux":
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            return int(line.split()[1]) / 1024
            elif sys.platform == "darwin":
                r = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    return int(r.stdout.strip()) / 1024
            elif sys.platform == "win32":
                r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    try:
                        reader = csv.reader([r.stdout.strip()])
                        for row in reader:
                            if len(row) >= 5:
                                mem = row[4].strip().replace(" K", "").replace(",", "")
                                return int(mem) / 1024
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    # ── Server Profiles ──────────────────────────────────────
    def _save_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            return
        self._server_dir().mkdir(parents=True, exist_ok=True)
        profile_path = self._server_dir() / "profiles" / f"{name}.json"
        profile = self.config.copy()
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        self.root.after(0, lambda: self.profile_status.configure(text=f"Saved: {name}"))
        self._log(f"Profile saved: {name}", "success")

    def _load_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            return
        profile_path = self._server_dir() / "profiles" / f"{name}.json"
        if not profile_path.exists():
            self.root.after(0, lambda: self.profile_status.configure(text=f"Profile '{name}' not found"))
            return
        try:
            with open(profile_path) as f:
                profile = json.load(f)
            self.config.update(profile)
            self._save_config()
            self.root.after(0, lambda: self.profile_status.configure(text=f"Loaded: {name}"))
            self._log(f"Profile loaded: {name}", "success")
            self.root.after(100, self._apply_config_to_ui)
        except Exception as e:
            self.root.after(0, lambda: self.profile_status.configure(text=f"Error: {e}"))

    def _delete_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            return
        profile_path = self._server_dir() / "profiles" / f"{name}.json"
        if not profile_path.exists():
            self.root.after(0, lambda: self.profile_status.configure(text=f"Profile '{name}' not found"))
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{name}'?"):
            return
        try:
            profile_path.unlink()
            self.root.after(0, lambda: self.profile_status.configure(text=f"Deleted: {name}"))
        except Exception as e:
            self.root.after(0, lambda: self.profile_status.configure(text=f"Error: {e}"))

    def _apply_config_to_ui(self):
        for key, var in self._cfg_vars.items():
            val = self.config.get(key, "")
            var.set(str(val))
        if hasattr(self, 'ram_min_var'):
            self.ram_min_var.set(self.config.get("ram_min", "1G"))
        if hasattr(self, 'ram_max_var'):
            self.ram_max_var.set(self.config.get("ram_max", "2G"))
        if hasattr(self, 'server_type_var'):
            self.server_type_var.set(self.config.get("server_type", "paper"))
            self._on_server_type_change()

    def _apply_preset(self):
        name = self.preset_var.get()
        if name == "Custom":
            return
        preset = SERVER_PRESETS.get(name)
        if not preset:
            return
        if not messagebox.askyesno("Apply Preset",
                                   f"Apply '{name}' preset?\nThis will change your server settings."):
            return
        self.config.update(preset)
        self._save_config()
        self._apply_config_to_ui()
        self.preset_status.configure(text=f"Applied: {name}")
        self._log(f"Preset applied: {name}", "success")

    def _generate_startup_script(self):
        stype = self.config.get("server_type", "paper")
        jar_map = {"paper": "paper.jar", "vanilla": "server.jar",
                   "fabric": "fabric-server.jar", "forge": "forge-server.jar"}
        jar = jar_map.get(stype, "paper.jar")
        xms = self.config.get("ram_min", "1G")
        xmx = self.config.get("ram_max", "2G")

        sh_content = f"""#!/bin/bash
# MCServerHost - Startup Script
# Server type: {stype.title()}
# Generated by MCServerHost

cd "$(dirname "$0")/.."

java -Xms{xms} -Xmx{xmx} -jar "{jar}" nogui
"""

        bat_content = f"""@echo off
REM MCServerHost - Startup Script
REM Server type: {stype.title()}
REM Generated by MCServerHost

cd /d "%~dp0.."
java -Xms{xms} -Xmx{xmx} -jar "{jar}" nogui
pause
"""

        out_dir = self._server_dir() / "scripts"
        out_dir.mkdir(parents=True, exist_ok=True)

        sh_path = out_dir / "start.sh"
        bat_path = out_dir / "start.bat"

        try:
            sh_path.write_text(sh_content)
            if sys.platform != "win32":
                sh_path.chmod(0o755)
            bat_path.write_text(bat_content)
            self._log(f"Startup scripts generated in {out_dir}", "success")
            self.root.after(0, lambda: self.script_status.configure(
                text=f"Saved to {out_dir}"))
        except Exception as e:
            self._log(f"Failed to generate scripts: {e}", "error")

    def _write_eula(self):
        (self._server_dir() / "eula.txt").write_text("eula=true\n")
        self.config["accepted_eula"] = True
        self.eula_var.set(True)
        self._save_config()

    def _on_notifications_toggle(self):
        self.config["notifications_enabled"] = self.notifications_var.get()
        self._save_config()

    def _send_notification(self, title, message):
        if not self.config.get("notifications_enabled", True):
            return
        def _do():
            try:
                system = platform.system()
                if system == "Linux":
                    subprocess.run(
                        ["notify-send", title, message],
                        capture_output=True, timeout=5
                    )
                elif system == "Darwin":
                    subprocess.run(
                        ["osascript", "-e",
                         f'display notification "{message}" with title "{title}"'],
                        capture_output=True, timeout=5
                    )
                elif system == "Windows":
                    ps_cmd = (
                        f"Add-Type -AssemblyName System.Windows.Forms;"
                        f"[System.Windows.Forms.MessageBox]::Show('{message}', '{title}')"
                    )
                    subprocess.run(
                        ["powershell", "-Command", ps_cmd],
                        capture_output=True, timeout=5
                    )
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _notify_player_join(self, player):
        self._send_notification("MCServerHost", f"{player} joined the server")

    def _notify_player_leave(self, player):
        self._send_notification("MCServerHost", f"{player} left the server")

    def _build_configs_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Configs  ")

        top = ttk.Frame(tab)
        top.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        ttk.Label(top, text="Config File Editor", style="SubHeader.TLabel").pack(anchor="w")

        body = ttk.Frame(top)
        body.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        ttk.Label(left, text="Config Files", style="Dim.TLabel",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

        self.config_tree = ttk.Treeview(left, columns=("File",), show="headings", selectmode="browse", height=10)
        self.config_tree.heading("File", text="Filename")
        self.config_tree.column("File", width=240)
        cfg_scroll = ttk.Scrollbar(left, orient="vertical", command=self.config_tree.yview)
        self.config_tree.configure(yscrollcommand=cfg_scroll.set)
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cfg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_tree.bind("<<TreeviewSelect>>", lambda e: self._load_selected_config())
        self.config_tree.tag_configure("exists", foreground=FG_GREEN)
        self.config_tree.tag_configure("missing", foreground=FG_DIM)

        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.config_status = ttk.Label(right, text="Select a config file to edit", style="Dim.TLabel")
        self.config_status.pack(anchor="w", pady=(0, 4))

        self.config_editor = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, bg=BG_ENTRY, fg=FG_MAIN, insertbackground=FG_ACCENT,
            font=("Cascadia Code", 10), relief=tk.FLAT, borderwidth=0,
            selectbackground=BG_HOVER, selectforeground=FG_BRIGHT,
            padx=10, pady=6, spacing1=1
        )
        self.config_editor.pack(fill=tk.BOTH, expand=True)

        btn_row = ttk.Frame(right)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Save", style="Green.TButton",
                   command=self._save_selected_config).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Reload", command=self._load_selected_config).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="Create", style="Blue.TButton",
                   command=self._create_config_file).pack(side=tk.LEFT)
        self.config_save_status = ttk.Label(btn_row, text="", style="Dim.TLabel")
        self.config_save_status.pack(side=tk.LEFT, padx=8)

        self._config_files = [
            "server.properties",
            "bukkit.yml",
            "spigot.yml",
            "paper-global.yml",
            "paper-world-defaults.yml",
            "config/paper-global.yml",
            "config/paper/world-defaults.yml",
        ]
        self._selected_config_path = None
        self._refresh_config_list()

    def _refresh_config_list(self):
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)
        for fname in self._config_files:
            fpath = self._server_dir() / fname
            exists = fpath.exists()
            tag = "exists" if exists else "missing"
            display = fname if exists else f"{fname}  (missing)"
            self.config_tree.insert("", "end", values=(display,), tags=(tag,), iid=fname)

    def _load_selected_config(self):
        sel = self.config_tree.selection()
        if not sel:
            return
        fname = sel[0]
        fpath = self._server_dir() / fname
        self._selected_config_path = fpath
        if not fpath.exists():
            self.config_editor.delete("1.0", tk.END)
            self.config_status.configure(text=f"{fname} does not exist — click Create to add it")
            self.config_save_status.configure(text="")
            return
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.config_status.configure(text=f"Error reading {fname}: {e}")
            return
        self.config_editor.delete("1.0", tk.END)
        self.config_editor.insert("1.0", content)
        self.config_status.configure(text=f"Editing: {fname}")
        self.config_save_status.configure(text="")

    def _save_selected_config(self):
        if not self._selected_config_path:
            return
        fpath = self._selected_config_path
        content = self.config_editor.get("1.0", tk.END).rstrip("\n") + "\n"
        try:
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
            self.config_save_status.configure(text="Saved!", style="Ok.TLabel")
            self._log(f"Config saved: {fpath.name}", "success")
        except Exception as e:
            self.config_save_status.configure(text=f"Error: {e}", style="Err.TLabel")

    def _create_config_file(self):
        if not self._selected_config_path:
            return
        fpath = self._selected_config_path
        if fpath.exists():
            messagebox.showinfo("Already Exists", f"{fpath.name} already exists.")
            return
        templates = {
            "server.properties": generate_server_properties(self.config),
            "bukkit.yml": (
                "settings:\n"
                "  allow-end: true\n"
                "  warn-on-overload: true\n"
                "  permissions-file: permissions.yml\n"
                "  update-folder: update\n"
                "  plugin-profiling: false\n"
                "  deprecated-alias: warn-on-use\n"
                "  shutdown-message: Server closed\n"
                "  minimum-api: none\n"
                "spam-limiter:\n"
                "  thrsh-perSec: 20\n"
                "  thrsh-per-10Sec: 100\n"
                "  kick-message: <red>Too many packets!</red>\n"
                "commands:\n"
                "  replace-commands:\n"
                "  - setblock\n"
                "  log: true\n"
                "  spam-limit: 200\n"
                "world-settings:\n"
                "  default:\n"
                "    mob-spawn-range: 4\n"
                "    item-despawn-rate: 6000\n"
                "    merge-radius:\n"
                "      exp: 3.0\n"
                "      item: 2.5\n"
                "    arrow-despawn-rate: 6000\n"
                "    enable-zombie-pigmen-portal-spawns: true\n"
            ),
            "spigot.yml": (
                "settings:\n"
                "  save-user-cache-on-stop-only: false\n"
                "  bungeecord: false\n"
                "  sample-count: 12\n"
                "  player-shuffle: 0\n"
                "  user-cache-size: 1000\n"
                "  moved-wrongly-threshold: 0.0625\n"
                "  moved-too-quickly-multiplier: 10.0\n"
                "  log-villager-deaths: true\n"
                "  log-npc-deaths: false\n"
                "commands:\n"
                "  spam-exclusions:\n"
                "  - skill\n"
                "  silent-commandblock: false\n"
                "  replace-commands:\n"
                "  - setblock\n"
                "  log: true\n"
                "  tab-complete: 0\n"
                "  send-namespaced: true\n"
                "advancements:\n"
                "  disable-saving: false\n"
                "  disabled:\n"
                "  - minecraft:story/disabled\n"
                "world-settings:\n"
                "  default:\n"
                "    mob-spawn-range: 4\n"
                "    item-despawn-rate: 6000\n"
                "    merge-radius:\n"
                "      exp: 3.0\n"
                "      item: 2.5\n"
                "    arrow-despawn-rate: 6000\n"
                "    enable-zombie-pigmen-portal-spawns: true\n"
            ),
            "paper-global.yml": (
                "_version: 30\n"
                "chunk-loading-advanced:\n"
                "  auto-config-send-distance: true\n"
                "  player-max-view-distance-chunk-load-rate: -1.0\n"
                "  player-max-chunk-generate-rate: -1.0\n"
                "  player-max-chunk-load-rate: -1.0\n"
                "  player-max-chunk-send-rate: -1.0\n"
                "chunk-loading-basic:\n"
                "  auto-config-send-distance: true\n"
                "  per-player-send-distance: true\n"
                "  player-max-chunk-generate-rate: -1.0\n"
                "  player-max-chunk-load-rate: -1.0\n"
                "  player-max-chunk-send-rate: -1.0\n"
                "chunk-system:\n"
                "  gen-parallelism: default\n"
                "  io-threads: auto\n"
                "  worker-threads: auto\n"
                "collisions:\n"
                "  enable-player-collisions: false\n"
                "  send-full-pos-for-hard-colliding-entities: true\n"
                "commands:\n"
                "  fix-target-selector-tag-completion: true\n"
                "  suggest-player-names-when-null-tab-completions: true\n"
                "  time-command-affects-all-worlds: false\n"
                "console:\n"
                "  enable-brigadier-completions: true\n"
                "  enable-brigadier-highlighting: true\n"
                "  has-all-permissions: false\n"
                "item-validation:\n"
                "  book:\n"
                "    author: 8192\n"
                "    page: 16384\n"
                "    title: 8192\n"
                "  display-name: 8192\n"
                "  lore-line: 8192\n"
                "  resolve-selectors-in-books: false\n"
                "logging:\n"
                "  deobfuscate-stacktraces: true\n"
                "  log-player-ip-addresses: true\n"
                "  use-rgb-for-named-text-colors: true\n"
                "messages:\n"
                "  kick:\n"
                "    authentication-servers-down: <translation:message.authserver.down>\n"
                "    connection-throttle: <red>Connection throttled! Please wait.</red>\n"
                "    connection-throttle-kick: <red>Connection throttled! Please wait.</red>\n"
                "  no-permission: <red>I'm sorry, but you do not have permission to perform this command.</red>\n"
                "  use-display-name-in-quit-message: false\n"
                "misc:\n"
                "  chat-threads:\n"
                "    chat-executor-core-size: -1\n"
                "    chat-executor-max-size: -1\n"
                "  fix-entity-position-desync: true\n"
                "  lag-compensate-block-breaking: true\n"
                "  load-permissions-yml-before-plugins: true\n"
                "  max-joins-per-tick: 5\n"
                "  region-file-cache-size: 256\n"
                "  strict-advancement-walk-check: false\n"
                "pack:\n"
                "  auto-download: false\n"
                "  auto-inject-libraries: false\n"
                "  auto-update: true\n"
                "  prevent-modifiers: false\n"
                "  repos:\n"
                "  - https://repo.papermc.io/repository/maven-public/\n"
                "player-auto-save:\n"
                "  enabled: true\n"
                "  max-per-tick: -1\n"
                "  rate: 6000\n"
                "proxies:\n"
                "  bungee-cord:\n"
                "    online-mode: true\n"
                "  proxy-protocol: false\n"
                "  velocity:\n"
                "    enabled: false\n"
                "    online-mode: false\n"
                "    secret: ''\n"
                "scoreboards:\n"
                "  save-empty-scoreboard-teams: false\n"
                "  track-plugin-scoreboards: false\n"
                "spam-limiter:\n"
                "  incoming-packet-threshold: 300\n"
                "  recipe-spam-increment: 1\n"
                "  recipe-spam-limit: 20\n"
                "  tab-spam-increment: 1\n"
                "  tab-spam-limit: 500\n"
                "timings:\n"
                "  enabled: true\n"
                "  hidden-config-entries:\n"
                "  - database\n"
                "  - proxies.velocity.secret\n"
                "  history-interval: 300\n"
                "  history-length: 3600\n"
                "  server-name: Unknown Server\n"
                "  server-name-privacy: false\n"
                "  url: https://timings.aikar.co/\n"
                "  verbose: true\n"
                "unsupported-settings:\n"
                "  allow-grindstone-overstacking: false\n"
                "  allow-headless-pistons: false\n"
                "  allow-permanent-block-break-exploits: false\n"
                "  allow-piston-duplication: false\n"
                "  perform-username-validation: true\n"
                "watchdog:\n"
                "  early-warning-delay: 10000\n"
                "  early-warning-every: 5000\n"
            ),
            "paper-world-defaults.yml": (
                "_version: 31\n"
                "ant-xray:\n"
                "  enabled: true\n"
                "  mode: ENGINE\n"
                "  lava-obfuscation: true\n"
                "  replacement-blocks:\n"
                "  - netherrack\n"
                "  - deepslate\n"
                "  - deepslate_ore\n"
                "chunks:\n"
                "  auto-save-interval: -1\n"
                "  delay-chunk-unloads-by: 10s\n"
                "  entity-per-chunk-save-limit:\n"
                "    arrow: 16\n"
                "    ender_pearl: 8\n"
                "    experience_orb: 16\n"
                "    fireball: 8\n"
                "    small_fireball: 8\n"
                "    snowball: 8\n"
                "  fixed-chunk-inhabited-time: -1\n"
                "  max-auto-save-chunks-per-tick: -1\n"
                "  region-file-format: ANVIL\n"
                "  schedule-save-auto: false\n"
                "  save-empty-chunk-sections: false\n"
                "environment:\n"
                "  disable-explosion-knockback: false\n"
                "  disable-ice-and-snow: false\n"
                "  disable-teleportation-suffocation-check: false\n"
                "  disable-thunder: false\n"
                "  fire-tick-delay: 30\n"
                "  frosted-ice:\n"
                "    delay-min: 40\n"
                "    delay-max: 60\n"
                "    enabled: true\n"
                "  generate-flat-bedrock: false\n"
                "  nether-ceiling-void-damage-height: disabled\n"
                "  optimize-explosions: false\n"
                "  portal-create-radius: 16\n"
                "  portal-search-radius: 128\n"
                "  portal-search-vanilla-dimension-scaling: true\n"
                "  treasure-maps:\n"
                "    enabled: true\n"
                "    finding-chunks-per-tick: 9\n"
                "    max-search-radius: 100\n"
                "  water-over-lava-flow-speed: 5\n"
                "entities:\n"
                "  armor-feet:\n"
                "    allow: true\n"
                "  armor-head:\n"
                "    allow: true\n"
                "  armor-legs:\n"
                "    allow: true\n"
                "  armor-torso:\n"
                "    allow: true\n"
                "  experience-orb:\n"
                "    allow: true\n"
                "  minecart-rideable:\n"
                "    allow: true\n"
                "  mob-spawner:\n"
                "    allow: true\n"
                "  axolotl:\n"
                "    survival-despawn-range:\n"
                "      ambient: 59\n"
                "      peaceful: 59\n"
                "      total: 120\n"
                "  armor-stand:\n"
                "    tick: true\n"
                "    optimize-effects: true\n"
                "  arrows:\n"
                "    allow-tnt-piston: true\n"
                "    creative-arrow-despawn-rate: 6000\n"
                "    survival-arrow-despawn-rate: 300\n"
                "  mobs:\n"
                "    can-move-off-wall: true\n"
                "    water-over-lava-flow-speed: 5\n"
                "    disable-chest-cat-detection: true\n"
                "    disable-creeper-lingering-effect: false\n"
                "    disable-player-crits: false\n"
                "    door-breaking-difficulty:\n"
                "      husk:\n"
                "      - normal\n"
                "      - hard\n"
                "      vindicator:\n"
                "      - normal\n"
                "      - hard\n"
                "      ravager:\n"
                "      - hard\n"
                "    mob-effects:\n"
                "      immune-to-wither-effect:\n"
                "        wither: true\n"
                "        skeleton: true\n"
                "    nerf-piglin-love: false\n"
                "    parrots-are-unaffected-by-player-movement: false\n"
                "    phantoms-do-not-spawn-on-creative-players: true\n"
                "    pillager-patrols:\n"
                "      disable: false\n"
                "      start: 5\n"
                "      step: 1\n"
                "      per-player: false\n"
                "    piglins-guard-chests: true\n"
                "    pillager-patrol-disable-distance: -1\n"
                "    should-remove-dragon: false\n"
                "    zombie-villager-infection-chance: default\n"
                "    zombies-target-turtle-eggs: true\n"
                "  vehicles:\n"
                "    fix-climbing-bypassing-cramming: true\n"
                "    max-entities-with-dismount: 24\n"
                "  villagers:\n"
                "    display-trading-seasons: true\n"
                "    filter-bad-tile-entities-from-falling-blocks: true\n"
                "    find-golems-looking-for-home: false\n"
                "    ignore-villager-workload-protection: false\n"
                "    max-brain-ticks: 40\n"
                "    wandering-trader:\n"
                "      spawn-chance-failure-increment: 25\n"
                "      spawn-day-max: 3\n"
                "      spawn-day-min: 1\n"
                "      spawn-minute-max: 1200\n"
                "      spawn-minute-min: 600\n"
                "    trade-rebalance: false\n"
                "unsupported-settings:\n"
                "  fix-invulnerable-end-crystal-exploit: true\n"
                "version:\n"
                "  auto-save-interval: -1\n"
                "  keep-spawn-loaded: false\n"
                "  keep-spawn-loaded-in-nether: false\n"
            ),
        }
        for key in ("config/paper-global.yml", "config/paper/world-defaults.yml"):
            alt = key.split("/")[-1]
            if key not in templates and alt in templates:
                templates[key] = templates[alt]
        content = templates.get(fpath.name, templates.get(str(fpath.relative_to(self._server_dir())), ""))
        if not content:
            content = f"# {fpath.name}\n# Edit this file manually\n"
        try:
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
            self.config_save_status.configure(text="Created!", style="Ok.TLabel")
            self._log(f"Config created: {fpath.name}", "success")
            self._refresh_config_list()
            self.config_tree.selection_set(fpath.name)
            self._load_selected_config()
        except Exception as e:
            self.config_save_status.configure(text=f"Error: {e}", style="Err.TLabel")

    def _download_world(self):
        if self.running:
            messagebox.showwarning("Server Running", "Stop the server before downloading the world.")
            return
        world_name = self.config.get("level_name", "world")
        world_dir = self._server_dir() / world_name
        if not world_dir.exists():
            messagebox.showwarning("No World", f"World directory '{world_name}' not found.")
            return
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"world_backup_{ts}.zip"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            initialfile=default_name,
            title="Save World As"
        )
        if not save_path:
            return
        self._log(f"Zipping world '{world_name}'...", "info")
        self.world_download_status.configure(text="Zipping world...")

        def _do():
            try:
                with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(str(world_dir)):
                        for file in files:
                            fp = os.path.join(root, file)
                            arcname = os.path.relpath(fp, str(world_dir))
                            zf.write(fp, arcname)
                self._log(f"World saved to {save_path}", "success")
                self.root.after(0, lambda: self.world_download_status.configure(text="Done!"))
            except Exception as e:
                self._log(f"World download failed: {e}", "error")
                self.root.after(0, lambda: self.world_download_status.configure(text="Failed"))

        threading.Thread(target=_do, daemon=True).start()

    # ── MOTD Editor ────────────────────────────────────────
    def _apply_motd(self):
        motd = self.motd_entry_var.get().strip()
        self.config["motd"] = motd
        if "motd" in self._cfg_vars:
            self._cfg_vars["motd"].set(motd)
        self._save_server_config()
        self._update_motd_preview()
        self._log(f"MOTD updated: {motd}", "success")

    def _update_motd_preview(self):
        raw = self.motd_entry_var.get()
        clean = re.sub(r'&[0-9a-fk-or]', '', raw)
        self.motd_preview_var.set(f"Preview: {clean}")

    # ── Scheduled Tasks ────────────────────────────────────
    def _load_scheduled_tasks(self):
        return self.config.get("scheduled_tasks", [])

    def _refresh_task_list(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        tasks = self._load_scheduled_tasks()
        for i, task in enumerate(tasks):
            tag = "even" if i % 2 == 0 else "odd"
            enabled = "Yes" if task.get("enabled", True) else "No"
            self.task_tree.insert("", "end", values=(task.get("command", ""),
                                  task.get("interval", 30), enabled), tags=(tag,))

    def _add_scheduled_task(self):
        cmd = self.task_cmd_var.get().strip()
        if not cmd:
            return
        try:
            interval = int(self.task_interval_var.get())
        except ValueError:
            interval = 30
        tasks = self._load_scheduled_tasks()
        tasks.append({"command": cmd, "interval": interval, "enabled": True})
        self.config["scheduled_tasks"] = tasks
        self._save_config()
        self._refresh_task_list()
        self.task_cmd_var.set("")
        self._log(f"Scheduled task added: {cmd} every {interval}min", "success")
        if self.running:
            self._start_scheduled_tasks_timer()

    def _remove_scheduled_task(self):
        sel = self.task_tree.selection()
        if not sel:
            return
        idx = self.task_tree.index(sel[0])
        tasks = self._load_scheduled_tasks()
        if idx < len(tasks):
            removed = tasks.pop(idx)
            self.config["scheduled_tasks"] = tasks
            self._save_config()
            self._refresh_task_list()
            self._log(f"Removed scheduled task: {removed.get('command', '')}", "info")
            if self.running:
                self._start_scheduled_tasks_timer()

    def _run_selected_task(self):
        sel = self.task_tree.selection()
        if not sel:
            return
        idx = self.task_tree.index(sel[0])
        tasks = self._load_scheduled_tasks()
        if idx < len(tasks):
            cmd = tasks[idx].get("command", "")
            if cmd:
                self._send_server_command(cmd)
                self._log(f"Ran scheduled task: {cmd}", "info")

    def _start_scheduled_tasks_timer(self):
        self._stop_scheduled_tasks_timer()
        if not self.running:
            return
        tasks = self._load_scheduled_tasks()
        for i, task in enumerate(tasks):
            if not task.get("enabled", True):
                continue
            try:
                interval = int(task.get("interval", 30))
            except (ValueError, TypeError):
                interval = 30
            ms = interval * 60 * 1000
            timer_id = self.root.after(ms, lambda t=task: self._execute_scheduled_task(t))
            self.scheduled_task_timers.append(timer_id)

    def _stop_scheduled_tasks_timer(self):
        for tid in self.scheduled_task_timers:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass
        self.scheduled_task_timers = []

    def _execute_scheduled_task(self, task):
        if not self.running:
            return
        cmd = task.get("command", "")
        if cmd:
            self._send_server_command(cmd)
            self._log(f"Scheduled task executed: {cmd}", "info")
        interval = int(task.get("interval", 30)) * 60 * 1000
        tid = self.root.after(interval, lambda: self._execute_scheduled_task(task))
        self.scheduled_task_timers.append(tid)

    # ── Plugin/Mod Update Checker ──────────────────────────
    def _check_plugin_updates(self):
        plugins_dir = self._server_dir() / "plugins"
        if not plugins_dir.exists():
            self.plugin_update_status.configure(text="No plugins directory found")
            return
        jars = list(plugins_dir.glob("*.jar"))
        if not jars:
            self.plugin_update_status.configure(text="No plugins installed")
            return
        self.plugin_update_status.configure(text=f"Scanning {len(jars)} plugin(s)...")
        mc_ver = self.config.get("mc_version", "")
        stype = self.config.get("server_type", "paper")

        def _do():
            results = []
            for jar in jars:
                name = jar.stem
                clean_name = re.sub(r'[-_](\d+\.\d+(\.\d+)?).*', '', name)
                clean_name = re.sub(r'[-_]v?\d+\.\d+.*', '', clean_name)
                clean_name = clean_name.replace("-", " ").replace("_", " ")
                try:
                    facets = [["project_type:plugin"]]
                    if stype == "paper":
                        facets.append(["categories:paper"])
                    facets_str = json.dumps(facets)
                    url = (f"{MODRINTH_API}/search?facets={urllib.parse.quote(facets_str)}"
                           f"&query={urllib.parse.quote(clean_name)}&limit=1")
                    if mc_ver:
                        url += f"&game_versions={urllib.parse.quote(f'[{json.dumps(mc_ver)}]')}"
                    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                    hits = data.get("hits", [])
                    if hits:
                        h = hits[0]
                        title = h.get("title", name)
                        project_id = h.get("project_id") or h.get("slug")
                        vreq = urllib.request.Request(
                            f"{MODRINTH_API}/project/{project_id}/version",
                            headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(vreq, timeout=10) as vresp:
                            versions = json.loads(vresp.read())
                        latest_ver = versions[0].get("version_number", "?") if versions else "?"
                        results.append((name, "installed", latest_ver, "Update available"))
                    else:
                        results.append((name, "installed", "?", "Not found"))
                except Exception as e:
                    results.append((name, "installed", "?", f"Error: {str(e)[:30]}"))
            self.root.after(0, lambda: self._show_plugin_update_results(results))

        threading.Thread(target=_do, daemon=True).start()

    def _show_plugin_update_results(self, results):
        for item in self.plugin_update_tree.get_children():
            self.plugin_update_tree.delete(item)
        for i, (name, installed, latest, status) in enumerate(results):
            tag_str = "has_update" if "Update" in status else ("up_to_date" if status == "Not found" else "error")
            row_tag = "even" if i % 2 == 0 else "odd"
            self.plugin_update_tree.insert("", "end",
                                          values=(name[:30], installed, latest, status),
                                          tags=(row_tag, tag_str))
        update_count = sum(1 for _, _, _, s in results if "Update" in s)
        self.plugin_update_status.configure(
            text=f"Scanned {len(results)} plugin(s), {update_count} update(s) available")

    def _check_mod_updates(self):
        mods_dir = self._server_dir() / "mods"
        if not mods_dir.exists():
            self.mod_update_status.configure(text="No mods directory found")
            return
        jars = list(mods_dir.glob("*.jar"))
        if not jars:
            self.mod_update_status.configure(text="No mods installed")
            return
        self.mod_update_status.configure(text=f"Scanning {len(jars)} mod(s)...")
        mc_ver = self.config.get("mc_version", "")
        stype = self.config.get("server_type", "fabric")

        def _do():
            results = []
            for jar in jars:
                name = jar.stem
                clean_name = re.sub(r'[-_](\d+\.\d+(\.\d+)?).*', '', name)
                clean_name = re.sub(r'[-_]v?\d+\.\d+.*', '', clean_name)
                clean_name = clean_name.replace("-", " ").replace("_", " ")
                try:
                    facets = [["project_type:mod"]]
                    if stype == "fabric":
                        facets.append(["categories:fabric"])
                    elif stype == "forge":
                        facets.append(["categories:forge"])
                    facets_str = json.dumps(facets)
                    url = (f"{MODRINTH_API}/search?facets={urllib.parse.quote(facets_str)}"
                           f"&query={urllib.parse.quote(clean_name)}&limit=1")
                    if mc_ver:
                        url += f"&game_versions={urllib.parse.quote(f'[{json.dumps(mc_ver)}]')}"
                    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                    hits = data.get("hits", [])
                    if hits:
                        h = hits[0]
                        project_id = h.get("project_id") or h.get("slug")
                        vreq = urllib.request.Request(
                            f"{MODRINTH_API}/project/{project_id}/version",
                            headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(vreq, timeout=10) as vresp:
                            versions = json.loads(vresp.read())
                        latest_ver = versions[0].get("version_number", "?") if versions else "?"
                        results.append((name, "installed", latest_ver, "Update available"))
                    else:
                        results.append((name, "installed", "?", "Not found"))
                except Exception as e:
                    results.append((name, "installed", "?", f"Error: {str(e)[:30]}"))
            self.root.after(0, lambda: self._show_mod_update_results(results))

        threading.Thread(target=_do, daemon=True).start()

    def _show_mod_update_results(self, results):
        for item in self.mod_update_tree.get_children():
            self.mod_update_tree.delete(item)
        for i, (name, installed, latest, status) in enumerate(results):
            tag_str = "has_update" if "Update" in status else ("up_to_date" if status == "Not found" else "error")
            row_tag = "even" if i % 2 == 0 else "odd"
            self.mod_update_tree.insert("", "end",
                                       values=(name[:30], installed, latest, status),
                                       tags=(row_tag, tag_str))
        update_count = sum(1 for _, _, _, s in results if "Update" in s)
        self.mod_update_status.configure(
            text=f"Scanned {len(results)} mod(s), {update_count} update(s) available")

    # ── Player Statistics ──────────────────────────────────
    def _player_stats_path(self):
        return self._server_dir() / "player_stats.json"

    def _load_player_stats(self):
        path = self._player_stats_path()
        if path.exists():
            try:
                with open(path) as f:
                    self._player_stats_data = json.load(f)
            except Exception:
                self._player_stats_data = {}
        else:
            self._player_stats_data = {}
        self._refresh_player_stats_ui()

    def _save_player_stats(self):
        path = self._player_stats_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(self._player_stats_data, f, indent=2)
        except Exception:
            pass

    def _track_player_join(self, player):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._player_stats_lock:
            if player not in self._player_stats_data:
                self._player_stats_data[player] = {"joins": 0, "total_seconds": 0, "last_seen": now}
            self._player_stats_data[player]["joins"] += 1
            self._player_stats_data[player]["last_seen"] = now
            self._player_session_starts[player] = time.time()
        self._save_player_stats()

    def _track_player_leave(self, player):
        with self._player_stats_lock:
            start = self._player_session_starts.pop(player, None)
            if start:
                elapsed = time.time() - start
                if player not in self._player_stats_data:
                    self._player_stats_data[player] = {"joins": 0, "total_seconds": 0, "last_seen": ""}
                self._player_stats_data[player]["total_seconds"] += elapsed
                self._player_stats_data[player]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if start:
            self._save_player_stats()

    def _refresh_player_stats(self):
        self._load_player_stats()

    def _refresh_player_stats_ui(self):
        for item in self.player_stats_tree.get_children():
            self.player_stats_tree.delete(item)
        with self._player_stats_lock:
            snapshot = dict(self._player_stats_data)
        sorted_players = sorted(snapshot.items(),
                                key=lambda x: x[1].get("last_seen", ""), reverse=True)
        for i, (player, stats) in enumerate(sorted_players):
            joins = stats.get("joins", 0)
            total = stats.get("total_seconds", 0)
            hours, rem = divmod(int(total), 3600)
            minutes, _ = divmod(rem, 60)
            playtime = f"{hours}h {minutes}m"
            last = stats.get("last_seen", "Unknown")
            tag = "even" if i % 2 == 0 else "odd"
            self.player_stats_tree.insert("", "end", values=(player, joins, playtime, last), tags=(tag,))
        self.player_stats_status.configure(text=f"{len(sorted_players)} player(s) tracked")

    def _clear_player_stats(self):
        if not messagebox.askyesno("Clear Stats", "Clear all player statistics? This cannot be undone."):
            return
        with self._player_stats_lock:
            self._player_stats_data = {}
        self._save_player_stats()
        self._refresh_player_stats_ui()
        self._log("Player statistics cleared", "info")

    # ── Backup Verification ────────────────────────────────
    def _verify_backup(self, zip_path):
        try:
            with zipfile.ZipFile(str(zip_path), 'r') as zf:
                bad = zf.testzip()
                if bad is not None:
                    return False, f"Corrupt file: {bad}"
                count = len(zf.infolist())
                total_size = sum(info.file_size for info in zf.infolist())
                return True, f"OK — {count} files, {total_size:,} bytes uncompressed"
        except zipfile.BadZipFile:
            return False, "Not a valid ZIP file"
        except Exception as e:
            return False, str(e)

    # ── Widget Visibility Toggle ───────────────────────────
    def _toggle_widget_visibility(self):
        for key, var in self._widget_vis.items():
            self.config[f"widget_visible_{key}"] = var.get()
        self._save_config()
        parent = self._stat_cards_frame.master
        for w in parent.winfo_children():
            w.pack_forget()
        if self._widget_vis["cards"].get():
            self._stat_cards_frame.pack(in_=parent, fill=tk.X, pady=(8, 10))
        if self._widget_vis["ram"].get():
            self._ram_label.pack(in_=parent, anchor="w", pady=(6, 2))
            self._ram_canvas.pack(in_=parent, fill=tk.X, pady=(0, 6))
        if self._widget_vis["tps"].get():
            self._tps_label.pack(in_=parent, anchor="w", pady=(6, 2))
            self._tps_canvas.pack(in_=parent, fill=tk.X)

    def _on_close(self):
        self.stopped_manually = True
        self._cancel_all_timers()
        self._stop_resource_monitor()
        if self._log_flush_id:
            try:
                self.root.after_cancel(self._log_flush_id)
            except Exception:
                pass
            self._log_flush_id = None
        self._flush_log_queue()
        self._close_log_file()
        if self.running:
            if not messagebox.askokcancel("Quit", "Server is running. Stop it and quit?"):
                return
            self._stop_server()
            try:
                self.server_process.wait(timeout=5)
            except Exception:
                try:
                    self.server_process.kill()
                    self.server_process.wait(timeout=3)
                except Exception:
                    pass
        self._stop_playit()
        self._save_server_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MCServerHost().run()
