The reason you are seeing that error is because your terminal is currently sitting inside the Windows system folder (`C:\WINDOWS\system32>`) instead of your project folder where you saved the files. Because of that, Windows has no idea where `run.bat` is.

Also, those `chmod` commands are strictly for **macOS and Linux**—they will not work on Windows at all!

Here is exactly how to fix the error, where to type the commands, and a complete, professional `README.md` designed to be pasted directly into your repository.

---

## How to Fix the "Not Recognized" Error on Windows

You can run your server using either **PowerShell** or the standard **Command Prompt (CMD)**, but you must first navigate to the correct folder.

Assuming you saved your `LocalDrop` folder on your Desktop, follow these exact steps:

### Method A: Using Windows PowerShell (Your current terminal)

1. Open PowerShell.
2. Navigate to your project folder by typing:
```powershell
cd ~\Desktop\LocalDrop

```


3. In PowerShell, you cannot just type the name of a file to run it; you must explicitly tell it to look in the current folder using **`.\`**. Type this command:
```powershell
.\run.bat

```



### Method B: Using Standard Command Prompt (CMD) — Recommended for Batch Files

1. Press the **Windows Key**, type **cmd**, and hit Enter.
2. Navigate to your folder:
```cmd
cd %USERPROFILE%\Desktop\LocalDrop

```


3. Launch the script directly by typing its name:
```cmd
run.bat

```



---

## Master Project Documentation (`README.md`)

Copy and paste this entire block below into your `README.md` file. It contains the explicit hardware requirements, multi-device ecosystem capabilities, and steps for running the app on any platform.

```markdown
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

```

---

## 🚀 How to Run Local Drop

### 1. Windows Deployment

You can execute the automated runner using either standard Command Prompt or PowerShell.

#### Option A: Via Command Prompt (CMD)

```cmd
# Navigate to the directory where your project is stored
cd C:\Path\To\Your\LocalDrop

# Fire up the automated environment check and server launcher
run.bat

```

#### Option B: Via Windows PowerShell

```powershell
# Navigate into the project root directory
cd C:\Path\To\Your\LocalDrop

# Execute the batch file using the required local folder prefix
.\run.bat

```

### 2. macOS & Linux Deployment

For Unix-based environments, use your native terminal application.

```bash
# Navigate to your project repository folder
cd /Path/To/Your/LocalDrop

# Grant execution permissions to the shell launch script
chmod +x run.sh

# Run the initialization and dependency check script
./run.sh

```

---

## 🔍 How to Install the App Icon on Your Mobile Device

Once the console displays the generated QR code, follow these steps to remove the web address bar and run Local Drop like a native mobile application:

1. Connect your mobile device to the **exact same Wi-Fi network or Hotspot band** as your computer.
2. Scan the terminal's QR code using your mobile camera or preferred browser app.
3. Once the interface loads in your browser:
* **On Android (Chrome):** Tap the three-dot menu icon in the upper-right corner, then select **"Add to Home screen"** or **"Install app"**.
* **On iOS (Safari):** Tap the central **Share** button along the bottom navigation bar, scroll down, and select **"Add to Home Screen"**.


4. Close your web browser. You will find a clean **Local Drop** application shortcut icon on your mobile layout launcher. Tap it to access the system instantly in fullscreen mode.

---

## ⚡ Network & Bandwidth Troubleshooting

* **Band Hopping Protection:** The automation runner script is built with an active connection loop. If you toggle your phone's hotspot configuration or shift between 2.4GHz and 5GHz mid-transfer, do not close the console window. The script will hold active processes and resume sharing functionality within 3 seconds of the adapter re-authenticating.
* **Why is Hotspot slower than Ethernet?** Local files are processed completely over-the-air through your device's internal Wi-Fi components. Mobile hotspots are optimized for data sharing efficiency rather than raw sustained local network loads, meaning physical high-gigabit Ethernet links or dedicated 5GHz routers will always deliver optimal transfer speeds.
* **The Android Native Share Menu Rule:** Mobile operating systems require secure, verified HTTPS connections before allowing an application to register inside the system-wide native "Share" panel sheet. Because local connections route over standard IP pathways (`http://192.168.x.x`), browsers block native system integration for safety. Use the clean home screen PWA icon app interface to execute rapid drag-and-drop transfers.

```

Are you able to navigate to your folder path using the `cd` command now, or would you like a quick shortcut on how to open the terminal directly inside your project folder?

```
