# Local Drop 🚀

A high-performance, lightweight, open-source Progressive Web App (PWA) designed to transfer files directly across local networks (LAN) at maximum hardware speeds — no internet, no cloud, no accounts.

---

## ⚡ Quick Start

These commands are designed to be run from anywhere. They will automatically download the app, or if you already have it, update it to the latest version and launch it!

### Windows (Command Prompt / CMD)

```cmd
if exist Local-Drop (cd Local-Drop && git pull && .\run.bat) else (git clone [https://github.com/anacondy/Local-Drop.git](https://github.com/anacondy/Local-Drop.git) && cd Local-Drop && .\run.bat)

```

### Windows (PowerShell)

```powershell
if (Test-Path Local-Drop) { cd Local-Drop; git pull; .\run.bat } else { git clone [https://github.com/anacondy/Local-Drop.git](https://github.com/anacondy/Local-Drop.git); cd Local-Drop; .\run.bat }

```

### macOS / Linux

```bash
[ -d "Local-Drop" ] && (cd Local-Drop && git pull && ./run.sh) || (git clone [https://github.com/anacondy/Local-Drop.git](https://github.com/anacondy/Local-Drop.git) && cd Local-Drop && chmod +x run.sh && ./run.sh)

```

---

## 💻 System & Device Compatibility

### Host Machine (The Server — runs the Python server)

| OS | Support |
| --- | --- |
| Windows 10 / 11 | Full support. Detects OneDrive and routes files there automatically. |
| macOS 11+ | Full support. Uses native `Movies` folder for video. |
| Linux (Ubuntu, Arch, Fedora…) | Full support. |

### Client Devices (Connect via browser — send or receive files)

| Device | How |
| --- | --- |
| Android | Chrome browser. Can install as PWA from the address bar. |
| iPhone / iPad | Safari browser. Use "Add to Home Screen" for PWA install. |
| Any PC on same WiFi | Open the URL or scan the QR code in the terminal. |

> Multiple devices can connect at the same time. The UI shows a live count and each device's current role (sending ↑ / receiving ↓ / viewing).

---

## 🗂️ Where Files Go

Every received file is saved in **two places**:

1. **Sorted by type** into the appropriate folder:
* Images → `Pictures/LocalDrop/`
* Videos → `Videos/LocalDrop/`
* Music → `Music/LocalDrop/`
* Documents → `Documents/LocalDrop/`
* Other → `Downloads/LocalDrop/`


2. **Flat inbox** for quick access → `OneDrive/LocalDrop-Inbox/` (Windows) or `~/LocalDrop-Inbox/`

The inbox folder is created automatically when the server starts.

---

## 🛠️ Prerequisites

* **Python 3.8 or higher** — must be in your system PATH
* **Git** — to clone the repo

### Project Structure

```
Local-Drop/
├── local_drop.py    # Flask server + PWA frontend
├── requirements.txt # Dependencies (flask, qrcode)
├── run.bat          # Windows launcher (auto-installs deps)
└── run.sh           # macOS/Linux launcher

```

---

## 🛡️ Security Notes

* **Session token**: Each server start generates a unique token. Old browser tabs from a previous session cannot upload files after the server is restarted — they get a "Session closed" error and must refresh.
* **Shutdown locks uploads**: Pressing `Ctrl+C` stops the server and immediately rejects any further upload attempts from any device.
* **LAN only**: The server binds to your local IP. It is not accessible from the internet.

---

## 🚀 How It Works

1. Run `.\run.bat` (Windows) or `./run.sh` (Mac/Linux)
2. A QR code appears in the terminal
3. Scan it with any device on the same WiFi
4. **Send to PC**: tap the upload zone → select files → they go to your PC instantly
5. **Get from PC**: files you place in the `LocalDrop` sorted folders appear in the "Get from PC" list on any connected device

---

## 🔄 Uninstall

Delete the `Local-Drop` folder. The only other things created are the `LocalDrop` subfolders inside your Pictures/Videos/etc. and the `LocalDrop-Inbox` folder — delete those too if you want a clean uninstall. Nothing else is touched on your system.

```

```