# Releasing

Pushing a version tag builds the downloads and publishes them as a GitHub Release.

```bat
git tag v0.1.0
git push origin v0.1.0
```

`.github/workflows/release.yml` then, on Windows and on macOS:

1. installs the app's dependencies and the build tools (`requirements-build.txt`);
2. builds the app with PyInstaller (`packaging/dj-toolkit.spec`);
3. runs the built app with `--self-test`, which fails the release if the assets, the tempo analysis, MP3 export
   (ffmpeg) or Qt don't work inside the bundle;
4. packs `DJ-Toolkit-Windows.zip` and `DJ-Toolkit-macOS.dmg` and attaches them to the release.

The file names never change, so `https://github.com/tomgreef/on-the-one/releases/latest/download/DJ-Toolkit-Windows.zip`
always points at the newest build. The website shows its download buttons only once a release has both files.
Bump `__version__` in `djtoolkit/__init__.py` and add the release to `CHANGELOG.md` before tagging.

## Build it yourself

```bat
.venv\Scripts\pip install -r requirements-build.txt
.venv\Scripts\python -m PyInstaller --noconfirm packaging/dj-toolkit.spec
"dist\DJ Toolkit\DJ Toolkit.exe" --self-test
```

On macOS the app is `dist/DJ Toolkit.app`. To try the release workflow without publishing anything, run it from the
Actions tab (*Run workflow*): it builds and uploads the files as artifacts only.

## Not done yet

- **Code signing.** The builds aren't signed, so Windows SmartScreen and macOS Gatekeeper warn on first open; the
  install steps say how to get past that. Signing needs a paid Windows certificate and an Apple Developer account.
- **Intel Macs.** The macOS build is for Apple silicon. An Intel build needs an Intel runner (or a universal build).
- **An installer for Windows.** The zip runs anywhere without admin rights; a setup program could add a Start menu
  entry and an uninstaller.
- **The app icon** is `packaging/icon.png`, drawn by `tools/make_icon.py` from the brand mark.
