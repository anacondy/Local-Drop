"""
Security tests — these encode the SECURE behavior the app SHOULD exhibit.
A failing test here = a real security bug.
"""
import io
import os
import time

import pytest

import local_drop as L


def _upload(client, token, files, ajax=True):
    data = {"session_token": token, "client_launch_timestamp": str(int(time.time() * 1000)),
            "files": [(io.BytesIO(p), n) for p, n in files]}
    headers = {"X-Requested-With": "XMLHttpRequest"} if ajax else {}
    return client.post("/upload", data=data, content_type="multipart/form-data", headers=headers)


# ── 1. Session-token enforcement on upload ────────────────────────────────────
def test_upload_rejects_missing_token(client):
    data = {"files": [(io.BytesIO(b"x"), "a.txt")]}
    r = client.post("/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 403


def test_upload_rejects_wrong_token(client):
    data = {"session_token": "deadbeef-not-the-real-token",
            "files": [(io.BytesIO(b"x"), "a.txt")]}
    r = client.post("/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 403


def test_upload_rejects_empty_token(client):
    data = {"session_token": "", "files": [(io.BytesIO(b"x"), "a.txt")]}
    r = client.post("/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 403


def test_upload_accepts_correct_token(client, session_token):
    r = _upload(client, session_token, [(b"x", "a.txt")])
    assert r.status_code == 200


# ── 2. Shutdown lock: uploads rejected after server stop ──────────────────────
def test_upload_rejected_after_shutdown(client, session_token, app_module):
    app_module.server_alive = False
    r = _upload(client, session_token, [(b"x", "a.txt")])
    assert r.status_code == 403


# ── 3. Path traversal in /download/<path:filename> ────────────────────────────
# The download route joins the user-supplied filename onto a base dir and serves
# whatever os.path.exists() resolves. If '..' survives, an attacker on the LAN
# can read arbitrary files. We assert the SECRET must NOT be retrievable.
TRAVERSAL_PAYLOADS = [
    "../../secret.txt",
    "../../../secret.txt",
    "..%2f..%2fsecret.txt",
    "..%5c..%5csecret.txt",
    "....//....//secret.txt",
    "%2e%2e/%2e%2e/secret.txt",
]


@pytest.fixture
def secret_outside_allowed_dirs(app_module, home):
    """Place a secret file in HOME root (outside every allowed subdir)."""
    secret = os.path.join(str(home), "secret.txt")
    with open(secret, "w") as f:
        f.write("TOPSECRET-LEAK")
    # also create a legit file so the route's search loop enters
    legit_dir = os.path.join(str(home), "Pictures", "LocalDrop")
    os.makedirs(legit_dir, exist_ok=True)
    with open(os.path.join(legit_dir, "ok.png"), "w") as f:
        f.write("ok")
    return secret


@pytest.mark.parametrize("payload", TRAVERSAL_PAYLOADS)
def test_download_path_traversal_blocked(client, secret_outside_allowed_dirs, payload):
    r = client.get(f"/download/{payload}")
    # MUST NOT return the secret content
    assert r.status_code == 404, f"traversal payload {payload!r} leaked a file"
    assert b"TOPSECRET-LEAK" not in r.get_data()


# ── 4. Upload cannot escape its target dir via filename ───────────────────────
def test_upload_filename_traversal(client, session_token, home):
    # Flask/Werkzeug normally strips path components; ensure no file lands at HOME root
    _upload(client, session_token, [(b"escaped", "../../evil.txt")])
    assert not os.path.exists(os.path.join(str(home), "evil.txt"))
    assert not os.path.exists(os.path.join(str(home), "..", "evil.txt"))
