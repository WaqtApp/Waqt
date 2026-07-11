"""
build.py — Waqt v6 build script
================================
Creates dist/Waqt.exe — single executable, no Python required.

Usage:
    python build.py              # release build
    python build.py --debug      # console window for debugging
    python build.py --clean      # delete build/ dist/ first

Requirements:
    pip install pyinstaller pillow requests PyQt6
    pip install PyQt6-Qt6Multimedia   # optional, for azan sound

What gets bundled:
    - All Python source files
    - assets/ folder (icons, sounds, background_images)
    - All PyQt6 plugins (needed for SVG icons and multimedia)
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

APP_NAME    = "Waqt"
ENTRY_POINT = "main.py"
ROOT        = Path(__file__).parent.resolve()
DIST_DIR    = ROOT / "dist"
BUILD_DIR   = ROOT / "build"
ASSETS_DIR  = ROOT / "assets"

# Files and folders to include as data
DATA_DIRS = [
    ("core",   "core"),
    ("ui",     "ui"),
    ("assets", "assets"),
]

# Hidden imports that PyInstaller misses
HIDDEN_IMPORTS = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtSvg",
    "PyQt6.QtSvgWidgets",
    "PyQt6.QtMultimedia",
    "PyQt6.QtNetwork",
    "requests",
    "timezonefinder",
    "timezonefinder.timezone_names",
    "PIL",
    "PIL.Image",
    "pkg_resources.py2_warn",
]

# Runtime hooks to collect
COLLECT_ALL = [
    "PyQt6",
    "timezonefinder",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd: list[str], label: str = ""):
    """Run command and stream output."""
    if label:
        print(f"\n{'─'*60}")
        print(f"  {label}")
        print(f"{'─'*60}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"\n✗  Command failed: {' '.join(cmd)}")
        sys.exit(1)


def check_deps():
    """Check all required packages are installed."""
    print("\n📦  Checking dependencies…")
    required = {
        "PyInstaller":  "pyinstaller",
        "PyQt6":        "PyQt6",
        "requests":     "requests",
        "Pillow":        "Pillow",
    }
    optional = {
        "PyQt6-Qt6Multimedia": "PyQt6-Qt6Multimedia",
        "timezonefinder":      "timezonefinder",
    }
    missing_req = []
    for name, pkg in required.items():
        try:
            __import__(pkg.replace("-", "_").split(".")[0])
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name}  (required)")
            missing_req.append(pkg)

    for name, pkg in optional.items():
        try:
            __import__(pkg.replace("-", "_").split(".")[0])
            print(f"  ✓ {name}  (optional)")
        except ImportError:
            print(f"  · {name}  (optional — skipping)")

    if missing_req:
        print(f"\n  Install missing: pip install {' '.join(missing_req)}")
        sys.exit(1)


def make_icon() -> str | None:
    """Convert app_icon.png → Waqt.ico for the .exe."""
    ico_path = str(ROOT / "assets" / "icons" / "Waqt.ico")
    png_path = ROOT / "assets" / "icons" / "app_icon.png"

    if Path(ico_path).exists():
        return ico_path

    if not png_path.exists():
        print("  · No app_icon.png found — .exe will use default icon")
        return None

    try:
        from PIL import Image
        img = Image.open(str(png_path)).convert("RGBA")
        sizes = [(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
        imgs  = [img.resize(s, Image.LANCZOS) for s in sizes]
        imgs[0].save(ico_path, format="ICO", sizes=[s for s in sizes],
                     append_images=imgs[1:])
        print(f"  ✓ Icon created: {ico_path}")
        return ico_path
    except Exception as e:
        print(f"  · Could not create icon: {e}")
        return None


def build(debug: bool = False, clean: bool = False):
    os.chdir(ROOT)

    if clean:
        print("\n🗑   Cleaning build artifacts…")
        for d in [BUILD_DIR, DIST_DIR]:
            if d.exists():
                shutil.rmtree(d)
                print(f"  ✓ Removed {d}")

    check_deps()

    icon_path = make_icon()

    # ── Build command ──────────────────────────────────────────────────────────
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name", APP_NAME,
    ]

    # Window mode (no console) unless debug
    if not debug:
        cmd += ["--windowed"]
    else:
        print("\n  ⚠  Debug build: console window will be visible")

    # Icon
    if icon_path:
        cmd += ["--icon", icon_path]

    # Data files
    for src, dst in DATA_DIRS:
        src_path = ROOT / src
        if src_path.exists():
            cmd += ["--add-data", f"{src_path}{sep}{dst}"]

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    # Collect all (includes Qt plugins)
    for pkg in COLLECT_ALL:
        try:
            cmd += ["--collect-all", pkg]
        except Exception:
            pass

    # PyQt6 SVG plugin (needed for sidebar icons)
    cmd += ["--collect-data", "PyQt6"]

    # Optimize
    cmd += [
        "--optimize", "2",
        # Exclude heavy unused modules
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
    ]

    cmd.append(ENTRY_POINT)

    run(cmd, f"Building {APP_NAME}.exe…")

    # ── Post-build ─────────────────────────────────────────────────────────────
    exe = DIST_DIR / f"{APP_NAME}.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n{'═'*60}")
        print(f"  ✓  Build complete!")
        print(f"  📦  {exe}")
        print(f"  📏  Size: {size_mb:.1f} MB")
        print(f"{'═'*60}")

        # Copy assets next to exe for any relative-path references
        exe_assets = DIST_DIR / "assets"
        if ASSETS_DIR.exists() and not exe_assets.exists():
            shutil.copytree(str(ASSETS_DIR), str(exe_assets))
            print(f"  ✓  Assets copied to dist/assets/")

        print(f"\n  Share dist/{APP_NAME}.exe — no Python required!\n")
    else:
        print("\n✗  Build failed — exe not found")
        sys.exit(1)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME}.exe")
    parser.add_argument("--debug", action="store_true",
                        help="Show console window (for debugging)")
    parser.add_argument("--clean", action="store_true",
                        help="Clean build/dist before building")
    args = parser.parse_args()
    build(debug=args.debug, clean=args.clean)