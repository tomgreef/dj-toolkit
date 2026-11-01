"""Write the licence notices that go inside every download of DJ Toolkit (docs/releasing.md, "Licences").

`packaging/dj-toolkit.spec` runs this while it builds, with the Python the build uses, so each download carries a notice
for exactly what it was built from:

    python tools/make_notices.py THIRD-PARTY-LICENSES.txt

It starts from the same list of libraries as tools/make_sbom.py (what `pip inspect` reports for the packages
`requirements.txt` names, and what those need in turn), adds what no package says by itself (Qt, the ffmpeg program with
its own build configuration, the libraries inside two wheels, the PyInstaller bootloader), copies each package's own
licence files, and ends with the full text of the copyleft licences from packaging/licenses/. Standard library only, no
network.

It stops, so a release can't go out, if a package in the build states a copyleft licence that this file has no notice
for: add the notice first. `build_notices` is a pure function of what it is given, so tests/test_make_notices.py needs
no pip and no build.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import make_sbom  # noqa: E402  (the same list of libraries as the SBOM)

LICENSES = ROOT / "packaging" / "licenses"
REPO = "https://github.com/tomgreef/dj-toolkit"
TEXTS = ("GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "MPL-2.0", "Python-2.0")  # packaging/licenses/<name>.txt

# "GPL-2.0-or-later", "LGPLv3+", "GNU General Public License v3", "MPL-2.0": the letters of a licence's name, not the
# middle of a word (SIMPLE, TEMPLATE), and with no word break needed after them ("GPLv3").
COPYLEFT = re.compile(
    r"(?<![A-Za-z])(A?L?GPL|MPL|EPL|CDDL|EUPL)|general public licen[cs]e|mozilla public licen[cs]e|eclipse public licen[cs]e",
    re.I,
)
# Packages whose copyleft licence has a notice below: the Qt for Python family, and these three.
COVERED = {"mutagen", "soxr", "certifi"}
COVERED_PREFIXES = ("pyside6", "shiboken6")
LICENCE_FILE = re.compile(r"(licen[sc]e|copying|notice|unlicense)", re.I)
MAX_LICENCE_FILE = 300_000  # bytes: a licence is not a megabyte


def _covered(key: str) -> bool:
    return key in COVERED or key.startswith(COVERED_PREFIXES)


def _stated_licence(metadata: Mapping) -> str:
    """What the package says its licence is: an SPDX expression, a short name, or a licence classifier."""
    if metadata.get("license_expression"):
        return str(metadata["license_expression"])
    name = (metadata.get("license") or "").strip()
    if name and "\n" not in name and len(name) <= 100:
        return name
    classified = [c.rsplit("::", 1)[-1].strip() for c in metadata.get("classifier") or [] if c.startswith("License ::")]
    return ", ".join(classified) or "(not stated in its metadata: see its licence files below)"


def _source(metadata: Mapping) -> str:
    """A page where the package's source is: its own source link if it names one, else its home page, else PyPI."""
    urls = {}
    for entry in metadata.get("project_url") or []:
        label, _, url = entry.partition(",")
        urls[label.strip().lower()] = url.strip()
    for label in ("source", "source code", "repository", "code", "github", "homepage", "home"):
        if urls.get(label):
            return urls[label]
    return metadata.get("home_page") or f"https://pypi.org/project/{metadata['name']}/{metadata['version']}/"


def read_licence_files(location: Path) -> dict[str, str]:
    """The licence files an installed package carries (its `.dist-info` folder), by their path inside it."""
    found: dict[str, str] = {}
    for path in sorted(location.rglob("*")):
        relative = path.relative_to(location)
        if not path.is_file() or path.stat().st_size > MAX_LICENCE_FILE:
            continue
        if LICENCE_FILE.search(path.name) or "licenses" in relative.parts:
            found[relative.as_posix()] = path.read_text("utf-8", errors="replace").strip()
    return found


def _heading(title: str, mark: str = "-") -> str:
    return f"{title}\n{mark * len(title)}\n"


def ffmpeg_licence(configuration: str) -> tuple[str, str]:
    """(the licence, the text to read) that an ffmpeg build's own configuration line puts it under. A build with
    `--enable-nonfree` can't be passed on at all, so it stops the notice."""
    flags = set(configuration.split())
    if "--enable-nonfree" in flags:
        raise ValueError("This ffmpeg is built with --enable-nonfree, which can't be redistributed. Use another build.")
    version3 = "--enable-version3" in flags
    if "--enable-gpl" in flags:
        return (
            f"GNU General Public License, version {'3' if version3 else '2'} or later (this build is configured "
            "with --enable-gpl)",
            "GPL-3.0" if version3 else "GPL-2.0",
        )
    return (
        f"GNU Lesser General Public License, version {'3' if version3 else '2.1'} or later (this build is configured "
        "without --enable-gpl)",
        "LGPL-3.0" if version3 else "LGPL-2.1",
    )


def build_notices(
    packages: Mapping[str, Mapping],
    licence_files: Mapping[str, Mapping[str, str]],
    texts: Mapping[str, str],
    *,
    app_version: str,
    python: str,
    python_copyright: str,
    qt: str,
    ffmpeg_version: str,
    ffmpeg_configuration: str,
) -> str:
    """The notice, as text. `packages` is `make_sbom.needed_packages`; `licence_files` has each package's own licence
    files by comparable name; `texts` has the copyleft licences by name (`TEXTS`)."""
    uncovered = sorted(
        metadata["name"]
        for key, metadata in packages.items()
        if COPYLEFT.search(_stated_licence(metadata)) and not _covered(key)
    )
    if uncovered:
        raise ValueError(
            f"{', '.join(uncovered)} state a copyleft licence that tools/make_notices.py has no notice for. "
            "Add one to the copyleft section, and to COVERED, in the change that adds the package."
        )
    missing = [name for name in TEXTS if not texts.get(name)]
    if missing:
        raise ValueError(f"packaging/licenses is missing {', '.join(missing)}.")

    def version(key: str) -> str:
        return packages[key]["version"] if key in packages else "?"

    out = [
        _heading(f"DJ Toolkit {app_version}: licences of what is inside this download", "="),
        f"DJ Toolkit's own source code is under the MIT licence ({REPO}/blob/main/LICENSE).\n"
        "This download also contains software written by other people, each part under its own licence. The parts that "
        "need a notice of their own come first, then every Python package in the build, then the licence files those "
        "packages carry, then the full text of the GNU, Mozilla and Python licences.\n\n"
        "WHERE THE SOURCE CODE IS. DJ Toolkit's complete source code is this repository at the tag of the release "
        f"(for this download, v{app_version}): {REPO}. The source of each part named below is at the link next to it. "
        f"If you can't find the source of anything in this download, ask in an issue ({REPO}/issues) and we will "
        "provide it.\n\n"
        "This notice was written by the project's maintainers and has not been reviewed by a lawyer.\n",
        _heading("1. Parts that need a notice of their own"),
    ]
    entries = []
    if "mutagen" in packages:
        entries.append(
            f"mutagen {version('mutagen')}: GNU General Public License, version 2 or later (GPL-2.0-or-later).\n"
            "  DJ Toolkit imports it to read the tags of your music files and to write the BPM tag into exported ones.\n"
            f"  Source: https://pypi.org/project/mutagen/{version('mutagen')}/#files and https://github.com/quodlibet/mutagen\n"
            "  Licence text: GPL-2.0, below."
        )
    ffmpeg_terms, ffmpeg_text = ffmpeg_licence(ffmpeg_configuration)
    # "7.1" and "7.1-essentials_build-www.gyan.dev" are both release 7.1; "N-12345-gabc" (a git build) isn't a release
    release = re.match(r"\d+(\.\d+)+(?![\w.])|\d+(\.\d+)+(?=-)", ffmpeg_version.strip())
    ffmpeg_source = (
        f"https://ffmpeg.org/releases/ffmpeg-{release.group(0)}.tar.xz"
        if release
        else "https://ffmpeg.org/download.html#get-sources"
    )
    entries.append(
        f"ffmpeg {ffmpeg_version}: {ffmpeg_terms}.\n"
        "  A separate program that DJ Toolkit runs to make MP3 files (the imageio-ffmpeg package carries it). It has "
        "other libraries built into it,\n"
        "  each under its own licence: the configuration line below names them. Its own account of how it was built:\n"
        f"    {ffmpeg_configuration or '(this ffmpeg did not print its configuration)'}\n"
        f"  Source: {ffmpeg_source}, and each library the configuration line names, from its own project.\n"
        f"  Licence text: {ffmpeg_text}, below. Its libraries have theirs in their own projects."
    )
    entries.append(
        f"Qt {qt}, with PySide6 {version('pyside6')}: GNU Lesser General Public License, version 3 (LGPL-3.0). "
        "PySide6 offers it as one of three choices; this is the one used here.\n"
        "  The Qt libraries are separate files in this download, so you can replace them with your own build of the "
        "same version.\n"
        "  Source: https://code.qt.io/cgit/pyside/pyside-setup.git (Qt for Python) and https://download.qt.io/"
        "official_releases/qt/ (Qt).\n"
        "  Licence texts: LGPL-3.0 and GPL-3.0, below."
    )
    entries.append(
        "The FFmpeg libraries inside Qt Multimedia (libavcodec, libavformat, libavutil, libswresample, libswscale): "
        "LGPL-2.1-or-later (Qt ships them as an LGPL build).\n"
        "  A different copy of FFmpeg from the program above: Qt Multimedia plays audio with it. Separate library files "
        "in this download, which you can replace with your own build.\n"
        "  Source: https://ffmpeg.org/download.html#get-sources (the version is in the library file names, such as "
        "libavcodec.63).\n"
        "  Licence text: LGPL-2.1, below."
    )
    entries.append(
        "libsndfile, inside the soundfile package: GNU Lesser General Public License, version 2.1 or later "
        "(LGPL-2.1-or-later), with the codec libraries it carries.\n"
        "  A separate library file in this download, which you can replace with your own build.\n"
        "  Source: https://github.com/libsndfile/libsndfile and https://github.com/bastibe/python-soundfile\n"
        "  Licence text: LGPL-2.1, below."
    )
    if "soxr" in packages:
        entries.append(
            f"soxr {version('soxr')} (libsoxr, the sample-rate converter, built into it): LGPL-2.1-or-later.\n"
            "  A separate library file in this download, which you can replace with your own build.\n"
            "  Source: https://github.com/dofuuz/python-soxr and https://sourceforge.net/projects/soxr/\n"
            "  Licence text: LGPL-2.1, below."
        )
    if "certifi" in packages:
        entries.append(
            f"certifi {version('certifi')}: Mozilla Public License 2.0 (MPL-2.0).\n"
            "  It carries Mozilla's list of trusted certificate authorities, unchanged.\n"
            "  Source: https://github.com/certifi/python-certifi\n"
            "  Licence text: MPL-2.0, below."
        )
    entries.append(
        f"Python {python}: the Python Software Foundation licence (PSF-2.0). Its own notice:\n"
        + "\n".join(f"    {line}" for line in python_copyright.strip().splitlines()[:2])
        + "\n  The Python the program runs on is inside it, with the libraries Python itself is built with (OpenSSL, "
        "zlib, SQLite and others), each under its own licence:\n"
        "  https://docs.python.org/3/license.html lists them.\n"
        "  Source: https://www.python.org/downloads/source/\n"
        "  Licence text: Python-2.0, below."
    )
    entries.append(
        "PyInstaller (the tool that built this download; its bootloader is inside the program): GNU General Public "
        "License, version 2 or later,\n"
        "  with an exception that lets the programs it builds be distributed under other licences.\n"
        "  Source: https://github.com/pyinstaller/pyinstaller"
    )
    out.append("\n\n".join(entries) + "\n")

    out.append(_heading("\n2. Every Python package installed with this build"))
    out.append(
        "This list comes from what the build installed. Not every part of every package ends up in the download (the "
        "build leaves out, for example, Qt WebEngine and Qt Quick), so it can list more than the download holds.\n"
    )
    for key in sorted(packages):
        metadata = packages[key]
        out.append(
            f"{metadata['name']} {metadata['version']}: {_stated_licence(metadata)}\n  Source: {_source(metadata)}"
        )

    out.append("\n" + _heading("3. The licence files those packages carry"))
    for key in sorted(packages):
        for filename, text in sorted(licence_files.get(key, {}).items()):
            out.append(
                f"{'~' * 78}\n{packages[key]['name']} {packages[key]['version']}: {filename}\n{'~' * 78}\n{text}\n"
            )

    out.append("\n" + _heading("4. The full text of the GNU, Mozilla and Python licences"))
    for name in TEXTS:
        out.append(f"{'=' * 78}\n{name}\n{'=' * 78}\n{texts[name].strip()}\n")
    return "\n".join(out).rstrip() + "\n"


def write(output: Path) -> Path:
    """Build the notice for the packages installed in this Python, and write it."""
    sys.path.insert(0, str(ROOT))
    import imageio_ffmpeg
    from PySide6 import QtCore

    from djtoolkit import __version__

    # pip prints each package's own text, so on Windows it must write UTF-8 into the pipe, not cp1252
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "inspect"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=True,
    )
    inspected = json.loads(pip.stdout)
    packages = make_sbom.needed_packages(inspected, (ROOT / "requirements.txt").read_text("utf8"))
    locations = {
        make_sbom._key(item["metadata"]["name"]): item.get("metadata_location") for item in inspected["installed"]
    }
    licence_files = {key: read_licence_files(Path(locations[key])) for key in packages if locations.get(key)}

    report = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-version"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=True,
    ).stdout
    configuration = next((ln.split(":", 1)[1].strip() for ln in report.splitlines() if "configuration:" in ln), "")

    notices = build_notices(
        packages,
        licence_files,
        {name: (LICENSES / f"{name}.txt").read_text("utf-8") for name in TEXTS},
        app_version=__version__,
        python=platform.python_version(),
        python_copyright=sys.copyright,
        qt=QtCore.qVersion(),
        ffmpeg_version=imageio_ffmpeg.get_ffmpeg_version(),
        ffmpeg_configuration=configuration,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(notices, encoding="utf-8", newline="\n")
    return output


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python tools/make_notices.py OUTPUT.txt", file=sys.stderr)
        return 2
    path = write(Path(argv[0]))
    print(f"Wrote {path}: {path.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
