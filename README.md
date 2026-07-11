# MCServerHost

A single-file Python GUI for hosting a Minecraft server. Players join instantly through Minecraft Multiplayer. No networking knowledge required.

**Requirements:** Python 3.8+ and Java 21+ (both auto-installed if missing).  
**Platforms:** Linux, Windows, macOS (Intel & Apple Silicon).

## Quick Start

**Linux / macOS:** `chmod +x run.sh && ./run.sh`  
**Windows:** Double-click `run.bat`  
**Manual:** `python3 mcserverhost.py`

1. Select server type and Minecraft version in Setup.
2. Click **Download / Update Server**.
3. Go to Server tab, click **Start Server**.
4. Share the address from the Network tab.

## Server Types

| Type | Description |
|------|-------------|
| Paper MC | Recommended. High-performance, plugin support. |
| Vanilla | Official Mojang server. |
| Fabric | Lightweight mod loader. |
| Forge | Traditional mod loader with large ecosystem. |

## Connection Modes

**playit.gg (Recommended)** — No port forwarding. The app runs a playit.gg tunnel agent. Start the server, click "Claim Agent", add a Minecraft tunnel in the playit.gg dashboard, and share the public address.

**Direct IP** — Requires manual port forwarding. The app can auto-configure UFW, iptables, Windows Defender, or macOS Application Firewall.

## Features

| Category | Features |
|----------|----------|
| **Server Control** | Start/stop/restart, console commands, auto-restart on crash, scheduled restarts, scheduled recurring commands |
| **Multi-Server** | Manage multiple instances with separate configs, worlds, plugins, and mods |
| **World Management** | Auto-backup before start, manual backup/restore, periodic backups, backup rotation, world download as ZIP, cloud backup via rclone |
| **Player Management** | Whitelist/OP lists, player bans/IP bans, online player tracking, player statistics (joins, playtime, last seen) |
| **Plugin & Mod Manager** | Search Modrinth, one-click install, check for updates on installed plugins/mods |
| **Chat & Notifications** | Color-coded chat panel, desktop notifications (Linux/macOS/Windows) |
| **Network** | playit.gg tunnel, direct IP with public IP detection, port accessibility checker |
| **Configuration** | All server.properties fields, bukkit.yml/spigot.yml/paper-global.yml editors, MOTD editor with color codes, resource pack management, server profiles, quick presets (Survival, Hardcore, Creative, Skyblock, PVP, etc.) |
| **Performance Dashboard** | Real-time RAM and TPS graphs, uptime/player count cards, customizable widget visibility |
| **Utilities** | Crash report analyzer, startup script generator, server auto-update, log export with rotation, server migration (tar.gz package/import) |

## File Structure

| Path | Contents |
|------|----------|
| `~/MCServerHost/config.json` | Application configuration |
| `~/MCServerHost/backups/` | World backup ZIPs |
| `~/MCServerHost/logs/` | Exported server logs |
| `~/MCServerHost/profiles/` | Saved config presets |
| `~/MCServerHost/scripts/` | Generated startup scripts |
| `~/MCServerHost/plugins/` | Installed plugins |
| `~/MCServerHost/mods/` | Installed mods |
| `~/MCServerHost/servers/` | Additional server instances |

## License

MIT License. See [LICENSE](LICENSE).
