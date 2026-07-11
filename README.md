# MCServerHost

A single-file Python application for hosting a Minecraft server on your own machine. Players join instantly through Minecraft Multiplayer. No networking knowledge required.

## Requirements

- Python 3.8 or newer
- Java 17 or newer (auto-installed on supported systems if missing)

The application will automatically install Python's tkinter library and Java on first run if they are not already present.

## Quick Start

**Linux / macOS:**

```bash
chmod +x run.sh
./run.sh
```

**Windows:**

```
run.bat
```

Or run directly:

```bash
python3 mcserverhost.py
```

## How It Works

1. The app checks for Java and tkinter, installing them if needed.
2. Select your server type and Minecraft version in the Setup tab.
3. Click "Download / Update Server" to fetch the server files.
4. Go to the Server tab and click "Start Server".
5. Your server address appears in the Network tab. Share it with your friends.

## Server Types

| Type | Description |
|------|-------------|
| Paper MC | Recommended. High-performance fork of Spigot with plugin support. |
| Vanilla | Official Mojang server. No modifications. |
| Fabric | Lightweight mod loader for Minecraft. |
| Forge | Traditional mod loader with a large mod ecosystem. |

## Connection Modes

### playit.gg (Recommended)

No port forwarding required. The app downloads and runs the playit.gg agent, which creates a free tunnel so your server is reachable from anywhere. First-time setup:

1. Start the server with playit.gg mode enabled.
2. Click "Claim Agent" and log in at playit.gg.
3. In the playit.gg dashboard, add a Minecraft tunnel pointing to your local server port.
4. Share the public address shown in the Network tab.

### Direct IP

Requires manual port forwarding on your router. The app can automatically open the server port using UFW (Linux), Windows Defender Firewall, or macOS Application Firewall.

## Features

### Server Management

- Start, stop, and restart the server from the GUI.
- Send commands directly from the Console tab.
- View live server output with color-coded log levels.
- Auto-restart on crash with configurable delay.
- Scheduled restarts at configurable intervals.

### World Management

- Automatic world backup before each server start.
- Manual backup and restore from the GUI.
- Periodic backups on a timer (5 to 360 minutes).
- Backup rotation: automatically delete backups older than N days or keep only the last N backups.

### Player Management

- Dedicated Players tab: whitelist and OP lists with live display.
- Dedicated Bans tab: player ban and IP ban lists with live display.
- Online players display updated in real time.

### Plugin Manager

- Search the Modrinth plugin repository directly from the Plugins tab.
- One-click plugin installation for Paper and Fabric servers.

### Network and Security

- playit.gg tunnel integration for zero-config public access.
- Direct IP mode with public IP detection.
- Automatic firewall configuration (UFW, iptables, Windows Defender, macOS Application Firewall).
- Port accessibility checker to verify your server is reachable from the internet.

### Configuration

- All server.properties fields editable from the GUI.
- Server profiles: save, load, and delete configuration presets.
- Quick presets for common server types (Survival SMP, Hardcore, Creative, Skyblock, PVP, and more).

### Utilities

- RAM monitoring with live display in the header bar.
- Server auto-update to the latest build.
- Startup script generator: export standalone `start.sh` and `start.bat` files.
- Crash report analyzer: parses Minecraft crash reports and suggests fixes.
- Log file export to timestamped files with rolling at 10 MB.

## Configuration

All configuration is stored in `~/MCServerHost/config.json`. Server files, world data, backups, and logs are stored in the same directory.

| Path | Contents |
|------|----------|
| `~/MCServerHost/config.json` | Application configuration |
| `~/MCServerHost/server.properties` | Minecraft server properties |
| `~/MCServerHost/backups/` | World backup ZIP files |
| `~/MCServerHost/logs/` | Exported server log files |
| `~/MCServerHost/profiles/` | Saved server profile presets |
| `~/MCServerHost/scripts/` | Generated startup scripts |
| `~/MCServerHost/plugins/` | Installed server plugins |

## Platform Support

| Platform | Status |
|----------|--------|
| Linux (x86_64, ARM64) | Fully supported |
| Windows (x86_64) | Fully supported |
| macOS (Intel, Apple Silicon) | Fully supported |

Java 17+ is required. The bootstrap phase will attempt to install it automatically using the system package manager (apt, dnf, yum, pacman, zypper, brew, or winget).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
