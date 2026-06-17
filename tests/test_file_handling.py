"""
Tests for filesystem handling: unique naming, directory scanning, sorting,
and platform-aware path resolution.
"""
import os
import time

import local_drop as L


# ── get_unique_filename ───────────────────────────────────────────────────────
def test_unique_filename_first_use(app_module, tmp_path):
    expected = os.path.join(str(tmp_path), "a.txt")
    assert L.get_unique_filename(str(tmp_path), "a.txt") == expected


def test_unique_filename_collision(app_module, tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "a.txt"), "w").close()                       # original
    got = L.get_unique_filename(d, "a.txt")
    assert got == os.path.join(d, "a (1).txt")


def test_unique_filename_multi_collision(app_module, tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "a.txt"), "w").close()
    open(os.path.join(d, "a (1).txt"), "w").close()
    open(os.path.join(d, "a (2).txt"), "w").close()
    got = L.get_unique_filename(d, "a.txt")
    assert got == os.path.join(d, "a (3).txt")


def test_unique_filename_preserves_extension(app_module, tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "song.mp3"), "w").close()
    got = L.get_unique_filename(d, "song.mp3")
    assert got.endswith(" (1).mp3")


def test_unique_filename_two_distinct_files(app_module, tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "x.txt"), "w").close()
    # different filename should not be affected by x.txt existing
    assert L.get_unique_filename(d, "y.txt") == os.path.join(d, "y.txt")


# ── get_all_network_files ─────────────────────────────────────────────────────
def _create(path, content="x", mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_scan_returns_empty_when_no_dirs(app_module):
    assert L.get_all_network_files() == []


def test_scan_lists_files_in_sorted_dirs(app_module, home):
    _create(os.path.join(str(home), "Pictures", "LocalDrop", "a.jpg"), mtime=1000)
    _create(os.path.join(str(home), "Documents", "LocalDrop", "b.pdf"), mtime=2000)
    files = L.get_all_network_files()
    assert set(files) == {"a.jpg", "b.pdf"}


def test_scan_newest_first(app_module, home):
    _create(os.path.join(str(home), "Pictures", "LocalDrop", "old.jpg"), mtime=1000)
    _create(os.path.join(str(home), "Pictures", "LocalDrop", "new.jpg"), mtime=9000)
    files = L.get_all_network_files()
    assert files[0] == "new.jpg"
    assert files[1] == "old.jpg"


def test_scan_includes_inbox(app_module, home):
    _create(os.path.join(str(home), "LocalDrop-Inbox", "from_inbox.txt"), mtime=5000)
    assert "from_inbox.txt" in L.get_all_network_files()


def test_scan_dedupes_by_basename_across_dirs(app_module, home):
    """Same filename in two dirs is reported once (basename keying)."""
    _create(os.path.join(str(home), "Pictures", "LocalDrop", "dup.jpg"), mtime=1000)
    _create(os.path.join(str(home), "LocalDrop-Inbox", "dup.jpg"), mtime=2000)
    files = L.get_all_network_files()
    assert files.count("dup.jpg") == 1


def test_scan_ignores_directories(app_module, home):
    os.makedirs(os.path.join(str(home), "Pictures", "LocalDrop", "subdir"))
    _create(os.path.join(str(home), "Pictures", "LocalDrop", "real.png"))
    files = L.get_all_network_files()
    assert files == ["real.png"]


# ── platform path resolution ──────────────────────────────────────────────────
def test_inbox_under_home(app_module, home):
    assert L.get_inbox_directory() == os.path.join(str(home), "LocalDrop-Inbox")


def test_target_dirs_keys(app_module):
    assert set(L.get_target_directories()) == {"Images", "Videos", "Music", "Docs", "Other"}


def test_target_dirs_each_has_localdrop_suffix(app_module, home):
    for path in L.get_target_directories().values():
        assert path.endswith("LocalDrop")
        assert str(home) in path
