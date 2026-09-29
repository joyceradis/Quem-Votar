from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRAWER_PAGES = [
    "index.html",
    "candidatos.html",
    "candidato.html",
    "temas.html",
    "comparar.html",
    "sobre.html",
]


LIGHT_SURFACES = (
    "#ffffff", "#f5fbff", "#eef9ff", "#eaf7ff", "#eff9ff", "#fff0f7", "#fff5fa", "#f7fbfe", "#f9fcfe",
)


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
    app = (ROOT / "src" / "js" / "core" / "a11y.js").read_text(encoding="utf-8")
    assert 'drawer.removeAttribute("inert")' in app
    assert 'drawer.setAttribute("inert", "")' in app
    assert 'closeButton?.focus()' in app
    assert 'if (wasOpen) menuButton?.focus()' in app


def test_muted_text_token_meets_wcag_aa_on_light_brand_surfaces():
    css = (ROOT / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    match = re.search(r"--muted:\s*(#[0-9a-fA-F]{6});", css)
    assert match, "CSS --muted token not found"
    muted = match.group(1)

    for background in LIGHT_SURFACES:
        assert _contrast_ratio(muted, background) >= 4.5, (muted, background)


def test_text_accent_tokens_meet_wcag_aa_on_light_brand_surfaces():
    # Links, rótulos e "Entender" usam estes tokens em texto pequeno sobre
    # fundos claros (inclusive os tingidos): AA (4,5:1) em todos, não só no branco.
    css = (ROOT / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    for token in ("blue-strong", "pink-strong", "ink-soft"):
        match = re.search(rf"--{token}:\s*(#[0-9a-fA-F]{{6}});", css)
        assert match, f"CSS --{token} token not found"
        for background in LIGHT_SURFACES:
            assert _contrast_ratio(match.group(1), background) >= 4.5, (token, match.group(1), background)


def test_published_tokens_match_source_tokens():
    # A raiz publicada é a saída do build: não pode divergir do token de origem.
    source = (ROOT / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    published = (ROOT / "styles" / "tokens.css").read_text(encoding="utf-8")
    assert source == published


class AccessibilityContractTests(unittest.TestCase):
    """Torna as verificações acima descobríveis pelo `unittest discover` do CI
    (o repositório não usa pytest; funções soltas nunca eram executadas)."""

    def test_closed_drawer_is_removed_from_keyboard_navigation(self):
        test_closed_drawer_is_removed_from_keyboard_navigation()

    def test_navigation_manages_inert_state_and_returns_focus(self):
        test_navigation_manages_inert_state_and_returns_focus()

    def test_muted_text_token_meets_wcag_aa(self):
        test_muted_text_token_meets_wcag_aa_on_light_brand_surfaces()

    def test_text_accent_tokens_meet_wcag_aa(self):
        test_text_accent_tokens_meet_wcag_aa_on_light_brand_surfaces()

    def test_published_tokens_match_source(self):
        test_published_tokens_match_source_tokens()
