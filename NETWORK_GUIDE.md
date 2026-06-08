# Network & Accessibility Guide

### 1. Firewall Configuration
To allow devices on your local network (like your phone) to connect to Local Drop, you must allow the Python process through your system's firewall.

#### **Windows**
1. Press `Win + R`, type `wf.msc`, and hit Enter.
2. Click **Inbound Rules** > **New Rule...**.
3. Select **Program**, then find your `python.exe` path.
4. Select **Allow the connection**.
5. Name it "Local Drop" and finish.

#### **Linux (UFW)**
If you are using `ufw`, run:
```bash
sudo ufw allow 5001/tcp
```

### 2. HTTPS / Local Development
Modern mobile browsers sometimes restrict features if the connection is not secure (HTTPS). 
- **Recommendation**: For local, ad-hoc file transfers, HTTP is usually sufficient. 
- **If you face issues**: Ensure your device is on the *exact same* Wi-Fi network as the host PC. Avoid "Guest" networks which often implement "AP Isolation" (a security setting that prevents wireless devices from talking to each other).
