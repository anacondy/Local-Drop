# Local Drop 🚀

A high-performance, lightweight, open-source Progressive Web App (PWA) designed to transfer files directly across local networks (LAN) at maximum hardware speeds without using cell data or internet bandwidth.

### 🚀 Quick Start
If you have Git and Python installed, simply run this command in your terminal:

**Windows (PowerShell):**
```powershell
git clone https://github.com/anacondy/Local-Drop.git && cd Local-Drop && .\run.bat
```

**macOS / Linux:**
```bash
git clone https://github.com/anacondy/Local-Drop.git && cd Local-Drop && chmod +x run.sh && ./run.sh
```

---


## 💻 System & Device Compatibility

Local Drop is engineered to be fully cross-platform. Below are the precise environmental requirements for deployment:

### Host Machine (The Server PC)
* **Windows:** Windows 10 or Windows 11 (Supports both standard directories and active OneDrive-redirected folders).
* **macOS:** macOS 11 (Big Sur) or newer (Automatically routes video assets to native Apple `Movies` directory).
* **Linux:** Any modern distribution (Ubuntu, Debian, Fedora, Arch) running Python 3.x.

### Client Devices (The Senders/Receivers)
* **Android:** Works on any modern Android device via Google Chrome (Supports full PWA standalone app installation directly to the home screen).
* **iOS / iPadOS:** Works via Safari browser (Supports "Add to Home Screen" framework layout).

---

## 🛠️ Prerequisites & Installation

Before launching the utility, ensure your host computer has **Python 3.8 or higher** installed and added to your system's environment variables (PATH).

### Project Directory Structure
Ensure your local project folder is organized exactly like this:
```text
LocalDrop/
├── .gitignore           # Keeps your repo clean
├── local_drop.py        # The master Flask & PWA backend
├── requirements.txt     # List of dependencies
├── run.bat              # Universal Windows launcher
└── run.sh               # Universal macOS/Linux launcher

### 🛡️ Isolated Execution Environment
To prevent system conflicts and adhere to modern PEP 668 standards (especially on Linux), the automated launch scripts will seamlessly generate a localized Python Virtual Environment (`venv`). 
* No `sudo` permissions required.
* No global system packages are touched.
* Simply delete the `LocalDrop` folder to completely uninstall; nothing is left behind on your OS.
