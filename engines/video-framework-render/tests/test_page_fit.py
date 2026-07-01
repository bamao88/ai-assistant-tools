from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from video_framework_render import render  # noqa: E402


def _rule(css: str, selector: str) -> str:
    m = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", css)
    assert m, f"missing CSS rule for {selector}"
    return m.group(1)


def test_vertical_ppt_content_box_fits_without_clipping():
    rule = _rule(render.PAGE_CSS, ".ppt")

    assert "height:640px" in rule
    assert "overflow:visible" in rule
    assert "overflow:hidden" not in rule


def test_deprecated_vertical_ppt_template_also_fits_without_clipping():
    rule = _rule(render.PAGE_CSS_PPT, ".ppt")

    assert "height:580px" in rule
    assert "overflow:visible" in rule
    assert "overflow:hidden" not in rule


def test_render_page_records_fit_scale_for_dense_pages():
    js = (ROOT / "video_framework_render" / "render_page.js").read_text(encoding="utf-8")

    assert "overflow:visible" in js
    assert "data-fit-scale" not in js  # JS uses dataset.fitScale, not literal HTML.
    assert "dataset.fitScale" in js
    assert "Math.min(availH / needH, availW / needW, 1)" in js


def test_page_text_preserves_br_without_rendering_raw_html():
    html = render.page_html_vertical(
        {
            "title": "T",
            "blocks": [
                {"type": "hero", "text": "第一行<br>第二行"},
                {"type": "mid", "text": "A<script>B</script>"},
            ],
        }
    )

    assert "第一行<br>第二行" in html
    assert "&lt;br&gt;" not in html
    assert "&lt;script&gt;" in html
    assert "<script>B</script>" not in html
