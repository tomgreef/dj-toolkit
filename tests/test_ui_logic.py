"""Theme, icons, Spotify sync gating, tutorials and dialogs."""

from pathlib import Path
from unittest.mock import patch

import pytest

from djtoolkit import tutorials
from djtoolkit.ui import theme


def test_theme_switch(app):
    assert theme.apply(app, "light").name == "light" and theme.P.name == "light"
    assert theme.apply(app, "dark").name == "dark" and theme.P.name == "dark"
    assert theme.apply(app, "nonsense").name == "dark"


# ----------------------------------------------------------------- icons
def test_every_icon_renders(app):
    from djtoolkit.ui import icons

    for name in icons._PATHS:
        for color in (theme.DARK.text, theme.LIGHT.text):
            pm = icons.pixmap(name, color, 18)
            assert not pm.isNull()
            img = pm.toImage()
            assert any(
                img.pixelColor(x, y).alpha() > 0 for x in range(0, img.width(), 2) for y in range(0, img.height(), 2)
            ), name


# ------------------------------------------------------------ spotify gate
def test_sync_now_requires_a_preview(app):
    from djtoolkit.settings import Settings
    from djtoolkit.spotify import engine
    from djtoolkit.spotify.types import SyncPlan
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())
    assert not t.sync_btn.isEnabled() and t.preview_btn.isEnabled()  # safe by default

    summary = engine.SyncSummary(tracks=3, matched=3, plans=[SyncPlan("House", "Local: House", ["a"], ["b"], 1)])
    t._finished(summary, dry_run=True)
    assert t.sync_btn.isEnabled()  # a successful preview unlocks it
    assert t.table.rowCount() == 1 and t.table.item(0, 0).text() == "Local: House"

    t.thresh.setValue(0.9)  # any setting change makes the preview stale
    assert not t.sync_btn.isEnabled()

    t._finished(summary, dry_run=True)
    assert t.sync_btn.isEnabled()
    t._finished(summary, dry_run=False)  # after a real sync a fresh preview is needed again
    assert not t.sync_btn.isEnabled()


def test_incomplete_matching_does_not_unlock_sync(app):
    from djtoolkit.settings import Settings
    from djtoolkit.spotify import engine
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())
    t._finished(engine.SyncSummary(tracks=10, matched=4, deferred=6, incomplete=True), dry_run=True)
    assert not t.sync_btn.isEnabled()


def test_the_unmatched_report_opens_in_the_system_viewer(app, tmp_path, monkeypatch):
    """`os.startfile` exists only on Windows, so the report has to open the way every system opens a file."""
    from PySide6.QtGui import QDesktopServices

    from djtoolkit.settings import Settings
    from djtoolkit.spotify import engine
    from djtoolkit.ui.sync_tab import SyncTab

    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    report = tmp_path / "unmatched.csv"
    report.write_text("genre,artist\n", "utf8")

    t = SyncTab(Settings())
    t._open_report()  # nothing synced yet: nothing to open
    assert opened == []
    t.summary = engine.SyncSummary(report_path=report)
    t._open_report()
    assert [Path(p) for p in opened] == [report]


# ---------------------------------------------------------------- dialogs
def test_file_dialogs_reopen_where_you_left_off(app, tmp_path, monkeypatch):
    from djtoolkit.settings import Settings
    from djtoolkit.ui import dialogs

    seen = {}

    def fake(parent, title, start, flt):
        seen["start"] = start
        return str(tmp_path / "sets" / "vocal.wav"), ""

    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(fake))
    s = Settings()
    assert dialogs.pick_file(None, s, "acapella_dir", "Open", "*") == str(tmp_path / "sets" / "vocal.wav")
    assert s.acapella_dir == str(tmp_path / "sets")  # remembered, and saved to disk
    assert Settings.load().acapella_dir == str(tmp_path / "sets")

    dialogs.pick_file(None, s, "acapella_dir", "Open", "*")  # next time it starts there...
    assert Path(seen["start"]).name == "sets" or seen["start"] == str(tmp_path)  # ...or the nearest folder that exists


def test_dialog_start_falls_back_when_the_remembered_folder_is_gone(app, tmp_path, monkeypatch):
    from djtoolkit.settings import Settings
    from djtoolkit.ui import dialogs

    starts = []
    monkeypatch.setattr(
        dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda p, t, start, f: (starts.append(start), ("", ""))[1])
    )
    s = Settings()
    s.sample_dir = str(tmp_path / "deleted" / "samples")
    dialogs.pick_file(None, s, "sample_dir", "Sample", "*")
    assert starts == [str(tmp_path)]  # the closest parent that still exists, not an error
    s.sample_dir = r"Q:\no\such\drive"
    dialogs.pick_file(None, s, "sample_dir", "Sample", "*")
    assert Path(starts[-1]).is_dir()


def test_cancelling_a_dialog_changes_nothing(app, monkeypatch):
    from djtoolkit.settings import Settings
    from djtoolkit.ui import dialogs

    monkeypatch.setattr(dialogs.QFileDialog, "getOpenFileName", staticmethod(lambda *a: ("", "")))
    s = Settings()
    s.acapella_dir = "keep"
    assert dialogs.pick_file(None, s, "acapella_dir", "Open", "*") == "" and s.acapella_dir == "keep"


# -------------------------------------------------------------- tutorials
def test_tutorials_stay_simple():
    items = tutorials.load_tutorials()
    assert len({t.id for t in items}) == len(items) >= 3
    for t in items:
        assert len(t.recommendation) <= 100, t.id
        assert 2 <= len(t.steps) <= 4, t.id
        assert all(len(s) <= 80 for s in t.steps), t.id


def test_forum_roundtrip_and_anonymity(tmp_path):
    f = tutorials.LocalForum(tmp_path / "d.json")
    assert f.handle.startswith("Anonymous DJ #")
    p = f.add_post("folder-structure", "Challenge", "  Why two levels?  ")
    assert p.text == "Why two levels?" and p.author == f.handle
    f.add_post("rekordbox-to-usb", "Question", "exFAT ok?")
    again = tutorials.LocalForum(tmp_path / "d.json")  # persisted, same anonymous handle
    assert again.handle == f.handle
    assert [x.text for x in again.list_posts("folder-structure")] == ["Why two levels?"]
    assert len(again.list_posts("rekordbox-to-usb")) == 1


def test_forum_validation(tmp_path):
    f = tutorials.LocalForum(tmp_path / "d.json")
    with pytest.raises(ValueError):
        f.add_post("x", "Question", "   ")
    with pytest.raises(ValueError):
        f.add_post("x", "Rant", "hi")
    assert len(f.add_post("x", "Question", "a" * 2000).text) == tutorials.MAX_POST_CHARS


# ------------------------------------------------------ setup guide paths
def test_setup_guide_walks_through_every_outcome(app):
    """Covers the success and failure messages, which no other test reaches."""
    from djtoolkit.settings import Settings
    from djtoolkit.ui.setup_guide import STEPS, SetupGuide

    g = SetupGuide(Settings())
    for i in range(len(STEPS)):
        g.steps.setCurrentRow(i)  # every step renders (text, image, extras)
        assert g.heading.text() and g.counter.text() == f"Step {i + 1} of {len(STEPS)}"
    g._connected("Rio")
    assert "Spotify linked as Rio" in g.conn_status.text()
    g._connect_failed("state mismatch")
    assert "Couldn't link Spotify" in g.conn_status.text() and g.s.redirect_uri in g.conn_status.text()
    g.steps.setCurrentRow(4)
    g.client_edit.setText("short")
    g._next()  # a clearly wrong Client ID is explained, not submitted
    assert "doesn't look like a Client ID" in g.body.text() and not g.s.client_id


def test_the_guide_never_uses_jargon_a_dj_would_not_say():
    from djtoolkit.ui.setup_guide import STEPS

    text = " ".join(" ".join(s) for s in STEPS).lower()
    for word in ("pkce", "oauth", "token", "authorize", "api key"):
        assert word not in text, word


# ---------------------------------------------------------- window state
def test_the_window_reopens_where_you_left_off(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.main_window import MainWindow

    w = MainWindow()
    w.go(2)
    w.resize(1234, 777)
    w.close()
    s = Settings.load()
    assert s.last_page == 2 and s.window  # saved on close

    w2 = MainWindow()
    assert w2.stack.currentIndex() == 2 and w2._nav.button(2).isChecked()
    w2.close()


def test_a_bad_remembered_page_falls_back_to_the_first(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.main_window import MainWindow

    s = Settings()
    s.last_page = 99
    s.save()
    w = MainWindow()
    assert w.stack.currentIndex() == 0
    w.close()


def test_modes_are_named_for_where_they_are_used(app):
    from djtoolkit.ui.main_window import MODE_TIPS, MainWindow

    w = MainWindow()
    assert w.mode._buttons["dark"].text() == "Booth" and w.mode._buttons["light"].text() == "Daylight"
    assert "club" in MODE_TIPS["dark"] and "day" in MODE_TIPS["light"].lower()
    w.close()


def test_the_tutorial_you_read_last_is_reopened(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.tutorials_tab import TutorialsTab

    s = Settings()
    t = TutorialsTab(forum=tutorials.LocalForum(), settings=s)
    t.list.setCurrentRow(2)
    again = TutorialsTab(forum=tutorials.LocalForum(), settings=Settings.load())
    assert again.list.currentRow() == 2
    s2 = Settings()
    s2.last_tutorial = "no-longer-exists"
    assert TutorialsTab(forum=tutorials.LocalForum(), settings=s2).list.currentRow() == 0


# ------------------------------------------------------ accent + floating look
def test_the_accent_you_pick_is_applied_saved_and_restored(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.main_window import MainWindow

    w = MainWindow()
    assert w.settings.accent == "mono" == theme.DEFAULT_ACCENT and w.accents._buttons["mono"].isChecked()
    w.accents._buttons["rose"].click()  # what a click on the dot does
    assert theme.P.accent == "rose" and Settings.load().accent == "rose"
    w.close()

    w2 = MainWindow()  # next launch
    assert theme.P.accent == "rose" and w2.accents._buttons["rose"].isChecked()
    w2.set_theme("light")
    assert theme.P.name == "light" and theme.P.accent == "rose" and w2.mode._buttons["light"].isChecked()
    w2.close()


def test_an_unknown_saved_accent_falls_back_to_the_default(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.main_window import MainWindow

    s = Settings()
    s.accent = "chartreuse"
    s.save()
    w = MainWindow()
    assert theme.P.accent == theme.DEFAULT_ACCENT
    w.close()


def test_every_accent_has_a_visible_swatch_and_a_name(app):
    from djtoolkit.ui.widgets import AccentPicker

    picker = AccentPicker()
    assert set(picker._buttons) == set(theme.ACCENTS)
    for key, b in picker._buttons.items():
        assert b.toolTip() == f"{theme.ACCENTS[key]['label']} accent" and theme.ACCENTS[key]["swatch"] in b.styleSheet()


def test_floating_panels_paint_a_card_with_a_shadow_below_it(app):
    from djtoolkit.ui.widgets import Panel

    pan = Panel("Title")
    pan.resize(400, 200)
    l, t, r, b = Panel.BLEED
    for mode, accent in (("dark", "violet"), ("light", "rose"), ("light", "mono")):
        theme.apply(app, mode, accent)
        img = pan.grab().toImage()
        c = theme.P
        centre = img.pixelColor(img.width() // 2, img.height() // 2)
        assert (centre.red(), centre.green(), centre.blue()) == tuple(
            int(c.panel[i : i + 2], 16) for i in (1, 3, 5)
        )  # the card
        edge = img.pixelColor(img.width() // 2, img.height() - b - 3 + 6)  # just under the card's bottom edge
        assert edge.alpha() > 0  # the soft shadow is painted there, not left empty
    theme.apply(app, "dark", theme.DEFAULT_ACCENT)


def test_callback_port_updates_on_ok(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())
    assert t.s.callback_port == 8888

    with patch("djtoolkit.ui.sync_tab.QInputDialog.getInt", return_value=(9999, True)):
        t._set_callback_port()
        assert t.s.callback_port == 9999


def test_callback_port_unchanged_on_cancel(app):
    from djtoolkit.settings import Settings
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())

    with patch("djtoolkit.ui.sync_tab.QInputDialog.getInt", return_value=(8888, False)):
        t._set_callback_port()
        assert t.s.callback_port == 8888


def test_menu_has_opaque_background(app):
    from PySide6.QtWidgets import QMenu

    from djtoolkit.ui import theme

    menu = QMenu()

    for mode in ("dark", "light"):
        theme.apply(app, mode)
        bg_color = menu.palette().window().color()
        assert bg_color.alpha() == 255


def test_a_disabled_menu_entry_looks_disabled(app):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QMenu

    def ink(img, rect, bg):  # how far a row's pixels sit from the background: its text
        pixels = (
            img.pixelColor(x, y) for x in range(rect.left(), rect.right()) for y in range(rect.top(), rect.bottom())
        )
        return sum(abs(p.red() - bg.red()) + abs(p.green() - bg.green()) + abs(p.blue() - bg.blue()) for p in pixels)

    for mode in ("dark", "light"):
        theme.apply(app, mode)
        menu = QMenu()
        on, off = menu.addAction("Same words"), menu.addAction("Same words")
        off.setEnabled(False)
        img, bg = menu.grab().toImage(), QColor(theme.P.panel)
        loud, quiet = ink(img, menu.actionGeometry(on), bg), ink(img, menu.actionGeometry(off), bg)
        assert loud > quiet > 0  # the disabled entry is quieter than the others, and still legible
    theme.apply(app, "dark", theme.DEFAULT_ACCENT)


# ------------------------------------------- the Spotify page, by keyboard and screen reader
def _tab_stops(page):
    """What Tab stops on, in order: walk the page's focus chain once, from its first control."""
    from PySide6.QtCore import Qt

    stops, seen, w = [], set(), page.guide_btn
    while w is not None and id(w) not in seen:
        seen.add(id(w))
        if w.focusPolicy() & Qt.FocusPolicy.TabFocus and w.isVisibleTo(page) and w.isEnabled():
            stops.append(w)
        w = w.nextInFocusChain()
    return stops


def test_every_tab_stop_on_the_spotify_page_has_a_name_a_screen_reader_can_say(app):
    from PySide6.QtWidgets import QAbstractButton, QLabel

    from djtoolkit.settings import Settings
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())
    t.stack.setCurrentIndex(1)  # the preview table, which a preview puts on show
    labelled = {lab.buddy(): lab.text() for lab in t.findChildren(QLabel) if lab.buddy() is not None}
    nameless = []
    for w in _tab_stops(t):
        if w.objectName() == "qt_spinbox_lineedit":  # the editor inside a spin box: the box itself carries the name
            continue
        name = w.accessibleName() or (w.text() if isinstance(w, QAbstractButton) else "") or labelled.get(w, "")
        if not name.strip():
            nameless.append(type(w).__name__)
    assert not nameless, f"Tab stops a screen reader can't name: {nameless}"


def test_tab_goes_down_the_spotify_page_and_reaches_the_preview(app):
    from PySide6.QtWidgets import QPushButton

    from djtoolkit.settings import Settings
    from djtoolkit.ui.sync_tab import SyncTab

    t = SyncTab(Settings())
    t.stack.setCurrentIndex(1)
    stops = _tab_stops(t)
    browse = next(b for b in t.findChildren(QPushButton) if b.text().startswith("Browse"))
    i = stops.index(t.root_edit)
    assert stops[i + 1] is browse and stops[i + 2] is t.ignore_edit  # Browse follows the folder it browses for
    assert stops.index(t.preview_btn) < stops.index(t.table) < stops.index(t.log)  # the preview, then the activity log


def test_the_preview_table_shows_where_you_are_in_both_themes(app):
    """A keyboard user has to see the focus ring on the table and which playlist is current."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor

    from djtoolkit.settings import Settings
    from djtoolkit.spotify import engine
    from djtoolkit.spotify.types import SyncPlan
    from djtoolkit.ui.sync_tab import SyncTab

    plans = [SyncPlan(n, f"Local: {n}", ["a"], [], 3) for n in ("House", "Techno", "Disco")]
    for mode in ("dark", "light"):
        theme.apply(app, mode)
        t = SyncTab(Settings())
        t.resize(900, 700)
        t.show()
        t._finished(engine.SyncSummary(tracks=9, matched=9, plans=plans), dry_run=True)
        t.table.setFixedHeight(200)  # room for the rows, whatever the window's layout does
        t.table.setCurrentCell(1, 0)
        t.table.setFocus(Qt.FocusReason.TabFocusReason)
        app.processEvents()
        assert t.table.hasFocus() and t.table.currentRow() == 1
        view = t.table.viewport().grab().toImage()
        current_y = t.table.visualRect(t.table.model().index(1, 0)).center().y()
        above_y = t.table.visualRect(t.table.model().index(0, 0)).center().y()
        # the ring runs round the table, unbroken, even beside the selected row (the pixel is the border's, not the row's)
        beside_row = t.table.viewport().mapTo(t.table, QPoint(0, current_y)).y()
        assert t.table.grab().toImage().pixelColor(1, beside_row) == QColor(theme.P.link), mode
        # the current playlist is marked, in the margin before its text, and the one above it is not
        assert view.pixelColor(3, current_y) == QColor(theme.P.select), mode
        assert view.pixelColor(3, above_y) != QColor(theme.P.select), mode
        assert [i.row() for i in t.table.selectedIndexes()].count(1) == t.table.columnCount()  # the whole row
        t.close()
    theme.apply(app, "dark", theme.DEFAULT_ACCENT)
