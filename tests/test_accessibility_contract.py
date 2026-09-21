from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DRAWER_PAGES = [
    "index.html",
    "candidatos.html",
    "candidato.html",
    "temas.html",
    "comparar.html",
    "sobre.html",
]


def _relative_luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(channel) for channel in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(foreground: str, background: str) -> float:
    a = _relative_luminance(foreground)
    b = _relative_luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def test_closed_drawer_is_removed_from_keyboard_navigation():
    for page in DRAWER_PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        assert 'aria-controls="drawer"' in html
        assert '<aside class="drawer" id="drawer" aria-hidden="true" inert>' in html


def test_navigation_manages_inert_state_and_returns_focus():
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    assert 'drawer.removeAttribute("inert")' in app
    assert 'drawer.setAttribute("inert","")' in app
    assert 'closeButton?.focus()' in app
    assert 'if(wasOpen)menuButton?.focus()' in app


def test_muted_text_token_meets_wcag_aa_on_light_brand_surfaces():
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    match = re.search(r"--muted:(#[0-9a-fA-F]{6});", css)
    assert match, "CSS --muted token not found"
    muted = match.group(1)

    for background in ("#ffffff", "#f5fbff", "#eef9ff", "#fff0f7", "#fff5fa", "#f7fbfe"):
        assert _contrast_ratio(muted, background) >= 4.5, (muted, background)
