from app.agents import brand
from app.config import settings


def test_logo_src_resolves_to_the_real_asset():
    assert brand.LOGO_SRC == "design/logo.png"
    assert (settings.REVIDEO_PROJECT_DIR / "public" / brand.LOGO_SRC).exists()


def test_brand_colors_are_hex_strings():
    for color in (brand.BACKGROUND_COLOR, brand.ACCENT_COLOR, brand.TEXT_COLOR, brand.ON_ACCENT_COLOR):
        assert isinstance(color, str)
        assert color.startswith("#")
