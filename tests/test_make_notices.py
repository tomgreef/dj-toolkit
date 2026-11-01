"""The licence notice inside every download (tools/make_notices.py, run by packaging/dj-toolkit.spec). It is built from
what `pip inspect` reports, so these hand it made-up packages: no pip, no build, nothing installed."""

from pathlib import Path

import pytest

from tools import make_notices, make_sbom

ROOT = Path(__file__).resolve().parents[1]
TEXTS = {name: f"The full text of {name}." for name in make_notices.TEXTS}
GPL_BUILD = "--prefix=/x --enable-gpl --enable-libx264 --enable-libmp3lame"


def package(name, version="1.0", **metadata):
    return {"name": name, "version": version, **metadata}


def notice(*packages, files=None, texts=TEXTS, ffmpeg="7.1", configuration=GPL_BUILD):
    return make_notices.build_notices(
        {make_sbom._key(p["name"]): p for p in packages},
        files or {},
        texts,
        app_version="0.2.0",
        python="3.12.1",
        python_copyright="Copyright (c) 2001-2026 Python Software Foundation.\nAll Rights Reserved.\n\nMore text.",
        qt="6.12.0",
        ffmpeg_version=ffmpeg,
        ffmpeg_configuration=configuration,
    )


def test_every_package_is_listed_with_its_licence_and_where_its_source_is():
    text = notice(
        package("alpha", "2.1", license_expression="MIT", project_url=["Source, https://example.org/alpha"]),
        package("beta", license="BSD-3-Clause", home_page="https://example.org/beta"),
        package("gamma", "3.0"),
    )
    assert "alpha 2.1: MIT\n  Source: https://example.org/alpha" in text
    assert "beta 1.0: BSD-3-Clause\n  Source: https://example.org/beta" in text
    assert "gamma 3.0: (not stated in its metadata: see its licence files below)" in text
    assert "https://pypi.org/project/gamma/3.0/" in text  # a package that names no source gets its PyPI page


def test_a_licence_classifier_names_the_licence_when_the_metadata_has_no_licence_field():
    classifiers = ["Programming Language :: Python", "License :: OSI Approved :: ISC License"]
    assert "delta 1.0: ISC License" in notice(package("delta", classifier=classifiers))


def test_each_packages_own_licence_files_are_copied_whole():
    text = notice(package("alpha"), files={"alpha": {"licenses/LICENSE": "Copyright (c) Alpha authors.\nMIT text."}})
    assert "alpha 1.0: licenses/LICENSE" in text
    assert "Copyright (c) Alpha authors.\nMIT text." in text


def test_the_parts_that_ask_for_more_than_a_notice_come_first_with_where_their_source_is():
    text = notice(
        package("mutagen", "1.48.1", license_expression="GPL-2.0-or-later"),
        package("PySide6", "6.12.0", license_expression="LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"),
        package("soxr", "1.1.0", license_expression="LGPL-2.1-or-later"),
        package("certifi", "2026.1", license_expression="MPL-2.0"),
    )
    first, rest = text.split("2. Every Python package")
    for must in (
        "mutagen 1.48.1",
        "https://github.com/quodlibet/mutagen",
        "Qt 6.12.0, with PySide6 6.12.0",
        "soxr 1.1.0",
        "certifi 2026.1",
        "libsndfile",
        "PyInstaller",
        "ffmpeg 7.1",
        "The FFmpeg libraries inside Qt Multimedia",
        "Python 3.12.1",
    ):
        assert must in first, must
    assert "WHERE THE SOURCE CODE IS" in first and "has not been reviewed by a lawyer" in first
    assert "mutagen 1.48.1: GPL-2.0-or-later" in rest  # and it is in the full list too


def test_python_is_named_with_its_own_copyright_notice_and_the_psf_text_travels_with_it():
    text = notice(package("alpha"))
    assert "Python 3.12.1: the Python Software Foundation licence (PSF-2.0)" in text
    assert "    Copyright (c) 2001-2026 Python Software Foundation.\n    All Rights Reserved.\n" in text
    assert "More text." not in text  # only the two lines of its notice, not the rest of sys.copyright
    assert "https://docs.python.org/3/license.html" in text
    assert text.rstrip().endswith("The full text of Python-2.0.")


def test_ffmpeg_is_described_by_its_own_configuration_line():
    gpl = notice(package("alpha"), configuration=GPL_BUILD)
    assert "ffmpeg 7.1: GNU General Public License, version 2 or later" in gpl
    assert GPL_BUILD in gpl and "Licence text: GPL-2.0" in gpl
    assert "ffmpeg-7.1.tar.xz" in gpl

    v3 = notice(package("alpha"), configuration="--enable-gpl --enable-version3")
    assert "version 3 or later" in v3 and "Licence text: GPL-3.0" in v3

    lgpl = notice(package("alpha"), configuration="--enable-libmp3lame")
    assert "Lesser General Public License, version 2.1 or later (this build is configured without --enable-gpl)" in lgpl

    named_build = notice(package("alpha"), ffmpeg="7.1-essentials_build-www.gyan.dev", configuration=GPL_BUILD)
    assert "ffmpeg 7.1-essentials_build-www.gyan.dev: GNU" in named_build  # the builder's name stays in the notice
    assert "https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz" in named_build  # and the release it is built from is linked

    git_build = notice(package("alpha"), ffmpeg="N-12345-gabcdef", configuration=GPL_BUILD)
    assert "ffmpeg-N-12345" not in git_build and "https://ffmpeg.org/download.html#get-sources" in git_build


def test_a_nonfree_ffmpeg_cannot_be_passed_on():
    with pytest.raises(ValueError, match="nonfree"):
        notice(package("alpha"), configuration="--enable-gpl --enable-nonfree")


@pytest.mark.parametrize(
    "licence",
    ["GPLv3", "LGPL-2.1+", "AGPL-3.0-only", "GNU General Public License v2", "MPL-1.1", "EPL-2.0", "CDDL-1.0"],
)
def test_a_new_copyleft_package_stops_the_notice_until_it_has_one(licence):
    with pytest.raises(ValueError, match="chardet.*no notice"):
        notice(package("chardet", license=licence))


@pytest.mark.parametrize("licence", ["MIT", "BSD-3-Clause", "Apache-2.0", "ISC", "SIMPLE", "Zlib AND CC0-1.0"])
def test_permissive_licences_do_not_stop_it(licence):
    assert "chardet 1.0" in notice(package("chardet", license=licence))


def test_the_qt_for_python_family_is_covered_by_the_qt_notice():
    qt = "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
    packages = [package(n, "6.12.0", license_expression=qt) for n in ("PySide6", "PySide6_Essentials", "shiboken6")]
    assert "Qt 6.12.0, with PySide6 6.12.0" in notice(*packages)


def test_the_full_texts_of_the_copyleft_licences_end_the_notice_in_order():
    text = notice(package("alpha"))
    positions = [text.index(f"\n{name}\n{'=' * 78}") for name in make_notices.TEXTS]
    assert positions == sorted(positions)
    assert make_notices.TEXTS[-1] == "Python-2.0" and "MPL-2.0" in make_notices.TEXTS
    with pytest.raises(ValueError, match="missing LGPL-3.0"):
        notice(package("alpha"), texts={k: v for k, v in TEXTS.items() if k != "LGPL-3.0"})


def test_the_same_build_gives_the_same_notice():
    args = (package("alpha", license="MIT"), package("beta", license="ISC"))
    assert notice(*args) == notice(*reversed(args))  # sorted, so the order a build lists them in doesn't matter


def test_licence_files_are_read_from_a_package_folder(tmp_path):
    folder = tmp_path / "alpha-1.0.dist-info"
    (folder / "licenses" / "vendor").mkdir(parents=True)
    (folder / "licenses" / "LICENSE").write_text("MIT text.\n", "utf-8")
    (folder / "licenses" / "vendor" / "COPYING-lib").write_text("Vendored.\n", "utf-8")
    (folder / "NOTICE.txt").write_text("A notice.\n", "utf-8")
    (folder / "METADATA").write_text("Name: alpha\n", "utf-8")
    (folder / "RECORD").write_text("alpha.py,,\n", "utf-8")
    (folder / "LICENSE-huge").write_text("x" * (make_notices.MAX_LICENCE_FILE + 1), "utf-8")
    found = make_notices.read_licence_files(folder)
    assert found == {
        "NOTICE.txt": "A notice.",
        "licenses/LICENSE": "MIT text.",
        "licenses/vendor/COPYING-lib": "Vendored.",
    }


def test_the_licence_texts_in_the_repository_are_the_real_ones():
    expected = {
        "GPL-2.0": ("GNU GENERAL PUBLIC LICENSE", "Version 2, June 1991"),
        "GPL-3.0": ("GNU GENERAL PUBLIC LICENSE", "Version 3, 29 June 2007"),
        "LGPL-2.1": ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 2.1, February 1999"),
        "LGPL-3.0": ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 3, 29 June 2007"),
        "MPL-2.0": ("Mozilla Public License Version 2.0", "1. Definitions"),
        "Python-2.0": (
            "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2",
            'This LICENSE AGREEMENT is between the Python Software Foundation ("PSF")',
        ),
    }
    assert set(expected) == set(make_notices.TEXTS)
    for name, (title, marker) in expected.items():
        text = (ROOT / "packaging" / "licenses" / f"{name}.txt").read_text("utf-8")
        assert text.lstrip().startswith(title) and marker in text and len(text) > 8_000, name  # whole, not a stub


def test_the_hashes_in_the_licence_texts_readme_are_the_files_hashes():
    import hashlib
    import re

    readme = (ROOT / "packaging" / "licenses" / "README.md").read_text("utf-8")
    listed = dict(re.findall(r"`([A-Za-z]+-[\d.]+\.txt)`\s*\|[^|]*\|[^|]*\|\s*`([0-9a-f]{64})`", readme))
    assert set(listed) == {f"{name}.txt" for name in make_notices.TEXTS}
    for filename, digest in listed.items():
        actual = hashlib.sha256((ROOT / "packaging" / "licenses" / filename).read_bytes()).hexdigest()
        assert actual == digest, f"{filename}: the README says {digest}, the file is {actual}"


def test_the_build_ships_the_notice_and_the_self_test_insists_on_it():
    """A download without its notice is the thing this exists to prevent: the build writes it, and the release's
    self-test fails if the built app doesn't hold it."""
    spec = (ROOT / "packaging" / "dj-toolkit.spec").read_text("utf-8")
    main = (ROOT / "main.py").read_text("utf-8")
    assert "make_notices" in spec and "THIRD-PARTY-LICENSES.txt" in spec
    assert "THIRD-PARTY-LICENSES.txt" in main and "GNU GENERAL PUBLIC LICENSE" in main
