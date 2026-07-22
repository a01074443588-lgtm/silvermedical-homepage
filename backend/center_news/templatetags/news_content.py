import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()
STRONG_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def _inline_markup(value):
    escaped = escape(value)
    return STRONG_PATTERN.sub(r"<strong>\1</strong>", escaped)


@register.filter
def render_news_body(value):
    """Render the small, escaped formatting subset used by imported posts."""
    blocks = []
    list_items = []

    def flush_list():
        if not list_items:
            return
        blocks.append("<ul>" + "".join(f"<li>{_inline_markup(item)}</li>" for item in list_items) + "</ul>")
        list_items.clear()

    for raw_block in re.split(r"\n\s*\n", value or ""):
        line = raw_block.strip()
        if not line:
            continue
        if line.startswith("• "):
            list_items.append(line[2:].strip())
            continue

        flush_list()
        if line.startswith("## "):
            blocks.append(f"<h2>{_inline_markup(line[3:].strip())}</h2>")
        elif line.startswith("> "):
            blocks.append(f"<blockquote>{_inline_markup(line[2:].strip())}</blockquote>")
        else:
            blocks.append(f"<p>{_inline_markup(line).replace(chr(10), '<br>')}</p>")

    flush_list()
    return mark_safe("".join(blocks))
