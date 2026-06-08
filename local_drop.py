import os
import socket
import qrcode
import time
import logging
import platform
from pathlib import Path
from flask import Flask, request, render_template_string, send_file, jsonify, redirect

# Disable default Flask development server logs to keep terminal logs readable
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
# Permit files up to 2 Gigabytes per transmission block
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024 

# Progressive Web App configuration manifest mapping
MANIFEST_JSON = {
    "name": "Local Drop",
    "short_name": "LocalDrop",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0a0a",
    "theme_color": "#0a0a0a",
    "icons": [
        {
            # A modern minimalist custom transfer emblem for your home screen app icon
            "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2'><path stroke-linecap='round' stroke-linejoin='round' d='M12 3v13m0 0l-4-4m4 4l4-4M4 19h16'/></svg>",
            "sizes": "192x192",
            "type": "image/svg+xml"
        }
    ]
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Local Drop Share</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a0a0a">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
    </style>
</head>
<body class="bg-neutral-950 text-neutral-100 min-h-screen flex flex-col items-center p-4 sm:p-8">
    <div class="w-full max-w-md bg-neutral-900 rounded-2xl border border-neutral-800 p-6 space-y-6 shadow-2xl">
        <header class="text-center">
            <h1 class="text-xl font-bold tracking-tight text-white">Local Drop</h1>
            <p class="text-xs text-neutral-400 mt-1">Direct device-to-device wireless fast transfer</p>
        </header>

        <div id="drop-zone" class="border-2 border-dashed border-neutral-700 rounded-xl p-8 text-center cursor-pointer hover:border-neutral-500 transition-colors bg-neutral-900/50">
            <input type="file" id="file-input" class="hidden" multiple>
            <div class="space-y-2">
                <svg class="mx-auto h-8 w-8 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                </svg>
                <p class="text-sm font-medium text-neutral-200">Tap to upload files</p>
            </div>
        </div>

        <div id="progress-container" class="hidden space-y-2">
            <div class="flex justify-between text-xs font-medium text-neutral-400">
                <span id="progress-status">Uploading...</span>
                <span id="progress-percent">0%</span>
            </div>
            <div class="w-full bg-neutral-800 rounded-full h-1.5 overflow-hidden">
                <div id="progress-bar" class="bg-white h-1.5 rounded-full transition-all duration-150" style="width: 0%"></div>
            </div>
        </div>

        <div class="space-y-3 pt-4 border-t border-neutral-800">
            <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Available Files on PC</h2>
            <div class="divide-y divide-neutral-800 max-h-48 overflow-y-auto pr-1">
                {% if files %}
                    {% for file in files %}
                    <div class="flex items-center justify-between py-2.5 text-sm">
                        <span class="truncate text-neutral-300 font-medium max-w-[70%]">{{ file }}</span>
                        <a href="/download/{{ file }}" download class="text-xs font-semibold text-black bg-white hover:bg-neutral-200 transition-colors px-3 py-1.5 rounded-lg">
                            Get
                        </a>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="text-xs text-neutral-500 py-2 italic text-center">Place files in LocalDrop folders on PC to see them here.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const progressStatus = document.getElementById('progress-status');

        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => handleFiles(fileInput.files));
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
            dropZone.addEventListener(ev, e => e.preventDefault(), false);
        });
        dropZone.addEventListener('drop', (e) => handleFiles(e.dataTransfer.files));

        function handleFiles(files) {
            if (files.length === 0) return;
            const formData = new FormData();
            
            // Capture precise client machine timestamp right before bytes enter the stream
            formData.append('client_launch_timestamp', Date.now());
            
            for (let i = 0; i < files.length; i++) { 
                formData.append('files', files[i]); 
            }
            
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/upload', true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressPercent.innerText = '0%';
            progressStatus.innerText = 'Uploading...';

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressPercent.innerText = percent + '%';
                }
            });

            xhr.onload = function() {
                if (xhr.status === 200) {
                    progressStatus.innerText = 'Finished!';
                    setTimeout(() => window.location.reload(), 600);
                } else {
                    alert('Network dropped or server rejected submission.');
                }
            };
            xhr.send(formData);
        }
    </script>
</body>
</html>
"""

def get_target_directories():
    """Identifies host OS platform structure and paths files into correct user directories."""
    home = str(Path.home())
    system = platform.system() 
    
    def resolve_path(*subdirs):
        if system == 'Windows':
            od_path = os.path.join(home, 'OneDrive', *subdirs, 'LocalDrop')
            if os.path.exists(os.path.join(home, 'OneDrive', *subdirs)):
                return od_path
        return os.path.join(home, *subdirs, 'LocalDrop')

    if system == 'Darwin': # macOS directory maps
        return {
            'Images': resolve_path('Pictures'),
            'Videos': resolve_path('Movies'),
            'Music':  resolve_path('Music'),
            'Docs':   resolve_path('Documents'),
            'Other':  resolve_path('Downloads')
        }
    else: # Linux and Windows standard directory fallback mapping
        return {
            'Images': resolve_path('Pictures'),
            'Videos': resolve_path('Videos'),
            'Music':  resolve_path('Music'),
            'Docs':   resolve_path('Documents'),
            'Other':  resolve_path('Downloads')
        }

def route_file(filename):
    """Sorts all files into target directories based on extension matching."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    dirs = get_target_directories()
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'raw', 'svg', 'tiff', 'ico']: 
        return dirs['Images']
    if ext in ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'ts']: 
        return dirs['Videos']
    if ext in ['mp3', 'wav', 'aac', 'flac', 'm4a', 'ogg', 'wma', 'alac', 'opus']: 
        return dirs['Music']
    if ext in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'json', 'xml', 'md']: 
        return dirs['Docs']
    
    return dirs['Other']

def format_size(size_in_bytes):
    """Parses binary byte streams into human-readable notations."""
    if size_in_bytes >= 1024 * 1024 * 1024: return f"{size_in_bytes / (1024 ** 3):.2f} GB"
    elif size_in_bytes >= 1024 * 1024: return f"{size_in_bytes / (1024 ** 2):.2f} MB"
    else: return f"{size_in_bytes / 1024:.2f} KB"

def get_local_ip():
    """Extracts internal operational LAN network interface IP identification string."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    return local_ip

@app.route('/manifest.json')
def serve_manifest():
    return jsonify(MANIFEST_JSON)

@app.route('/')
def index():
    all_files = []
    for dir_path in get_target_directories().values():
        if os.path.exists(dir_path):
            all_files.extend(os.listdir(dir_path))
    return render_template_string(HTML_TEMPLATE, files=all_files)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Saves file packages and displays processing versus wire transmission metrics."""
    if 'files' not in request.files:
        return 'No files uploaded', 400
    
    # Extract the client timing injection from the multi-part data packet
    client_timestamp = request.form.get('client_launch_timestamp')
    server_receive_time = time.time()
    
    files = request.files.getlist('files')
    
    for file in files:
        if file.filename:
            disk_start = time.time()
            target_dir = route_file(file.filename)
            os.makedirs(target_dir, exist_ok=True)
            
            filepath = os.path.join(target_dir, file.filename)
            file.save(filepath)
            disk_end = time.time()
            
            file_size = os.path.getsize(filepath)
            disk_duration = round((disk_end - disk_start) * 1000)
            
            # Compute total actual over-the-air network transmission transit time
            if client_timestamp:
                total_network_duration = round((server_receive_time - (float(client_timestamp) / 1000.0)) * 1000)
                if total_network_duration < 0: total_network_duration = 0
                network_display = f"{total_network_duration} ms"
            else:
                network_display = "Unable to compute (Incompatible client header)"

            print(f"\n✅ SUCCESS: {file.filename}")
            print(f"   📂 Path: {filepath}")
            print(f"   📦 Size: {format_size(file_size)}")
            print(f"   📡 Actual Network Transit Time: {network_display}")
            print(f"   💾 System Drive Write Duration: {disk_duration} ms")
            print("-" * 55)
            
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('/')
        
    return 'Success', 200

@app.route('/download/<filename>')
def download_file(filename):
    for dir_path in get_target_directories().values():
        target_path = os.path.join(dir_path, filename)
        if os.path.exists(target_path):
            return send_file(target_path, as_attachment=True)
    return "Target file not indexed", 404

if __name__ == '__main__':
    ip_addr = get_local_ip()
    port_num = 5001
    hosting_url = f"http://{ip_addr}:{port_num}"
    
    print("\n" + "="*55)
    print("      🚀 LOCAL DROP SHARE SERVER ACTIVE")
    print("="*55)
    print(f"\nUrl link route: {hosting_url}")
    print("If you toggle routing band connections, do not close this console.")
    
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(hosting_url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    
    app.run(host='0.0.0.0', port=port_num, debug=False, threaded=True)
