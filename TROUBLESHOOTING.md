# Troubleshooting

| Problem | Fix |
|---|---|
| `run.bat` says Python not found | Install Python 3.10+ from python.org and tick *Add Python to PATH*, then rerun. |
| Dependency install fails | Check internet/proxy; delete the `.venv` folder and run `run.bat` again. |
| Window doesn't appear / closes instantly | Open `%APPDATA%\VoidMiner\logs\launcher.log`. Try Settings → *native title bar* (edit `settings.json`: `"native_titlebar": true`). |
| "No Microsoft client ID configured" | Accounts page → paste your Azure client ID (README → Microsoft sign-in). |
| Sign-in: 403 / Invalid app registration | Mojang has not approved your Azure app yet. Submit https://aka.ms/AppRegInfo and wait for approval. |
| Sign-in: account does not own Minecraft | Log in with the Microsoft account that bought Minecraft: Java Edition (or has Game Pass PC). |
| Browser says it cannot reach localhost:8765 | Allow the launcher through the firewall prompt; make sure the redirect URI is `http://localhost` in Azure. |
| Game closes right after start | The crash dialog shows the log tail. Full log: `instances\<profile>\logs\voidminer-launch.log`. Typical causes: too little RAM, incompatible mod (disable mods in Mods page), wrong Java in settings. |
| "<Loader> does not support Minecraft X" | That loader has no build for that version. Pick another version/loader. |
| Mod install skipped | No Modrinth file exists for your Minecraft version + loader. Try another version. |
| Low FPS on Intel HD | Use Low-End or Potato mode, install performance mods on a Fabric profile, update the Intel graphics driver, keep the laptop plugged in (High performance power plan), close browsers. |
| Stutters / out of memory | Raise RAM on the Optimize page (never above ~60% of installed RAM); fewer mods; lower render distance. |
| Antivirus flags the built EXE | PyInstaller EXEs are often false positives; run from source with `run.bat` or add an exclusion. |
| Reset everything | Close the launcher and delete `%APPDATA%\VoidMiner\settings.json` (keeps profiles). Delete the whole folder to remove all data. |
