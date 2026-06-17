"""Pure-function unit tests for helpers in local_drop.py."""
import pytest

import local_drop as L


# ── detect_device ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ua, expected", [
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)", "mobile"),
    ("Mozilla/5.0 (Linux; Android 13; Pixel 7) Mobile Safari", "mobile"),
    ("Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)", "tablet"),
    ("Mozilla/5.0 (Linux; Android 11; Galaxy Tab) Safari", "tablet"),   # android w/o mobile
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome", "desktop"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X) Safari", "desktop"),
    ("curl/8.0", "desktop"),
    ("", "desktop"),
])
def test_detect_device(app_module, ua, expected):
    assert L.detect_device(ua) == expected


def test_detect_device_case_insensitive(app_module):
    assert L.detect_device("IPAD") == "tablet"
    assert L.detect_device("iPhOnE") == "mobile"


# ── format_size ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("n, expected", [
    (0, "0.00 KB"),
    (1, "0.00 KB"),
    (500, "0.49 KB"),
    (1023, "1.00 KB"),     # 1023/1024 = 0.999 -> "1.00 KB"
    (1024, "1.00 KB"),
    (1024 * 512, "512.00 KB"),
    (1024 ** 2, "1.00 MB"),
    (1024 ** 2 * 5, "5.00 MB"),
    (1024 ** 3, "1.00 GB"),
    (1024 ** 3 * 2 + 1024 ** 2 * 500, "2.49 GB"),
])
def test_format_size(app_module, n, expected):
    assert L.format_size(n) == expected


# ── color_filename ────────────────────────────────────────────────────────────
def test_color_filename_with_ext(app_module):
    out = L.color_filename("report.pdf")
    assert L.PURPLE in out          # name part colored
    assert L.OCEAN in out           # extension colored
    assert L.RESET in out
    assert "report" in out and "pdf" in out


def test_color_filename_no_ext(app_module):
    out = L.color_filename("Makefile")
    assert L.PURPLE in out
    assert "Makefile" in out


# ── get_local_ip ──────────────────────────────────────────────────────────────
def test_get_local_ip_returns_string(app_module):
    ip = L.get_local_ip()
    assert isinstance(ip, str)
    # must be a plausible IPv4 (fallback 127.0.0.1 in sandboxed nets)
    octets = ip.split(".")
    assert len(octets) == 4
    assert all(o.isdigit() and 0 <= int(o) <= 255 for o in octets)


def test_get_local_ip_handles_failure(monkeypatch, app_module):
    import socket as _socket
    def boom(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(_socket.socket, "connect", boom)
    assert L.get_local_ip() == "127.0.0.1"
