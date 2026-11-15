# PyInstaller recipe for the downloadable app. From the repo root:
#   python -m PyInstaller --noconfirm packaging/dj-toolkit.spec
# Windows: dist/DJ Toolkit/DJ Toolkit.exe (the release zips that folder). macOS: dist/DJ Toolkit.app.
# Then run the app with --self-test: it exits 0 only if assets, tempo analysis, MP3 export and Qt all work.
import shutil
import sys
from pathlib import Path

import imageio_ffmpeg
from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))
from djtoolkit import __version__  # noqa: E402
from tools import make_notices  # noqa: E402

# What this download holds, licence by licence (tools/make_notices.py). It stops the build if a package asks for a
# notice it doesn't have yet, so a release can't go out without one.
notices = make_notices.write(ROOT / "build" / "THIRD-PARTY-LICENSES.txt")

datas = [(str(ROOT / "assets"), "assets"), (str(notices), ".")]
datas += collect_data_files("librosa")  # librosa reads its .pyi stubs at run time to find its functions
binaries = [(imageio_ffmpeg.get_ffmpeg_exe(), "imageio_ffmpeg/binaries")]  # MP3 export; as a binary it stays runnable

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PIL", "PySide6.QtWebEngineCore", "PySide6.QtQuick"],
)
pyz = PYZ(a.pure)
icon = str(ROOT / "packaging" / "icon.png")  # PyInstaller turns it into .ico or .icns (with Pillow)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DJ Toolkit",
    console=False,
    icon=icon,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DJ Toolkit", upx=False)
shutil.copy2(notices, Path(DISTPATH) / "DJ Toolkit" / "THIRD-PARTY-LICENSES.txt")  # beside the program: where you look

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="DJ Toolkit.app",
        icon=icon,
        bundle_identifier="io.github.tomgreef.djtoolkit",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": "DJ Toolkit",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
