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
    return subprocess.CompletedProcess(cmd=[], returncode=1, stdout="", stderr="no package manager found")


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
                _install_package("python3-tk")
            return True
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
    print("[bootstrap] Java 17+ not found. Installing OpenJDK...")

    if system == "Linux":
        if pm in ("apt", "apt-get"):
            r = _install_package("openjdk-21-jre-headless")
            if r.returncode != 0:
                _install_package("openjdk-17-jre-headless")
            return True
        elif pm in ("dnf", "yum"):
            r = _install_package("java-21-openjdk-headless")
            if r.returncode != 0:
                _install_package("java-17-openjdk-headless")
            return True
        elif pm == "pacman":
            return _install_package("jre-openjdk").returncode == 0
        elif pm == "zypper":
            return _install_package("java-21-openjdk-headless").returncode == 0
    elif system == "Darwin":
        return _install_package("openjdk").returncode == 0
    elif system == "Windows":
        print("[bootstrap] Download Java 17+ from https://adoptium.net")
        return False
    return False


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
    if not java_ver or java_ver < 17:
        if _install_java():
            java_ver2, java_info2 = check_java()
            if java_ver2 and java_ver2 >= 17:
                print(f"[bootstrap] Java: OK ({java_info2})")
            else:
                print("[bootstrap] Java installed but may need a restart or PATH update.")
        else:
            print("[bootstrap] Java not installed. Install Java 17+ from https://adoptium.net")
            print("[bootstrap] You can still open the app, but need Java to run the server.")
    else:
        print(f"[bootstrap] Java: OK ({java_info})")

    print(f"{'=' * 50}\n")


# ── Phase 1: Bootstrap before any GUI imports ──────────────
if __name__ == "__main__":
    bootstrap()

# ── Phase 2: GUI imports (tkinter guaranteed installed) ─────
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
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

# ── Constants ───────────────────────────────────────────────
APP_NAME = "MCServerHost"
VERSION = "1.0.0"
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

BG_DARK = "#2b2b2b"
BG_MID = "#353535"
BG_LIGHT = "#454545"
FG_MAIN = "#e0e0e0"
FG_ACCENT = "#6ea8fe"
FG_GREEN = "#6bc76e"
FG_RED = "#e06060"
FG_YELLOW = "#d4a84a"
FG_DIM = "#808080"

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
        return "Download from https://adoptium.net"
    elif system == "Darwin":
        return "Install with: brew install openjdk (Homebrew)"
    return "Install Java 17+ from https://adoptium.net"


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
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress_cb and total > 0:
                        progress_cb(done, total)
        return True
    except Exception:
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
        "require-resource-pack": "false",
        "resource-pack-prompt": "",
        "resource-pack-id": "",
        "resource-pack": "",
        "resource-pack-sha1": "",
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
        self.root.geometry("1020x720")
        self.root.minsize(860, 600)
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

        self.config = self._load_config()
        self._setup_styles()
        self._build_ui()
        self.root.after(200, self._initial_checks)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        return cfg

    def _save_config(self):
        SERVER_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        BG_ACTIVE = "#404040"

        s.configure(".", background=BG_DARK, foreground=FG_MAIN, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG_DARK)
        s.configure("TLabel", background=BG_DARK, foreground=FG_MAIN)
        s.configure("Card.TFrame", background=BG_MID)
        s.configure("Card.TLabel", background=BG_MID, foreground=FG_MAIN)
        s.configure("Header.TLabel", background=BG_DARK, foreground=FG_MAIN, font=("Segoe UI", 15, "bold"))
        s.configure("SubHeader.TLabel", background=BG_MID, foreground=FG_MAIN, font=("Segoe UI", 11, "bold"))
        s.configure("Status.TLabel", background=BG_DARK, foreground=FG_GREEN, font=("Segoe UI", 11))
        s.configure("Off.TLabel", background=BG_DARK, foreground=FG_RED, font=("Segoe UI", 11))
        s.configure("Dim.TLabel", background=BG_DARK, foreground=FG_DIM)
        s.configure("CardDim.TLabel", background=BG_MID, foreground=FG_DIM)
        s.configure("Ok.TLabel", background=BG_MID, foreground=FG_GREEN)
        s.configure("Err.TLabel", background=BG_MID, foreground=FG_RED)
        s.configure("Addr.TLabel", background=BG_MID, foreground=FG_GREEN, font=("Consolas", 13, "bold"))

        s.configure("TButton", background=BG_LIGHT, foreground=FG_MAIN, padding=(12, 6),
                     relief="flat", borderwidth=0)
        s.map("TButton", background=[("active", BG_ACTIVE), ("pressed", BG_ACTIVE)])
        s.configure("Green.TButton", background=FG_GREEN, foreground=BG_DARK,
                     font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0)
        s.map("Green.TButton", background=[("active", "#5aad5a"), ("pressed", "#5aad5a")])
        s.configure("Red.TButton", background=FG_RED, foreground=BG_DARK,
                     font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0)
        s.map("Red.TButton", background=[("active", "#c45050"), ("pressed", "#c45050")])
        s.configure("Blue.TButton", background=FG_ACCENT, foreground=BG_DARK,
                     font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0)
        s.map("Blue.TButton", background=[("active", "#5a93d6"), ("pressed", "#5a93d6")])

        s.configure("TNotebook", background=BG_DARK, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_MID, foreground=FG_DIM, padding=(16, 8),
                     borderwidth=0, relief="flat")
        s.map("TNotebook.Tab", background=[("selected", BG_ACTIVE)], foreground=[("selected", FG_MAIN)])

        s.configure("TCheckbutton", background=BG_DARK, foreground=FG_MAIN)
        s.configure("TEntry", fieldbackground=BG_MID, foreground=FG_MAIN, insertcolor=FG_MAIN,
                     borderwidth=0, relief="flat")
        s.configure("TSpinbox", fieldbackground=BG_MID, foreground=FG_MAIN, borderwidth=0)
        s.configure("TCombobox", fieldbackground=BG_MID, foreground=FG_MAIN, borderwidth=0)
        s.map("TCombobox", fieldbackground=[("readonly", BG_MID)])
        s.configure("Horizontal.TProgressbar", background=FG_ACCENT, troughcolor=BG_MID, borderwidth=0)
        s.configure("TRadiobutton", background=BG_DARK, foreground=FG_MAIN)
        s.configure("TSeparator", background=BG_LIGHT)

    def _build_ui(self):
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        hdr = ttk.Frame(main)
        hdr.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(hdr, text=APP_NAME, style="Header.TLabel").pack(side=tk.LEFT)
        self.res_lbl = ttk.Label(hdr, text="", style="Dim.TLabel")
        self.res_lbl.pack(side=tk.LEFT, padx=12)
        self.status_lbl = ttk.Label(hdr, text="  Offline", style="Off.TLabel")
        self.status_lbl.pack(side=tk.RIGHT, padx=4)
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self._build_setup_tab()
        self._build_server_tab()
        self._build_console_tab()
        self._build_plugins_tab()
        self._build_network_tab()

    # ── Setup Tab ───────────────────────────────────────────
    def _build_setup_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Setup  ")
        frm = ttk.Frame(tab)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

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

        top = ttk.Frame(tab)
        top.pack(fill=tk.X, padx=12, pady=(12, 0))
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

        players_row = ttk.Frame(top)
        players_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(players_row, text="Online Players:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.players_lbl = ttk.Label(players_row, text="None", style="CardDim.TLabel")
        self.players_lbl.pack(side=tk.LEFT, padx=8)

        btn_row = ttk.Frame(tab)
        btn_row.pack(fill=tk.X, padx=12, pady=(0, 8))
        ttk.Button(btn_row, text="Save Config", command=self._save_server_config).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Accept EULA", command=self._write_eula).pack(side=tk.LEFT, padx=6)

        props = ttk.Frame(tab)
        props.pack(fill=tk.X, padx=12, pady=(0, 10))
        col1 = ttk.Frame(props)
        col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
        col2 = ttk.Frame(props)
        col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 0))

        def _field(parent, label, key, values=None, width=12):
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=18, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(self.config.get(key, "")))
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

        ttk.Separator(tab, orient="horizontal").pack(fill=tk.X, padx=12, pady=8)
        tools = ttk.Frame(tab)
        tools.pack(fill=tk.X, padx=12, pady=(0, 8))

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

        wl_frame = ttk.Frame(tools)
        wl_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(wl_frame, text="Whitelist / OP Manager", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        wl_row = ttk.Frame(wl_frame)
        wl_row.pack(fill=tk.X)
        self.wl_player_var = tk.StringVar()
        ttk.Entry(wl_row, textvariable=self.wl_player_var, width=20).pack(side=tk.LEFT)
        ttk.Button(wl_row, text="+ Whitelist", command=self._add_whitelist_player).pack(side=tk.LEFT, padx=4)
        ttk.Button(wl_row, text="- Whitelist", command=self._remove_whitelist_player).pack(side=tk.LEFT, padx=4)
        ttk.Label(wl_row, text="  ", style="Dim.TLabel").pack(side=tk.LEFT)
        ttk.Button(wl_row, text="+ OP", command=self._add_op_player).pack(side=tk.LEFT, padx=4)
        ttk.Button(wl_row, text="- OP", command=self._remove_op_player).pack(side=tk.LEFT, padx=4)
        self.wl_status = ttk.Label(wl_row, text="", style="Dim.TLabel")
        self.wl_status.pack(side=tk.LEFT, padx=8)

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
        ban_frame = ttk.Frame(tools)
        ban_frame.pack(fill=tk.X)
        ttk.Label(ban_frame, text="Ban Manager", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ban_row = ttk.Frame(ban_frame)
        ban_row.pack(fill=tk.X)
        self.ban_player_var = tk.StringVar()
        ttk.Entry(ban_row, textvariable=self.ban_player_var, width=20).pack(side=tk.LEFT)
        ttk.Button(ban_row, text="Ban Player", style="Red.TButton",
                   command=self._ban_player).pack(side=tk.LEFT, padx=4)
        ttk.Button(ban_row, text="Unban Player",
                   command=self._unban_player).pack(side=tk.LEFT, padx=4)
        ttk.Label(ban_row, text="  IP:", style="Dim.TLabel").pack(side=tk.LEFT, padx=(8, 2))
        self.ban_ip_var = tk.StringVar()
        ttk.Entry(ban_row, textvariable=self.ban_ip_var, width=15).pack(side=tk.LEFT)
        ttk.Button(ban_row, text="Ban IP",
                   command=self._ban_ip).pack(side=tk.LEFT, padx=4)
        ttk.Button(ban_row, text="Unban IP",
                   command=self._unban_ip).pack(side=tk.LEFT, padx=4)
        self.ban_status = ttk.Label(ban_row, text="", style="Dim.TLabel")
        self.ban_status.pack(side=tk.LEFT, padx=8)

    # ── Console Tab ──────────────────────────────────────────
    def _build_console_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Console  ")

        ctrl = ttk.Frame(tab)
        ctrl.pack(fill=tk.X, padx=12, pady=(12, 0))
        ttk.Label(ctrl, text="Command:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.cmd_entry = ttk.Entry(ctrl, width=60)
        self.cmd_entry.pack(side=tk.LEFT, padx=(6, 4), fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", lambda e: self._send_command())
        ttk.Button(ctrl, text="Send", style="Blue.TButton", command=self._send_command).pack(side=tk.LEFT)

        self.console = scrolledtext.ScrolledText(
            tab, wrap=tk.WORD, bg="#1e1e1e", fg=FG_MAIN, insertbackground=FG_MAIN,
            font=("Consolas", 10), relief=tk.FLAT, borderwidth=0, state="disabled"
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.console.tag_config("info", foreground=FG_MAIN)
        self.console.tag_config("warn", foreground=FG_YELLOW)
        self.console.tag_config("error", foreground=FG_RED)
        self.console.tag_config("success", foreground=FG_GREEN)
        self.console.tag_config("cmd", foreground=FG_ACCENT)

        clear_row = ttk.Frame(tab)
        clear_row.pack(fill=tk.X, padx=12, pady=(0, 8))
        ttk.Button(clear_row, text="Clear Console", command=self._clear_console).pack(side=tk.LEFT)
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

    # ── Plugins Tab ──────────────────────────────────────────
    def _build_plugins_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Plugins  ")
        frm = ttk.Frame(tab)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Plugin Manager (Modrinth)", style="SubHeader.TLabel").pack(anchor="w")
        ttk.Label(frm, text="Search and install plugins for Paper/Fabric servers.",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 6))

        search_row = ttk.Frame(frm)
        search_row.pack(fill=tk.X, pady=(0, 6))
        self.plugin_search_var = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.plugin_search_var, width=40).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(search_row, text="Search", style="Blue.TButton",
                   command=self._search_plugins).pack(side=tk.LEFT)
        self.plugin_search_btn = search_row.winfo_children()[-1]
        self.plugin_status = ttk.Label(search_row, text="", style="Dim.TLabel")
        self.plugin_status.pack(side=tk.LEFT, padx=8)

        list_frame = ttk.Frame(frm)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        cols = ("Name", "Downloads", "Description")
        self.plugin_tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.plugin_tree.heading("Name", text="Name")
        self.plugin_tree.heading("Downloads", text="Downloads")
        self.plugin_tree.heading("Description", text="Description")
        self.plugin_tree.column("Name", width=180)
        self.plugin_tree.column("Downloads", width=90)
        self.plugin_tree.column("Description", width=400)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.plugin_tree.yview)
        self.plugin_tree.configure(yscrollcommand=scrollbar.set)
        self.plugin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Install Selected", style="Green.TButton",
                   command=self._install_plugin).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Open Plugins Folder",
                   command=self._open_plugins_folder).pack(side=tk.LEFT, padx=8)
        self.plugin_install_status = ttk.Label(btn_row, text="", style="Dim.TLabel")
        self.plugin_install_status.pack(side=tk.LEFT, padx=8)

        self._plugin_results = []

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
            params = {
                "query": query,
                "limit": 20,
            }
            if mc_ver:
                params["game_versions"] = f'["{mc_ver}"]'
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
        for h in hits:
            name = h.get("title", "?")
            dl = h.get("downloads", 0)
            desc = (h.get("description") or "")[:80]
            self.plugin_tree.insert("", "end", values=(name, f"{dl:,}", desc))
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
                plugins_dir = SERVER_DIR / "plugins"
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
        plugins_dir = SERVER_DIR / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(plugins_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(plugins_dir)])
        else:
            subprocess.run(["xdg-open", str(plugins_dir)])

    # ── Network Tab ─────────────────────────────────────────
    def _build_network_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Network  ")
        frm = ttk.Frame(tab)
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

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

    # ── Helpers ─────────────────────────────────────────────
    def _info_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.lbl = ttk.Label(card, text="Checking...", style="CardDim.TLabel")
        card.lbl.pack(side=tk.LEFT, padx=12, pady=8)
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
        with self._log_lock:
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
        threading.Thread(target=self._do_initial_checks, daemon=True).start()

    def _do_initial_checks(self):
        java_ver, java_desc = check_java()
        if java_ver and java_ver >= 17:
            self.root.after(0, lambda: self._set_card(self.java_card, f"Java: OK - {java_desc}", True))
        else:
            hint = get_java_install_hint()
            self.root.after(0, lambda: self._set_card(self.java_card, f"Java: MISSING - {hint}", False))
        self.java_ok = java_ver is not None and java_ver >= 17

        self._check_server_installed()

        if PLAYIT_BIN.exists():
            self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Downloaded", True))
            self.playit_ready = True
        else:
            self.root.after(0, lambda: self._set_card(self.playit_card, "playit.gg: Not downloaded", False))
            self.playit_ready = False

        self._fetch_versions()
        self._fetch_ip()

    def _fetch_versions(self):
        stype = self.server_type_var.get()
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

    def _on_server_type_change(self):
        stype = self.server_type_var.get()
        labels = {"paper": "Paper MC Version", "vanilla": "Vanilla Version",
                  "fabric": "Fabric MC Version", "forge": "Forge MC Version"}
        self.version_label.configure(text=labels.get(stype, "Version"))
        self._check_server_installed()
        self._fetch_versions()

    def _check_server_installed(self):
        stype = self.server_type_var.get()
        jar_map = {"paper": PAPER_JAR, "vanilla": VANILLA_JAR, "fabric": FABRIC_JAR, "forge": FORGE_JAR}
        jar = jar_map.get(stype, PAPER_JAR)
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
        if stype == "paper":
            url, build_id, fname = get_paper_build_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log("No stable Paper build found for this version", "error")
                return
            dest = str(PAPER_JAR)
            label = f"Paper {version} build {build_id}"
        elif stype == "fabric":
            url, fname = get_fabric_server_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log(f"No Fabric server found for {version}", "error")
                return
            dest = str(FABRIC_JAR)
            label = f"Fabric {version}"
        elif stype == "forge":
            url, fname, label_text = get_forge_server_url(version)
            if not url:
                self._schedule_ui(lambda: self.dl_btn.configure(state="normal"))
                self._log(f"No Forge installer found for {version}", "error")
                return
            installer_dest = str(SERVER_DIR / "forge-installer.jar")
            SERVER_DIR.mkdir(parents=True, exist_ok=True)
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
                        cwd=str(SERVER_DIR), capture_output=True, text=True, timeout=600
                    )
                    if r.returncode == 0:
                        forge_jar = None
                        for f in SERVER_DIR.glob("forge-*server*.jar"):
                            forge_jar = f
                            break
                        if not forge_jar:
                            for f in SERVER_DIR.glob("forge-*.jar"):
                                if "installer" not in f.name:
                                    forge_jar = f
                                    break
                        if forge_jar:
                            shutil.copy2(str(forge_jar), str(FORGE_JAR))
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
            dest = str(VANILLA_JAR)
            fname = "server.jar"
            label = f"Vanilla {version}"

        SERVER_DIR.mkdir(parents=True, exist_ok=True)
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
            ok = download_file(url, str(PLAYIT_BIN))
            if ok:
                sha_url = url + ".sha256"
                try:
                    req = urllib.request.Request(sha_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        expected = resp.read().decode().strip().split()[0]
                    h = hashlib.sha256(PLAYIT_BIN.read_bytes()).hexdigest()
                    if h != expected:
                        self.root.after(0, lambda: self._log(
                            "playit.gg hash mismatch - download may be corrupted", "error"))
                        self.root.after(0, lambda: self._set_card(
                            self.playit_card, "playit.gg: Hash mismatch", False))
                        return
                except Exception:
                    pass
                if sys.platform != "win32":
                    os.chmod(str(PLAYIT_BIN), 0o755)
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
        jar_map = {"paper": PAPER_JAR, "vanilla": VANILLA_JAR, "fabric": FABRIC_JAR, "forge": FORGE_JAR}
        jar = jar_map.get(stype, PAPER_JAR)
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

        SERVER_DIR.mkdir(parents=True, exist_ok=True)
        PROPS_FILE.write_text(generate_server_properties(self.config))

        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

        self._log(f"Starting {stype.title()} server...", "info")

        if self.auto_backup_var.get():
            self._auto_backup_world()

        java_ver, _ = check_java()
        if not java_ver or java_ver < 17:
            self._log("Java 17+ is required! Please install Java.", "error")
            return

        xms = self.config.get("ram_min", "1G")
        xmx = self.config.get("ram_max", "2G")
        cmd = ["java", f"-Xms{xms}", f"-Xmx{xmx}", "-jar", str(jar), "nogui"]

        try:
            self.server_process = subprocess.Popen(
                cmd, cwd=str(SERVER_DIR), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            self.running = True
            self.server_ready = False
            self.stopped_manually = False
            self.online_players.clear()
            self.root.after(0, self._update_players_display)
            self.root.after(0, lambda: self.start_btn.configure(state="disabled"))
            self.root.after(0, lambda: self.stop_btn.configure(state="normal"))
            self.root.after(0, lambda: self._set_status("Starting...", True))
            threading.Thread(target=self._read_server_output, daemon=True).start()
            self._start_resource_monitor()
            if self.sched_restart_var.get():
                self.root.after(2000, self._start_scheduled_restart_timer)
            if self.periodic_backup_var.get():
                self.root.after(2000, self._start_periodic_backup_timer)
            if self.use_playit_var.get():
                self.root.after(2000, self._start_playit)
        except Exception as e:
            self._log(f"Failed to start server: {e}", "error")
            self.running = False

    def _read_server_output(self):
        proc = self.server_process
        if not proc or not proc.stdout:
            return
        start_time = time.time()
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
            self._log(line, tag)
        rc = proc.wait()
        uptime = time.time() - start_time
        self._log(f"Server stopped (exit code {rc})", "warn" if rc == 0 else "error")
        self.running = False
        self.server_ready = False
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
        crash_dir = SERVER_DIR / "crash-reports"
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
                [str(PLAYIT_BIN)], cwd=str(SERVER_DIR), stdout=subprocess.PIPE,
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
        for key, var in self._cfg_vars.items():
            val = var.get()
            if key in ("server_port", "max_players", "view_distance", "spawn_protection"):
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
            self.online_players.add(player)
            self.root.after(0, self._update_players_display)
        elif leave_match:
            player = leave_match.group(1)
            self.online_players.discard(player)
            self.root.after(0, self._update_players_display)

    def _update_players_display(self):
        if self.online_players:
            self.players_lbl.configure(text=", ".join(sorted(self.online_players)))
        else:
            self.players_lbl.configure(text="None")

    def _auto_backup_world(self):
        world_dir = SERVER_DIR / self.config.get("level_name", "world")
        if not world_dir.exists():
            return
        backups_dir = SERVER_DIR / "backups"
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
            self.root.after(0, lambda: self.backup_status.configure(text=f"Last backup: {ts}"))
            self._rotate_backups()
        except Exception as e:
            self._log(f"Backup failed: {e}", "error")

    def _rotate_backups(self):
        backups_dir = SERVER_DIR / "backups"
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
        backups_dir = SERVER_DIR / "backups"
        if not backups_dir.exists():
            messagebox.showinfo("No Backups", "No backups found.")
            return
        backups = sorted(backups_dir.glob("world_backup_*.zip"), reverse=True)
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
        world_dir = SERVER_DIR / world_name
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
        wl_file = SERVER_DIR / "whitelist.json"
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

    def _remove_whitelist_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        wl_file = SERVER_DIR / "whitelist.json"
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

    def _add_op_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        ops_file = SERVER_DIR / "ops.json"
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

    def _remove_op_player(self):
        name = self.wl_player_var.get().strip()
        if not name:
            return
        ops_file = SERVER_DIR / "ops.json"
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
            if stype == "paper":
                url, build_id, fname = get_paper_build_url(ver)
                if not url:
                    self._log("No stable Paper build found", "error")
                    return
                dest = str(PAPER_JAR)
                label = f"Paper {ver} build {build_id}"
            else:
                url = get_vanilla_download_url(ver)
                if not url:
                    self._log(f"No vanilla server found for {ver}", "error")
                    return
                dest = str(VANILLA_JAR)
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
        bans_file = SERVER_DIR / "bans.json"
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

    def _unban_player(self):
        name = self.ban_player_var.get().strip()
        if not name:
            return
        bans_file = SERVER_DIR / "bans.json"
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

    def _ban_ip(self):
        ip = self.ban_ip_var.get().strip()
        if not ip:
            return
        bans_file = SERVER_DIR / "ip-bans.json"
        bans = []
        if bans_file.exists():
            try:
                with open(bans_file) as f:
                    bans = json.load(f)
            except Exception:
                bans = []
        if any(e.get("ip", "") == ip for e in bans):
            self.root.after(0, lambda: self.ban_status.configure(text=f"{ip} already banned"))
            return
        bans.append({"ip": ip, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "source": "MCServerHost", "reason": "IP banned via GUI", "expires": "forever"})
        with open(bans_file, "w") as f:
            json.dump(bans, f, indent=2)
        self.root.after(0, lambda: self.ban_status.configure(text=f"Banned IP {ip}"))
        self.ban_ip_var.set("")
        self._log(f"IP banned: {ip}", "warn")

    def _unban_ip(self):
        ip = self.ban_ip_var.get().strip()
        if not ip:
            return
        bans_file = SERVER_DIR / "ip-bans.json"
        if not bans_file.exists():
            self.root.after(0, lambda: self.ban_status.configure(text="No IP bans file"))
            return
        try:
            with open(bans_file) as f:
                bans = json.load(f)
            before = len(bans)
            bans = [e for e in bans if e.get("ip", "") != ip]
            with open(bans_file, "w") as f:
                json.dump(bans, f, indent=2)
            if len(bans) < before:
                self.root.after(0, lambda: self.ban_status.configure(text=f"Unbanned IP {ip}"))
                self._log(f"IP unbanned: {ip}", "success")
            else:
                self.root.after(0, lambda: self.ban_status.configure(text=f"{ip} not found in IP bans"))
        except Exception as e:
            self.root.after(0, lambda: self.ban_status.configure(text=f"Error: {e}"))
        self.ban_ip_var.set("")

    # ── Log Export ───────────────────────────────────────────
    def _on_log_export_toggle(self):
        self.config["log_export"] = self.log_export_var.get()
        self._save_config()
        if self.log_export_var.get():
            self._open_log_file()
        else:
            self._close_log_file()

    def _open_log_file(self):
        logs_dir = SERVER_DIR / "logs"
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
                if self.log_file.tell() > 10 * 1024 * 1024:
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
        else:
            self.root.after(0, lambda: self.res_lbl.configure(text=""))
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
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        profile_path = PROFILES_DIR / f"{name}.json"
        profile = self.config.copy()
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        self.root.after(0, lambda: self.profile_status.configure(text=f"Saved: {name}"))
        self._log(f"Profile saved: {name}", "success")

    def _load_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            return
        profile_path = PROFILES_DIR / f"{name}.json"
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
        profile_path = PROFILES_DIR / f"{name}.json"
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

java -Xms{xms} -Xmx{xmx} -jar {jar} nogui
"""

        bat_content = f"""@echo off
REM MCServerHost - Startup Script
REM Server type: {stype.title()}
REM Generated by MCServerHost

cd /d "%~dp0.."
java -Xms{xms} -Xmx{xmx} -jar {jar} nogui
pause
"""

        out_dir = SERVER_DIR / "scripts"
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
        EULA_FILE.write_text("eula=true\n")
        self.config["accepted_eula"] = True
        self.eula_var.set(True)
        self._save_config()

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
        self._close_log_file()
        if self.running:
            if not messagebox.askokcancel("Quit", "Server is running. Stop it and quit?"):
                return
            self._stop_server()
            time.sleep(1)
        self._stop_playit()
        self._save_server_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MCServerHost().run()
