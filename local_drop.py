import os
import sys
import shutil
import socket
import qrcode
import time
import logging
import platform
import threading
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, render_template_string, send_file, jsonify, redirect

# ── Logging ───────────────────────────────────────────────────────────────────
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# ── Session state ─────────────────────────────────────────────────────────────
connected_clients = {}   # ip -> {id, device, role, last_seen, joined}
connected_lock    = threading.Lock()
server_alive      = True
SESSION_TOKEN     = str(uuid.uuid4())

# ── ANSI colors ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
PURPLE = "\033[95m"
OCEAN  = "\033[96m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def P(*args, **kwargs):
    print(*args, **kwargs, flush=True)

def color_filename(filename):
    if '.' in filename:
        name, _, ext = filename.rpartition('.')
        return f"{PURPLE}{name}{RESET}.{OCEAN}{ext}{RESET}"
    return f"{PURPLE}{filename}{RESET}"

# ── Paths ─────────────────────────────────────────────────────────────────────
def get_inbox_directory():
    home = str(Path.home())
    if platform.system() == 'Windows':
        od = os.path.join(home, 'OneDrive')
        if os.path.exists(od):
            return os.path.join(od, 'LocalDrop-Inbox')
    return os.path.join(home, 'LocalDrop-Inbox')

def get_target_directories():
    home   = str(Path.home())
    system = platform.system()
    def resolve(*subdirs):
        if system == 'Windows':
            od = os.path.join(home, 'OneDrive', *subdirs, 'LocalDrop')
            if os.path.exists(os.path.join(home, 'OneDrive', *subdirs)):
                return od
        return os.path.join(home, *subdirs, 'LocalDrop')
    if system == 'Darwin':
        return {'Images': resolve('Pictures'), 'Videos': resolve('Movies'),
                'Music': resolve('Music'), 'Docs': resolve('Documents'), 'Other': resolve('Downloads')}
    return {'Images': resolve('Pictures'), 'Videos': resolve('Videos'),
            'Music': resolve('Music'), 'Docs': resolve('Documents'), 'Other': resolve('Downloads')}

def route_file(filename):
    ext  = filename.lower().split('.')[-1] if '.' in filename else ''
    dirs = get_target_directories()
    if ext in ['jpg','jpeg','png','gif','bmp','webp','heic','heif','raw','svg','tiff','ico']: return dirs['Images']
    if ext in ['mp4','mov','avi','mkv','webm','flv','wmv','m4v','3gp','ts']:                  return dirs['Videos']
    if ext in ['mp3','wav','aac','flac','m4a','ogg','wma','alac','opus']:                     return dirs['Music']
    if ext in ['pdf','doc','docx','txt','xls','xlsx','ppt','pptx','csv','json','xml','md']:   return dirs['Docs']
    return dirs['Other']

def format_size(n):
    if n >= 1024**3: return f"{n/1024**3:.2f} GB"
    if n >= 1024**2: return f"{n/1024**2:.2f} MB"
    return f"{n/1024:.2f} KB"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

# ── Device tracking ───────────────────────────────────────────────────────────
def detect_device(ua: str) -> str:
    ua = ua.lower()
    if any(x in ua for x in ['ipad', 'tablet']): return 'tablet'
    if 'android' in ua and 'mobile' not in ua:   return 'tablet'
    if any(x in ua for x in ['mobile', 'iphone', 'android']): return 'mobile'
    return 'desktop'

def register_client(ip: str, ua: str, role: str = 'viewer'):
    with connected_lock:
        if ip not in connected_clients:
            connected_clients[ip] = {
                'id'       : ip,
                'device'   : detect_device(ua),
                'role'     : role,
                'last_seen': time.time(),
                'joined'   : datetime.now().strftime('%H:%M:%S'),
            }
            P(f"\n  {YELLOW}+ Connected{RESET}  {ip}  {DIM}({detect_device(ua)}){RESET}")
        else:
            connected_clients[ip]['last_seen'] = time.time()
            connected_clients[ip]['role']      = role

def prune_stale(timeout: int = 60):
    now = time.time()
    with connected_lock:
        stale = [ip for ip, c in connected_clients.items() if now - c['last_seen'] > timeout]
        for ip in stale:
            del connected_clients[ip]
            P(f"\n  {DIM}- Disconnected  {ip}{RESET}")

# ── Manifest ──────────────────────────────────────────────────────────────────
MANIFEST_JSON = {
    "name": "Local Drop", "short_name": "LocalDrop",
    "start_url": "/", "display": "standalone",
    "background_color": "#020202", "theme_color": "#020202",
    "icons": [{"src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M12 3v13m0 0l-4-4m4 4l4-4M4 19h16'/></svg>", "sizes": "192x192", "type": "image/svg+xml"}],
}

# ── HTML / Cinematic Glassmorphism UI ─────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Local Drop | Vault</title>
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#020202">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <style>
    :root {
      --cyber-cyan: #00f0ff;
      --cyber-red: #ff003c;
      --glass-bg: rgba(15, 15, 18, 0.5);
      --glass-border: rgba(255, 255, 255, 0.08);
    }
    *{box-sizing:border-box}
    body {
      font-family: system-ui, -apple-system, sans-serif;
      -webkit-tap-highlight-color: transparent;
      background: radial-gradient(circle at 50% 0%, #111115 0%, #020202 100%);
      color: #e2e8f0;
      min-height: 100vh;
    }
    
    /* Cinematic Frosted Glass */
    .glass-panel {
      background: var(--glass-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), inset 0 1px 0 rgba(255,255,255,0.05);
      border-radius: 20px;
    }

    @keyframes pulse-glow {
      0%, 100% { opacity: 1; box-shadow: 0 0 15px rgba(0, 240, 255, 0.4); }
      50% { opacity: 0.6; box-shadow: 0 0 5px rgba(0, 240, 255, 0.1); }
    }
    .dot-active { animation: pulse-glow 2s ease-in-out infinite; background-color: var(--cyber-cyan); }
    
    @keyframes spin { to { transform: rotate(360deg); } }
    .spin { animation: spin 0.8s linear infinite; }
    
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 9px; }
    
    .zone-idle { border-color: rgba(255,255,255,0.15); }
    .zone-sending { border-color: var(--cyber-cyan); box-shadow: 0 0 0 4px rgba(0,240,255,0.1); }
    .zone-done { border-color: #22c55e; box-shadow: 0 0 0 4px rgba(34,197,94,0.1); }
    .zone-error { border-color: var(--cyber-red); box-shadow: 0 0 0 4px rgba(255,0,60,0.1); }
  </style>
</head>
<body class="flex flex-col items-center p-4 sm:p-8">

<div class="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-lg h-64 bg-cyan-900/10 blur-[100px] pointer-events-none"></div>

<div class="w-full max-w-md space-y-5 relative z-10">

  <div class="glass-panel p-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-white drop-shadow-md">The Vault</h1>
        <p class="text-xs text-neutral-400 mt-0.5 uppercase tracking-wider">Cross-Platform Sync</p>
      </div>
      <div class="flex items-center gap-2 bg-black/40 border border-white/10 rounded-full px-3 py-1.5 shadow-inner">
        <span id="dot" class="w-2.5 h-2.5 rounded-full bg-neutral-600"></span>
        <span id="device-count" class="text-xs font-semibold text-neutral-300">— nodes</span>
      </div>
    </div>
    
    <div id="device-list" class="hidden mt-4 space-y-1">
      <div id="device-items" class="space-y-1.5"></div>
    </div>
  </div>

  <div class="glass-panel p-5">
    <p class="text-[10px] font-bold uppercase tracking-widest text-cyan-400 mb-3 flex items-center gap-2">
      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
      Broadcast to Network
    </p>

    <div id="drop-zone"
         class="border-2 border-dashed zone-idle rounded-xl p-8 text-center cursor-pointer bg-black/20
                transition-all duration-300 hover:border-cyan-500/50 hover:bg-cyan-900/10 select-none">
      <input type="file" id="file-input" class="hidden" multiple>

      <div id="state-idle" class="space-y-3">
        <svg style="width:40px;height:40px;margin:0 auto;display:block;opacity:0.6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <div>
          <p class="text-sm font-semibold text-neutral-200">Tap to Select Files</p>
          <p class="text-[11px] text-neutral-500 mt-1">Available instantly on all devices</p>
        </div>
      </div>

      <div id="state-uploading" class="hidden space-y-4">
        <svg class="spin" style="width:28px;height:28px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24" stroke="#00f0ff" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
        </svg>
        <p id="prog-filename" class="text-xs text-neutral-400 truncate px-4 font-mono"></p>
        <div class="w-full bg-black/60 border border-white/10 rounded-full h-2 overflow-hidden shadow-inner">
          <div id="prog-bar" class="h-full rounded-full transition-all duration-100 bg-[#00f0ff] shadow-[0_0_12px_#00f0ff]" style="width:0%"></div>
        </div>
        <p class="text-xs text-cyan-400 font-mono tracking-widest"><span id="prog-pct">0</span>%</p>
      </div>

      <div id="state-done" class="hidden space-y-2">
        <svg style="width:36px;height:36px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24" stroke="#22c55e" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p class="text-sm font-semibold text-green-400">Transmitted</p>
      </div>

      <div id="state-error" class="hidden space-y-2">
        <svg style="width:36px;height:36px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24" stroke="#ff003c" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
        </svg>
        <p id="err-msg" class="text-sm font-semibold text-red-400">Connection Failed</p>
      </div>
    </div>
  </div>

  <div class="glass-panel p-5">
    <div class="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
      <p class="text-[10px] font-bold uppercase tracking-widest text-neutral-400">Network Inbox</p>
      <div class="flex items-center gap-1.5 text-[10px] text-cyan-500 font-mono tracking-widest uppercase">
        <span class="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-ping"></span>
        Live Sync
      </div>
    </div>

    <div id="file-list-container" class="space-y-2 max-h-72 overflow-y-auto pr-1">
      {% if files %}
        {% for file in files %}
        <div class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
          <span class="shrink-0 drop-shadow-md">{{ file_icon(file) | safe }}</span>
          <span class="flex-1 text-sm text-neutral-300 truncate" title="{{ file }}">{{ file }}</span>
          <a href="/download/{{ file }}" download
             class="shrink-0 flex items-center gap-1.5 text-[11px] font-bold tracking-wider uppercase
                    bg-black/40 hover:bg-cyan-900/40 text-cyan-400 border border-cyan-500/30
                    px-3 py-2 rounded-lg transition-all shadow-[0_0_10px_rgba(0,240,255,0.05)] hover:shadow-[0_0_15px_rgba(0,240,255,0.2)]">
            Download
          </a>
        </div>
        {% endfor %}
      {% else %}
        <div class="py-8 text-center">
          <p class="text-sm text-neutral-600 font-mono">Vault is empty.</p>
        </div>
      {% endif %}
    </div>
  </div>

</div>

<script>
// UI State Handlers
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const progBar = document.getElementById('prog-bar');
const progPct = document.getElementById('prog-pct');
const progFile = document.getElementById('prog-filename');
const errMsg = document.getElementById('err-msg');

function showState(name) {
  ['idle','uploading','done','error'].forEach(s => {
    document.getElementById('state-'+s).classList.toggle('hidden', s !== name);
  });
  dropZone.className = dropZone.className.replace(/zone-\\S+/g,'') + ' zone-' + name;
}

dropZone.addEventListener('click', () => { if (!dropZone.classList.contains('zone-uploading')) fileInput.click(); });
fileInput.addEventListener('change', () => handleFiles(fileInput.files));
['dragenter','dragover','dragleave','drop'].forEach(ev => dropZone.addEventListener(ev, e => e.preventDefault()));
dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));

// Upload Logic
function handleFiles(files) {
  if (!files.length) return;
  const fd = new FormData();
  fd.append('client_launch_timestamp', Date.now());
  fd.append('session_token', '{{ session_token }}');
  let names = [];
  for (let i = 0; i < files.length; i++) { fd.append('files', files[i]); names.push(files[i].name); }

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload', true);
  xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

  showState('uploading');
  progFile.textContent = names.join(', ');
  progBar.style.width = '0%';
  progPct.textContent = '0';

  xhr.upload.addEventListener('progress', e => {
    if (e.lengthComputable) {
      const pct = Math.round(e.loaded / e.total * 100);
      progBar.style.width = pct + '%';
      progPct.textContent = pct;
    }
  });

  xhr.onload = () => {
    if (xhr.status === 200) {
      showState('done');
      pollNetworkFiles(); // Immediately pull new files down to the list
      setTimeout(() => { showState('idle'); }, 1500);
    } else {
      errMsg.textContent = xhr.status === 403 ? 'Session Terminated' : 'Upload Failed';
      showState('error');
      setTimeout(() => showState('idle'), 3000);
    }
    fileInput.value = '';
  };
  xhr.onerror = () => {
    errMsg.textContent = 'Network Error';
    showState('error');
    setTimeout(() => showState('idle'), 3000);
  };
  xhr.send(fd);
}

// ── Live File Polling Engine (This powers the Cross-Platform Magic) ──
const fileListContainer = document.getElementById('file-list-container');
async function pollNetworkFiles() {
  try {
    const res = await fetch('/api/files');
    const data = await res.json();
    if (!data.files || data.files.length === 0) {
      fileListContainer.innerHTML = '<div class="py-8 text-center"><p class="text-sm text-neutral-600 font-mono">Vault is empty.</p></div>';
      return;
    }
    
    // Renders the list dynamically with innerHTML so SVGs display properly
    fileListContainer.innerHTML = data.files.map(f => `
      <div class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
        <span class="shrink-0 drop-shadow-md">${f.icon}</span>
        <span class="flex-1 text-sm text-neutral-300 truncate" title="${f.name}">${f.name}</span>
        <a href="/download/${encodeURIComponent(f.name)}" download
           class="shrink-0 flex items-center gap-1.5 text-[11px] font-bold tracking-wider uppercase
                  bg-black/40 hover:bg-cyan-900/40 text-cyan-400 border border-cyan-500/30
                  px-3 py-2 rounded-lg transition-all shadow-[0_0_10px_rgba(0,240,255,0.05)] hover:shadow-[0_0_15px_rgba(0,240,255,0.2)]">
          Download
        </a>
      </div>
    `).join('');
  } catch(e) {}
}
// Automatically ping the server for new files every 2 seconds
setInterval(pollNetworkFiles, 2000);

// ── Device Tracking Engine ──
const deviceCount = document.getElementById('device-count');
const deviceList  = document.getElementById('device-list');
const deviceItems = document.getElementById('device-items');
const dot         = document.getElementById('dot');

function deviceIcon(type) {
  const S = 'display:inline-block;vertical-align:middle;width:14px;height:14px';
  if (type === 'mobile') return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18h3"/></svg>`;
  if (type === 'tablet') return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5h3m-6.75 2.25h10.5a2.25 2.25 0 002.25-2.25v-15a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 4.5v15a2.25 2.25 0 002.25 2.25z"/></svg>`;
  return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25A2.25 2.25 0 015.25 3h13.5A2.25 2.25 0 0121 5.25z"/></svg>`;
}

async function pollDevices() {
  try {
    const res  = await fetch('/api/devices');
    const data = await res.json();
    const list = data.devices || [];

    deviceCount.textContent = list.length + (list.length === 1 ? ' node' : ' nodes');
    dot.className = 'w-2.5 h-2.5 rounded-full ' + (list.length > 1 ? 'dot-active' : 'bg-neutral-600');

    if (list.length > 1) {
      deviceList.classList.remove('hidden');
      deviceItems.innerHTML = list.map(d => `
        <div class="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-black/20 border border-white/5">
          <span class="text-neutral-500">${deviceIcon(d.device)}</span>
          <span class="font-mono text-[10px] text-neutral-400 flex-1 truncate">${d.id}</span>
        </div>`).join('');
    } else {
      deviceList.classList.add('hidden');
    }
  } catch(_) {}
}

setInterval(pollDevices, 3000);
pollDevices();
setInterval(() => fetch('/api/ping', {method:'POST'}), 20000);
</script>
</body>
</html>"""

# ── Jinja helper ──────────────────────────────────────────────────────────────
@app.template_global()
def file_icon(filename):
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    S = 'display:inline-block;width:20px;height:20px;vertical-align:middle'
    if ext in ['jpg','jpeg','png','gif','bmp','webp','heic','svg','ico']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#c084fc" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/></svg>'
    if ext in ['mp4','mov','avi','mkv','webm']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#f472b6" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"/></svg>'
    if ext in ['mp3','wav','aac','flac','m4a','ogg']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#34d399" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"/></svg>'
    if ext in ['pdf','doc','docx','txt','xls','xlsx','ppt','pptx','csv','md']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#38bdf8" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>'
    return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#9ca3af" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>'

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/manifest.json')
def serve_manifest():
    return jsonify(MANIFEST_JSON)

@app.route('/')
def index():
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    register_client(ip, ua, 'viewer')
    prune_stale()
    all_files = []
    
    for d in get_target_directories().values():
        if os.path.exists(d):
            all_files.extend(os.listdir(d))
            
    inbox_dir = get_inbox_directory()
    if os.path.exists(inbox_dir):
        all_files.extend(os.listdir(inbox_dir))
        
    return render_template_string(HTML_TEMPLATE, files=sorted(set(all_files), key=lambda x: os.path.getmtime(os.path.join(inbox_dir, x)) if os.path.exists(os.path.join(inbox_dir, x)) else 0, reverse=True),
                                  session_token=SESSION_TOKEN)

@app.route('/api/ping', methods=['POST'])
def api_ping():
    register_client(request.remote_addr, request.headers.get('User-Agent',''), 'viewer')
    prune_stale()
    return 'ok', 200

@app.route('/api/devices')
def api_devices():
    prune_stale()
    my_ip = request.remote_addr
    with connected_lock:
        devices  = [{'id': c['id'], 'device': c['device'], 'role': c['role']} for c in connected_clients.values()]
        my_role  = connected_clients.get(my_ip, {}).get('role', 'viewer')
    return jsonify({'devices': devices, 'my_role': my_role})

@app.route('/api/files')
def api_files():
    all_files = []
    for d in get_target_directories().values():
        if os.path.exists(d):
            all_files.extend(os.listdir(d))
            
    inbox_dir = get_inbox_directory()
    if os.path.exists(inbox_dir):
        all_files.extend(os.listdir(inbox_dir))
        
    unique_files = sorted(set(all_files), key=lambda x: os.path.getmtime(os.path.join(inbox_dir, x)) if os.path.exists(os.path.join(inbox_dir, x)) else 0, reverse=True)
    file_data = [{'name': f, 'icon': file_icon(f)} for f in unique_files]
    return jsonify({'files': file_data})

@app.route('/upload', methods=['POST'])
def upload_file():
    global server_alive
    if not server_alive: return 'Session closed', 403

    token = request.form.get('session_token', '')
    if token != SESSION_TOKEN: return 'Invalid session', 403

    if 'files' not in request.files: return 'No files', 400

    client_ip           = request.remote_addr
    ua                  = request.headers.get('User-Agent', '')
    client_timestamp    = request.form.get('client_launch_timestamp')
    server_receive_time = time.time()

    register_client(client_ip, ua, 'sending')
    files = request.files.getlist('files')

    for file in files:
        if not file.filename: continue

        disk_start = time.time()
        target_dir = route_file(file.filename)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, file.filename)
        file.save(filepath)

        inbox_dir  = get_inbox_directory()
        os.makedirs(inbox_dir, exist_ok=True)
        inbox_path = os.path.join(inbox_dir, file.filename)
        shutil.copy2(filepath, inbox_path)

        disk_ms   = round((time.time() - disk_start) * 1000)
        file_size = os.path.getsize(filepath)
        net_display = f"{max(0, round((server_receive_time - float(client_timestamp) / 1000.0) * 1000))} ms" if client_timestamp else "n/a"

        ts = datetime.now().strftime('%H:%M:%S')
        P(f"\n  {GREEN}[{ts}] RECEIVED{RESET}  {color_filename(file.filename)}")
        P(f"   From    : {client_ip}  ({detect_device(ua)})")
        P(f"   Sorted  : {filepath}")
        P(f"   Inbox   : {inbox_path}")
        P(f"   Size    : {format_size(file_size)}")
        P(f"   Network : {net_display}   Write: {disk_ms} ms")
        P("   " + "-" * 52)

    register_client(client_ip, ua, 'viewer')
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest': return redirect('/')
    return 'Success', 200

@app.route('/download/<path:filename>')
def download_file(filename):
    client_ip = request.remote_addr
    ua        = request.headers.get('User-Agent', '')
    register_client(client_ip, ua, 'receiving')

    search_paths = list(get_target_directories().values()) + [get_inbox_directory()]
    for d in search_paths:
        target = os.path.join(d, filename)
        if os.path.exists(target):
            ts = datetime.now().strftime('%H:%M:%S')
            P(f"\n  {YELLOW}[{ts}] SENT{RESET}  {color_filename(filename)}  -> {client_ip}  ({detect_device(ua)})")
            P("   " + "-" * 52)
            resp = send_file(target, as_attachment=True)
            register_client(client_ip, ua, 'viewer')
            return resp

    register_client(client_ip, ua, 'viewer')
    return "File not found", 404

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import signal
    if platform.system() == 'Windows': os.system('color')

    inbox = get_inbox_directory()
    os.makedirs(inbox, exist_ok=True)

    ip_addr     = get_local_ip()
    port_num    = 5001
    hosting_url = f"http://{ip_addr}:{port_num}"

    def graceful_shutdown(sig, frame):
        global server_alive
        server_alive = False
        P(f"\n\n  {RED}[STOPPED]{RESET} Server closed. Uploads rejected.\n")
        sys.exit(0)

    signal.signal(signal.SIGINT,  graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    P("\n" + "=" * 55)
    P("       LOCAL DROP  -  SERVER ACTIVE")
    P("=" * 55)
    P(f"\n  URL   : {hosting_url}")
    P(f"  Inbox : {inbox}")
    P(f"\n  Keep this window open while transferring.")
    P(f"  Press Ctrl+C to stop.\n")

    qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(hosting_url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    P(f"\n  Scan QR above  or  open: {hosting_url}\n")
    P("-" * 55)

    app.run(host='0.0.0.0', port=port_num, debug=False, threaded=True)