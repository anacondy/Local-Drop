"""Tests for file-type routing (route_file) and icon rendering (file_icon)."""
import pytest

import local_drop as L


# ── route_file ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("filename, category", [
    ("photo.jpg", "Images"), ("PHOTO.PNG", "Images"), ("anim.gif", "Images"),
    ("clip.mp4", "Videos"), ("movie.mkv", "Videos"), ("trailer.mov", "Videos"),
    ("song.mp3", "Music"), ("beat.flac", "Music"), ("voice.wav", "Music"),
    ("report.pdf", "Docs"), ("notes.txt", "Docs"), ("data.csv", "Docs"),
    ("budget.xlsx", "Docs"), ("page.html", "Docs") if False else ("readme.md", "Docs"),
    ("archive.zip", "Other"), ("setup.exe", "Other"), ("data.bin", "Other"),
])
def test_route_file_categories(app_module, filename, category):
    dirs = L.get_target_directories()
    assert L.route_file(filename) == dirs[category]


def test_route_file_no_extension(app_module):
    assert L.route_file("Makefile") == L.get_target_directories()["Other"]


def test_route_file_unknown_extension(app_module):
    assert L.route_file("mystery.xyz123") == L.get_target_directories()["Other"]


def test_route_file_case_insensitive(app_module):
    img = L.get_target_directories()["Images"]
    assert L.route_file("PIC.JPEG") == img
    assert L.route_file("Pic.Jpg") == img


# ── file_icon ─────────────────────────────────────────────────────────────────
def test_file_icon_returns_svg(app_module):
    svg = L.file_icon("x.png")
    assert isinstance(svg, str)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")


@pytest.mark.parametrize("filename, color_hint", [
    ("img.png", "#c084fc"),     # purple -> image
    ("vid.mp4", "#f472b6"),     # pink   -> video
    ("snd.mp3", "#34d399"),     # green  -> audio
    ("doc.pdf", "#38bdf8"),     # blue   -> doc
])
def test_file_icon_color_by_type(app_module, filename, color_hint):
    assert color_hint in L.file_icon(filename)


def test_file_icon_unknown_uses_default_gray(app_module):
    assert "#9ca3af" in L.file_icon("blob.zzz")
