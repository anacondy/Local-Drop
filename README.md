# Local-Drop
Sharing files between cross platform devices, without internet 


# Local Drop 🚀

A high-performance, lightweight, open-source Progressive Web App (PWA) designed to transfer files directly across local networks (LAN) at maximum hardware speeds without using cell data or internet bandwidth.

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
├── local_drop.py        # Core Flask server backend and PWA generator
├── requirements.txt     # Python dependency configuration file
├── run.bat              # Automation script for Windows environments
├── run.sh               # Automation script for macOS and Linux environments
└── README.md            # System documentation and guide
