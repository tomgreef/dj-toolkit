"""The website's colour tokens must stay in sync with the app's Mono palette.

Changing a colour in theme.py or in website/src/styles/global.css without the other
makes this test fail, naming the tokens that drifted.
"""

from __future__ import annotations

import re
from pathlib import Path

from djtoolkit.ui import theme

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "website" / "src" / "styles" / "global.css"

# Site token name -> Palette attribute (or a special string for stage/dark values)
# Mapping kept here as the issue requested.
LIGHT_MAP = {
    "--ground": "bg",
    "--ground-raised": "sidebar",  # also matches panel2
    "--surface": "panel",
    "--ink": "text",
    "--muted": "muted",
    "--line": "border",
    "--line-strong": "border_strong",
    "--primary": "primary",
    "--primary-hover": "primary_hover",
    "--on-primary": "on_primary",
    "--cue": "cue",
    "--selection": "sel_bg",
    "--stage": "stage",
    "--stage-raised": "stage_raised",
    "--stage-ink": "stage_text",
    "--stage-muted": "stage_muted",
    "--stage-data": "stage_data",
    "--stage-cue": "cue",  # dark cue value is used on stage
    "--on-cue": "on_cue",
}

DARK_MAP = {
    "--ground": "bg",
    "--ground-raised": "sidebar",
    "--surface": "panel",
    "--ink": "text",
    "--muted": "muted",
    "--line": "border",
    "--line-strong": "border_strong",
    "--primary": "primary",
    "--primary-hover": "primary_hover",
    "--on-primary": "on_primary",
    "--cue": "cue",
    "--selection": "sel_bg",
}


def _parse_block(css: str, start_marker: str, end_marker: str | None = None) -> dict[str, str]:
    """Extract --token: #hex; pairs from a CSS block starting after start_marker."""
    start = css.find(start_marker)
    if start == -1:
        return {}
    chunk = css[start:]
    if end_marker:
        end = chunk.find(end_marker)
        if end != -1:
            chunk = chunk[:end]
    tokens = {}
    for m in re.finditer(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8}|transparent)", chunk):
        tokens[m.group(1)] = m.group(2).lower()
    return tokens


def _expected(pal: theme.Palette, mapping: dict[str, str]) -> dict[str, str]:
    out = {}
    for site, role in mapping.items():
        if role == "cue" and site == "--stage-cue":
            # stage cue uses the dark amber
            out[site] = theme.palette("dark", "mono").cue.lower()
        else:
            val = getattr(pal, role, None)
            if isinstance(val, str):
                out[site] = val.lower()
    return out


def test_website_daylight_matches_app_mono_light():
    css = CSS_PATH.read_text(encoding="utf-8")
    site = _parse_block(css, ":root {", "@media")
    pal = theme.palette("light", "mono")
    expected = _expected(pal, LIGHT_MAP)
    mismatches = []
    for token, want in expected.items():
        got = site.get(token)
        if got != want:
            mismatches.append(f"{token}: site={got} app={want}")
    assert not mismatches, "Daylight tokens drifted:\n" + "\n".join(mismatches)


def test_website_booth_matches_app_mono_dark():
    css = CSS_PATH.read_text(encoding="utf-8")
    # Both the media query block and the [data-theme=dark] block should match
    media = _parse_block(css, ':root:not([data-theme="light"])', "}")
    explicit = _parse_block(css, ':root[data-theme="dark"]', "}")
    pal = theme.palette("dark", "mono")
    expected = _expected(pal, DARK_MAP)
    for label, site in (("media", media), ("data-theme", explicit)):
        mismatches = []
        for token, want in expected.items():
            got = site.get(token)
            if got != want:
                mismatches.append(f"{token}: site={got} app={want}")
        assert not mismatches, f"Booth ({label}) tokens drifted:\n" + "\n".join(mismatches)
