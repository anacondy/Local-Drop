"""
Flask route tests via the test client — happy paths and basic contract checks.
"""
import io
import json
import os
import time

import local_drop as L


def _upload(client, token, files, ajax=True, timestamp=None):
    """files: list of (bytes, filename). Returns the response."""
    if timestamp is None:
        timestamp = str(int(time.time() * 1000))
    data = {"session_token": token, "client_launch_timestamp": timestamp}
    data["files"] = [(io.BytesIO(payload), name) for payload, name in files]
    headers = {"X-Requested-With": "XMLHttpRequest"} if ajax else {}
    return client.post("/upload", data=data, content_type="multipart/form-data", headers=headers)


# ── index page ────────────────────────────────────────────────────────────────
def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "<html" in body.lower()
    assert "Local Drop" in body or "Vault" in body


def test_index_registers_caller_as_device(client, app_module):
    client.get("/")
    assert "127.0.0.1" in app_module.connected_clients


# ── manifest ──────────────────────────────────────────────────────────────────
def test_manifest_json(client):
    r = client.get("/manifest.json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Local Drop"
    assert data["display"] == "standalone"
    assert data["icons"] and "image/svg+xml" in data["icons"][0]["src"]


# ── api/ping & disconnect ─────────────────────────────────────────────────────
def test_ping_registers_and_returns_ok(client, app_module):
    r = client.post("/api/ping")
    assert r.status_code == 200
    assert r.get_data(as_text=True) == "ok"
    assert "127.0.0.1" in app_module.connected_clients


def test_disconnect_removes_client(client, app_module):
    client.post("/api/ping")
    assert "127.0.0.1" in app_module.connected_clients
    r = client.post("/api/disconnect")
    assert r.status_code == 204
    assert "127.0.0.1" not in app_module.connected_clients


# ── api/devices ───────────────────────────────────────────────────────────────
def test_devices_returns_list_and_my_id(client):
    r = client.get("/api/devices")
    assert r.status_code == 200
    data = r.get_json()
    assert "devices" in data and isinstance(data["devices"], list)
    assert data["my_id"] == "127.0.0.1"


def test_devices_shows_connected_node(client, app_module):
    app_module.register_client("192.168.0.42", "Mozilla/5.0 (iPhone)", "viewer")
    data = client.get("/api/devices").get_json()
    ids = [d["id"] for d in data["devices"]]
    assert "192.168.0.42" in ids
    # each device dict must expose the documented fields
    node = next(d for d in data["devices"] if d["id"] == "192.168.0.42")
    assert node["device"] == "mobile"
    assert node["role"] == "viewer"


# ── api/files ─────────────────────────────────────────────────────────────────
def test_api_files_lists_with_icons(client, app_module, home):
    os.makedirs(os.path.join(str(home), "Pictures", "LocalDrop"))
    open(os.path.join(str(home), "Pictures", "LocalDrop", "pic.png"), "w").close()
    r = client.get("/api/files")
    assert r.status_code == 200
    data = r.get_json()
    names = [f["name"] for f in data["files"]]
    assert "pic.png" in names
    icon = next(f["icon"] for f in data["files"] if f["name"] == "pic.png")
    assert icon.startswith("<svg")


# ── upload happy path ─────────────────────────────────────────────────────────
def test_upload_text_file(client, session_token, app_module, home):
    r = _upload(client, session_token, [(b"hello world", "note.txt")])
    assert r.status_code == 200
    # routed into Documents/LocalDrop
    saved = os.path.join(str(home), "Documents", "LocalDrop", "note.txt")
    assert os.path.exists(saved)
    assert open(saved).read() == "hello world"


def test_upload_image_routes_to_pictures(client, session_token, home):
    r = _upload(client, session_token, [(b"\x89PNGdata", "snap.jpg")])
    assert r.status_code == 200
    assert os.path.exists(os.path.join(str(home), "Pictures", "LocalDrop", "snap.jpg"))


def test_upload_multiple_files(client, session_token, home):
    r = _upload(client, session_token, [
        (b"a", "a.txt"),
        (b"b", "b.txt"),
        (b"\x00\x01", "img.png"),
    ])
    assert r.status_code == 200
    assert os.path.exists(os.path.join(str(home), "Documents", "LocalDrop", "a.txt"))
    assert os.path.exists(os.path.join(str(home), "Documents", "LocalDrop", "b.txt"))
    assert os.path.exists(os.path.join(str(home), "Pictures", "LocalDrop", "img.png"))


def test_upload_duplicate_gets_unique_name(client, session_token, home):
    _upload(client, session_token, [(b"v1", "dup.txt")])
    _upload(client, session_token, [(b"v2", "dup.txt")])
    docs = os.path.join(str(home), "Documents", "LocalDrop")
    assert os.path.exists(os.path.join(docs, "dup.txt"))
    assert os.path.exists(os.path.join(docs, "dup (1).txt"))
    assert open(os.path.join(docs, "dup.txt")).read() == "v1"
    assert open(os.path.join(docs, "dup (1).txt")).read() == "v2"


def test_upload_without_ajax_redirects(client, session_token):
    r = _upload(client, session_token, [(b"x", "a.txt")], ajax=False)
    assert r.status_code in (301, 302, 303)
    assert r.headers.get("Location", "").endswith("/")


def test_upload_missing_client_timestamp_does_not_crash(client, session_token):
    # client_launch_timestamp omitted entirely
    data = {"session_token": session_token, "files": [(io.BytesIO(b"x"), "a.txt")]}
    r = client.post("/upload", data=data, content_type="multipart/form-data",
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200


# ── download happy path ───────────────────────────────────────────────────────
def test_download_existing_file(client, app_module, home):
    p = os.path.join(str(home), "Pictures", "LocalDrop", "dl.png")
    os.makedirs(os.path.dirname(p))
    with open(p, "wb") as f:
        f.write(b"\x89PNGbytes")
    r = client.get("/download/dl.png")
    assert r.status_code == 200
    assert r.get_data() == b"\x89PNGbytes"


def test_download_missing_returns_404(client):
    r = client.get("/download/does_not_exist.xyz")
    assert r.status_code == 404
