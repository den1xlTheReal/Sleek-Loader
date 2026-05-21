# Sleek Loader

> A minimalist video downloader with a clean GUI. Supports YouTube, Instagram, TikTok, Twitter/X, and hundreds more sites via yt-dlp.

---

## Features

- **Any quality** — choose your preferred resolution or format
- **Audio-only mode** — extract audio directly
- **Insta Cast** — skip the confirmation dialog for rapid-fire downloads
- **Persistent settings** — remembers your last-used options
- **In-app yt-dlp updates** — update the downloader without leaving the app

---

## Prerequisites

Before anything else, make sure these are installed and available in your system PATH:

|Dependency|Required for|
|---|---|
|[Python](https://www.python.org/downloads/)|Running / compiling the app|
|[yt-dlp](https://github.com/yt-dlp/yt-dlp)|Video downloading|
|[ffmpeg + ffprobe](https://ffmpeg.org/download.html)|Merging/converting media|
|`customtkinter`|GUI (install via pip)|
|`pyinstaller`|Compiling to .exe (optional)|

```bash
pip install customtkinter pyinstaller
```

---

## Installation

### Method 1 — Run with Python

No compilation needed. Run directly from source:

```bash
python main.py
```

> Note: A terminal window will open alongside the app.

---

### Method 2 — Compile: Portable .exe ✅ Recommended

Produces an `.exe` that depends on external `yt-dlp.exe`, `ffmpeg.exe`, and `ffprobe.exe` in the same folder. This means **in-app yt-dlp updates work correctly** — they update the actual file on disk.

```bash
python -m PyInstaller --onefile --noconsole --icon=icon.ico --name="Sleek Loader" main.py
```

Folder structure required at runtime:

```
📁 your-folder/
├── Sleek Loader.exe
├── yt-dlp.exe
├── ffmpeg.exe
└── ffprobe.exe
```

---

### Method 3 — Compile: Fully Standalone .exe

Bundles all dependencies inside the `.exe` — no separate files needed. Trade-off: **in-app yt-dlp updates won't persist** between launches (the bundled version resets on each run). To get a new yt-dlp version, recompile.

```bash
python -m PyInstaller --onefile --noconsole --icon=icon.ico --name="Sleek Loader" --add-data "yt-dlp.exe;." --add-data "ffmpeg.exe;." --add-data "ffprobe.exe;." main.py
```

---

## Notes

- The icon can be swapped freely — just rename your file to `icon.ico`
- For a list of supported sites, see the [yt-dlp supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)