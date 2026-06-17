# Local Drop — Rigorous Test Report

**Date:** 2026-06-17
**Scope:** Full automated test suite for `local_drop.py` (Flask LAN file-transfer PWA)

---

## TL;DR

- Built a **98-test pytest suite** covering helpers, file routing, filesystem
  handling, all 9 Flask routes, device tracking (incl. concurrency), and security.
- **2 critical path-traversal vulnerabilities found and fixed.**
- After fixes: **98/98 pass**, `flake8` clean (exit 0).
- Your GitHub CI was upgraded to actually run the tests (it previously only linted).

```
tests/ ........................ 98 passed in 0.30s
flake8 (CI gate) .............. 0 issues
```

---

## 🔴 Vulnerabilities Found & Fixed

### 1. Arbitrary File READ via `/download/<path:filename>`  (HIGH/CRITICAL)

Anyone on the same WiFi could read **any file** the server process can access
(e.g. `~/.ssh/id_rsa`, browser cookies, `/etc/passwd`):

```
GET /download/..%2f..%2fsecret.txt   ->  HTTP 200, body = "PASSWORD=hunter2"
```

**Root cause:** the route did `os.path.join(base_dir, filename)` and served
whatever `os.path.exists()` resolved, with no containment check.

**Fix:** resolve to real paths and reject anything that escapes the base dir:
```python
base   = os.path.realpath(d)
target = os.path.realpath(os.path.join(d, filename))
inside = os.path.commonpath([base, target]) == base   # False for ../
if inside and os.path.isfile(target): ...
```
After fix → `HTTP 404`.

### 2. Arbitrary File WRITE / path escape via upload filename  (HIGH)

A crafted filename escaped the target folder:
```
upload filename "../../owned.txt"  ->  written to ~/owned.txt (outside target dir)
```

**Fix:** strip directory components from the uploaded filename before saving:
```python
safe_name = file.filename.replace('\\', '/').split('/')[-1]
if not safe_name or safe_name in ('.', '..'):
    continue
```
After fix → file lands correctly in `Documents/LocalDrop/owned.txt`.

### Bonus lint fix
Removed a redundant `global server_alive` in `upload_file()` (read-only use;
flagged by flake8 `F824`).

---

## Test Suite Layout (`tests/`)

| File | Covers |
|------|--------|
| `conftest.py` | Isolated HOME (never touches your real disk), state reset, test client |
| `test_utils.py` | `detect_device`, `format_size`, `color_filename`, `get_local_ip` |
| `test_routing.py` | `route_file` (all categories/case), `file_icon` |
| `test_file_handling.py` | unique naming, scanning, newest-first sort, dedupe, inbox |
| `test_routes.py` | All 9 routes: index, manifest, ping, disconnect, devices, files, upload, download |
| `test_security.py` | session-token enforcement, shutdown lock, path traversal (both) |
| `test_devices.py` | register/prune lifecycle, custom timeouts, thread-safety (50 threads) |

---

## Files changed vs your original

1. `local_drop.py` — 3 small edits (2 security fixes + lint fix)
2. `.github/workflows/ci.yml` — replaced "import check" with `pytest tests/ -q`
3. `tests/` — 7 new files (the suite)

A ready-to-apply git patch is at **`localdrop_security_fix.patch`** (applies to
`local_drop.py` + `ci.yml`; the `tests/` folder is new).

---

## How to get this back to your Windows repo

You have two equivalent options (both in your `Local-Drop` folder, on a branch):

### Option A — git patch (for the source fixes) + copy tests/
```powershell
git checkout -b testing
# save the patch text into localdrop_security_fix.patch, then:
git apply localdrop_security_fix.patch
# copy the tests\ folder in
git add -A && git commit -m "fix: block path traversal; add pytest suite"
pytest tests\ -q
```

### Option B — restore the whole fixed project from bundle
Use `LocalDrop_FIXED_bundle.txt` (the entire corrected project, one text file,
verified to restore byte-for-byte with all 18 files). Restore over your folder;
unchanged files (`run.bat`, etc.) simply stay as-is.
