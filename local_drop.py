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
    """Print with immediate flush so output always appears in terminal."""
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
    """Always update last_seen and role — no role filtering."""
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
            connected_clients[ip]['role']      = role  # always update role

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
    "background_color": "#0a0a0a", "theme_color": "#0a0a0a",
    "icons": [{"src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M12 3v13m0 0l-4-4m4 4l4-4M4 19h16'/></svg>", "sizes": "192x192", "type": "image/svg+xml"}],
}

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Local Drop</title>
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#0a0a0a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <style>
    *{box-sizing:border-box}
    body{font-family:system-ui,-apple-system,sans-serif;-webkit-tap-highlight-color:transparent}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
    .dot-pulse{animation:pulse 2s ease-in-out infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .spin{animation:spin .8s linear infinite}
    ::-webkit-scrollbar{width:3px}
    ::-webkit-scrollbar-thumb{background:#404040;border-radius:9px}
    .zone-idle    {border-color:#404040}
    .zone-sending {border-color:#3b82f6;box-shadow:0 0 0 3px #3b82f618}
    .zone-done    {border-color:#22c55e;box-shadow:0 0 0 3px #22c55e18}
    .zone-error   {border-color:#ef4444;box-shadow:0 0 0 3px #ef444418}
  </style>
</head>
<body class="bg-neutral-950 text-neutral-100 min-h-screen flex flex-col items-center p-4 sm:p-8">
<div class="w-full max-w-md space-y-3">

  <!-- ── Header card ── -->
  <div class="bg-neutral-900 rounded-2xl border border-neutral-800 p-5 shadow-xl">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-base font-bold tracking-tight text-white">Local Drop</h1>
        <p class="text-xs text-neutral-500 mt-0.5">LAN file transfer</p>
      </div>
      <div class="flex items-center gap-1.5 bg-neutral-800 rounded-full px-3 py-1.5">
        <span id="dot" class="w-2 h-2 rounded-full bg-green-500 dot-pulse"></span>
        <span id="device-count" class="text-xs font-semibold text-neutral-200">— devices</span>
      </div>
    </div>
    <!-- device rows, hidden until 2+ connected -->
    <div id="device-list" class="hidden mt-3 space-y-1">
      <p class="text-xs font-semibold uppercase tracking-widest text-neutral-600 mb-1">Connected</p>
      <div id="device-items"></div>
    </div>
  </div>

  <!-- ── Send card ── -->
  <div class="bg-neutral-900 rounded-2xl border border-neutral-800 p-5 shadow-xl">
    <p class="text-xs font-semibold uppercase tracking-widest text-neutral-500 mb-3">
      Send to PC
      <span class="ml-1 text-neutral-600 normal-case font-normal tracking-normal">(tap or drag &amp; drop)</span>
    </p>

    <div id="drop-zone"
         class="border-2 border-dashed zone-idle rounded-xl p-7 text-center cursor-pointer
                transition-all duration-200 hover:border-neutral-500 select-none">
      <input type="file" id="file-input" class="hidden" multiple>

      <!-- idle state -->
      <div id="state-idle" class="space-y-2">
        <svg style="width:36px;height:36px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24"
             stroke="#9ca3af" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18"/>
        </svg>
        <p class="text-sm font-semibold text-neutral-200">Tap to upload files</p>
        <p class="text-xs text-neutral-600">Phone → PC</p>
      </div>

      <!-- uploading state -->
      <div id="state-uploading" class="hidden space-y-3">
        <svg class="spin" style="width:28px;height:28px;margin:0 auto;display:block" fill="none"
             viewBox="0 0 24 24" stroke="#3b82f6" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
        </svg>
        <p id="prog-filename" class="text-xs text-neutral-400 truncate px-4"></p>
        <div class="w-full bg-neutral-800 rounded-full h-1.5 overflow-hidden">
          <div id="prog-bar" class="h-1.5 rounded-full transition-all duration-100 bg-blue-500" style="width:0%"></div>
        </div>
        <p class="text-xs text-neutral-400"><span id="prog-pct">0</span>%</p>
      </div>

      <!-- done state -->
      <div id="state-done" class="hidden space-y-2">
        <svg style="width:32px;height:32px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24"
             stroke="#22c55e" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <p class="text-sm font-semibold text-green-400">Sent!</p>
      </div>

      <!-- error state -->
      <div id="state-error" class="hidden space-y-2">
        <svg style="width:32px;height:32px;margin:0 auto;display:block" fill="none" viewBox="0 0 24 24"
             stroke="#ef4444" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
        </svg>
        <p id="err-msg" class="text-sm font-semibold text-red-400">Upload failed</p>
      </div>
    </div>
  </div>

  <!-- ── Receive card ── -->
  <div class="bg-neutral-900 rounded-2xl border border-neutral-800 p-5 shadow-xl">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold uppercase tracking-widest text-neutral-500">Get from PC</p>
      <div class="flex items-center gap-1 text-xs text-neutral-600">
        <!-- download arrow -->
        <svg style="width:12px;height:12px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3"/>
        </svg>
        PC → Phone
      </div>
    </div>

    <div class="divide-y divide-neutral-800 max-h-56 overflow-y-auto -mx-1 px-1">
      {% if files %}
        {% for file in files %}
        <div class="flex items-center gap-3 py-2.5">
          <!-- file type icon -->
          <span class="shrink-0 text-neutral-600">{{ file_icon(file) }}</span>
          <span class="flex-1 text-xs text-neutral-300 truncate" title="{{ file }}">{{ file }}</span>
          <a href="/download/{{ file }}" download
             class="shrink-0 flex items-center gap-1 text-xs font-semibold
                    bg-neutral-800 hover:bg-neutral-700 text-neutral-200
                    px-2.5 py-1.5 rounded-lg transition-colors">
            <svg style="width:11px;height:11px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"/>
            </svg>
            Save
          </a>
        </div>
        {% endfor %}
      {% else %}
        <p class="text-xs text-neutral-600 py-4 text-center italic">
          No files shared from PC yet.
        </p>
      {% endif %}
    </div>
  </div>

</div><!-- /max-w-md -->

<script>
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const progBar    = document.getElementById('prog-bar');
const progPct    = document.getElementById('prog-pct');
const progFile   = document.getElementById('prog-filename');
const errMsg     = document.getElementById('err-msg');

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
  progBar.className = progBar.className.replace(/bg-\\S+/,'bg-blue-500');
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
      setTimeout(() => { showState('idle'); window.location.reload(); }, 1400);
    } else {
      errMsg.textContent = xhr.status === 403
        ? 'Session closed — server was stopped.' : 'Upload failed (' + xhr.status + ')';
      showState('error');
      setTimeout(() => showState('idle'), 3000);
    }
    fileInput.value = '';
  };
  xhr.onerror = () => {
    errMsg.textContent = 'Network error — are you on the same WiFi?';
    showState('error');
    setTimeout(() => showState('idle'), 3000);
  };
  xhr.send(fd);
}

// ── Device panel ──────────────────────────────────────────────────────────────
const deviceCount = document.getElementById('device-count');
const deviceList  = document.getElementById('device-list');
const deviceItems = document.getElementById('device-items');
const dot         = document.getElementById('dot');

function deviceIcon(type) {
  const S = 'display:inline-block;vertical-align:middle;width:14px;height:14px';
  if (type === 'mobile')
    return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18h3"/></svg>`;
  if (type === 'tablet')
    return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5h3m-6.75 2.25h10.5a2.25 2.25 0 002.25-2.25v-15a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 4.5v15a2.25 2.25 0 002.25 2.25z"/></svg>`;
  return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25A2.25 2.25 0 015.25 3h13.5A2.25 2.25 0 0121 5.25z"/></svg>`;
}

function roleIcon(role) {
  const S = 'display:inline-block;vertical-align:middle;width:13px;height:13px';
  if (role === 'sending')
    return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18"/></svg>`;
  if (role === 'receiving')
    return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="#4ade80" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3"/></svg>`;
  return `<svg style="${S}" fill="none" viewBox="0 0 24 24" stroke="#6b7280" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M2 12C2 12 5 5 12 5s10 7 10 7-3 7-10 7S2 12 2 12z"/></svg>`;
}

async function pollDevices() {
  try {
    const res  = await fetch('/api/devices');
    const data = await res.json();
    const list = data.devices || [];

    deviceCount.textContent = list.length + (list.length === 1 ? ' device' : ' devices');
    dot.className = 'w-2 h-2 rounded-full dot-pulse ' + (list.length > 1 ? 'bg-green-500' : 'bg-neutral-600');

    if (list.length > 1) {
      deviceList.classList.remove('hidden');
      deviceItems.innerHTML = list.map(d => `
        <div style="display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:8px;background:#262626">
          <span style="color:#9ca3af">${deviceIcon(d.device)}</span>
          <span style="font-size:11px;color:#d4d4d4;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d.id}</span>
          <span>${roleIcon(d.role)}</span>
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
    """Return an inline SVG icon string based on file extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    S = 'display:inline-block;width:14px;height:14px;vertical-align:middle'
    if ext in ['jpg','jpeg','png','gif','bmp','webp','heic','svg','ico']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#a78bfa" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/></svg>'
    if ext in ['mp4','mov','avi','mkv','webm']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#f472b6" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"/></svg>'
    if ext in ['mp3','wav','aac','flac','m4a','ogg']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#34d399" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"/></svg>'
    if ext in ['pdf','doc','docx','txt','xls','xlsx','ppt','pptx','csv']:
        return f'<svg style="{S}" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>'
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
    return render_template_string(HTML_TEMPLATE, files=sorted(set(all_files)),
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

@app.route('/upload', methods=['POST'])
def upload_file():
    global server_alive
    if not server_alive:
        return 'Session closed', 403

    token = request.form.get('session_token', '')
    if token != SESSION_TOKEN:
        return 'Invalid session — please refresh the page.', 403

    if 'files' not in request.files:
        return 'No files', 400

    client_ip           = request.remote_addr
    ua                  = request.headers.get('User-Agent', '')
    client_timestamp    = request.form.get('client_launch_timestamp')
    server_receive_time = time.time()

    register_client(client_ip, ua, 'sending')
    files = request.files.getlist('files')

    for file in files:
        if not file.filename:
            continue

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

        if client_timestamp:
            net_ms = max(0, round((server_receive_time - float(client_timestamp) / 1000.0) * 1000))
            net_display = f"{net_ms} ms"
        else:
            net_display = "n/a"

        ts = datetime.now().strftime('%H:%M:%S')
        P(f"\n  {GREEN}[{ts}] RECEIVED{RESET}  {color_filename(file.filename)}")
        P(f"   From    : {client_ip}  ({detect_device(ua)})")
        P(f"   Sorted  : {filepath}")
        P(f"   Inbox   : {inbox_path}")
        P(f"   Size    : {format_size(file_size)}")
        P(f"   Network : {net_display}   Write: {disk_ms} ms")
        P("   " + "-" * 52)

    register_client(client_ip, ua, 'viewer')

    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('/')
    return 'Success', 200

@app.route('/download/<path:filename>')
def download_file(filename):
    client_ip = request.remote_addr
    ua        = request.headers.get('User-Agent', '')
    register_client(client_ip, ua, 'receiving')

    # Search sorted dirs first, then inbox
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

    if platform.system() == 'Windows':
        os.system('color')

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