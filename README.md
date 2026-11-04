# VoidMiner Client

A real Minecraft: Java Edition launcher for Windows (Python + CustomTkinter). It installs and launches
Minecraft using Mojang's official metadata (via `minecraft-launcher-lib`), with per-profile instances,
Fabric / Quilt / Forge / NeoForge, a Modrinth mod manager, legitimate Microsoft sign-in and a performance
system tuned for low-end PCs (default target: Core i5-4210M, 8 GB RAM, Intel HD graphics, 128 GB SSD).

## Quick start
1. Install **Python 3.10+** from python.org (tick *Add Python to PATH*).
2. Double-click **`run.bat`** (first run creates `.venv` and installs `requirements.txt`).
3. Go to **Accounts** and follow *Microsoft sign-in* below, then press **PLAY** on the Dashboard.

To make an EXE: run **`build.bat`** → `dist\VoidMiner Client\VoidMiner Client.exe`.

## Microsoft sign-in (required to play)
VoidMiner never sees your password; it uses the official Microsoft OAuth (PKCE) → Xbox Live → XSTS → Minecraft
services chain and verifies you own Minecraft: Java Edition. Refresh tokens are kept in Windows Credential Manager.

You need your own (free) Azure app:
1. https://portal.azure.com → *App registrations* → *New registration*. Account types: *Personal Microsoft accounts*
   (or any directory + personal).
2. Redirect URI: platform **Mobile and desktop applications**, value `http://localhost`.
3. *Authentication* → **Allow public client flows = Yes**.
4. Copy the **Application (client) ID** into *Accounts → Client ID* (or set env var `VOIDMINER_CLIENT_ID`).
5. **Mojang approval:** Minecraft services reject brand-new Azure app IDs (HTTP 403 / "Invalid app registration")
   until Mojang approves them via the form at https://aka.ms/AppRegInfo. This is Microsoft/Mojang policy and
   cannot be bypassed - VoidMiner deliberately has no offline/cracked login and does not use other launchers' IDs.

## What's inside
| Area | Notes |
|---|---|
| Dashboard | Play/Stop, selected profile, skin preview, RAM, install + Java status, recents, live CPU/RAM of the running game |
| Profiles | Create / edit / rename / duplicate / delete; each has its own folder (`%APPDATA%\VoidMiner\instances\<id>`), version, loader, RAM, Java, JVM args |
| Optimize | Potato / Low-End / Balanced / High FPS / Custom, hardware auto-detect, RAM slider, JVM flags preview, `options.txt` tuning (backed up), performance-mod installer, background-app scan |
| Mods | Modrinth search, version picker, required-dependency install, SHA-1 verification, enable/disable, remove, conflict warnings |
| Skins | Front/back turntable preview, cape display (only capes your account owns), skin upload and cape switch via Mojang's API |
| Settings | RAM, Java, JVM args, game dir, resolution, fullscreen, language (EN/ES/FR/DE), accent theme, update URL |

## Performance - what is real
* Mode presets set RAM, G1GC flags, render/simulation distance, particles, graphics, FPS cap and entity/biome/mipmap options.
* Performance mods: Sodium, Lithium, FerriteCore, Entity Culling, ImmediatelyFast, ModernFix, Dynamic FPS, Sodium Extra
  (Fabric/Quilt) and Embeddium + friends (Forge/NeoForge). Only versions that actually exist for your Minecraft
  version are installed; the rest are reported as skipped.
* **No FPS is faked.** 1000 FPS is not promised. The launcher measures the game's real CPU/RAM; read real FPS with F3
  in-game (Sodium Extra adds an overlay). On an i5-4210M + Intel HD expect big gains from Low-End mode + Sodium, but the
  result depends on version, world and drivers.
* Safety: the launcher uses its own folder (`%APPDATA%\VoidMiner`), never overwrites existing Minecraft files, backs up
  `options.txt` once (`options.txt.voidminer.bak`), and skips unreadable profiles instead of touching them. RAM is capped at 60% of installed memory.

## Data locations
`%APPDATA%\VoidMiner\` → `settings.json`, `accounts.json` (no tokens), `instances\`, `minecraft\` (shared versions/libraries/assets/Java), `logs\`.

## Known limitations
* The skin preview is a 2D front/back view with a rotate animation, not a real 3D renderer.
* Language selection translates navigation and main buttons; other text stays English. Restart to apply language/theme.
* Not tested against every Minecraft version / loader combination; loaders are verified against their own metadata at profile creation.
