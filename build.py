#!/usr/bin/env python3
"""Builds index.html from recipe markdown frontmatter. No dependencies."""

import os
import re
import html as html_mod
from pathlib import Path

ROOT = Path(__file__).parent
RECIPES_DIR = ROOT / "recipes"
TEMPLATE = ROOT / "template.html"
OUTPUT = ROOT / "index.html"

TAG_ORDER = ["Healthy", "Everyday", "Special Occasions"]

CATEGORY_CSS = {
    "Healthy": "healthy",
    "Everyday": "everyday",
    "Special Occasions": "special",
}


def parse_frontmatter(text):
    m = re.match(r"^---\r?\n([\s\S]*?)\r?\n---", text)
    if not m:
        return {}
    data = {}
    for line in m.group(1).split("\n"):
        kv = re.match(r"^(\w[\w_]*):\s*(.*)", line)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            val = [s.strip().strip("\"'") for s in val[1:-1].split(",") if s.strip()]
        elif val == "true":
            val = True
        elif val == "false":
            val = False
        else:
            val = val.strip("\"'")
        data[key] = val
    return data


def esc(s):
    return html_mod.escape(s, quote=True)


def first_tag(tags):
    if isinstance(tags, list):
        for t in tags:
            if t in TAG_ORDER:
                return t
        return ""
    return tags if tags in TAG_ORDER else ""


def tag_index(tag):
    try:
        return TAG_ORDER.index(tag)
    except ValueError:
        return len(TAG_ORDER)


def slug(filename):
    return filename.replace(".md", "")


def format_time(prep, cook):
    parts = []
    if prep:
        parts.append(f"Prep {prep}")
    if cook:
        parts.append(f"Cook {cook}")
    return " · ".join(parts)


def card_meta_html(r):
    bits = []
    time_str = format_time(r.get("prep_time", ""), r.get("cook_time", ""))
    if time_str:
        bits.append(f'<span class="card-time">{esc(time_str)}</span>')
    srv = r.get("servings", "")
    if srv:
        bits.append(f'<span class="card-servings">{esc(str(srv))} servings</span>')
    if not bits:
        return ""
    return '<div class="card-meta">' + "".join(bits) + "</div>"


def category_pill(tag):
    if not tag:
        return ""
    css = CATEGORY_CSS.get(tag, "other")
    return f'<span class="card-category card-category--{css}">{esc(tag)}</span>'


# --- Read all recipe files ---

files = sorted(f for f in os.listdir(RECIPES_DIR) if f.endswith(".md") and not f.startswith("_"))

recipes = []
for f in files:
    text = (RECIPES_DIR / f).read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    meta["file"] = f
    recipes.append(meta)

# --- Separate grouped and standalone ---

group_map = {}
standalone = []

for r in recipes:
    if r.get("group"):
        gname = r["group"]
        if gname not in group_map:
            group_map[gname] = {"name": gname, "tag": first_tag(r.get("tags")), "variants": []}
        group_map[gname]["variants"].append(r)
        if not group_map[gname]["tag"] and r.get("tags"):
            group_map[gname]["tag"] = first_tag(r["tags"])
    else:
        standalone.append(r)

for g in group_map.values():
    g["variants"].sort(key=lambda v: int(v.get("group_order", 99)))

# --- Build card HTML ---

entries = []

for r in standalone:
    tag = first_tag(r.get("tags"))
    title = r.get("title") or r["file"].replace(".md", "")
    pill = category_pill(tag)
    meta = card_meta_html(r)
    sl = slug(r["file"])

    if r.get("plain"):
        inner = f'{pill}<h3 class="card-title">{esc(title)}</h3>{meta}'
        li = f'<li class="recipe-card recipe-card--plain" data-name="{esc(title)}" data-tags="{esc(tag)}" data-slug="{esc(sl)}"><div class="card-inner">{inner}</div></li>'
    else:
        inner = f'{pill}<h3 class="card-title">{esc(title)}</h3>{meta}'
        li = f'<li class="recipe-card" data-name="{esc(title)}" data-tags="{esc(tag)}" data-slug="{esc(sl)}"><a href="recipes/{r["file"]}" class="card-inner">{inner}</a></li>'
    entries.append({"tag": tag, "sort_key": title.lower(), "html": li})

for g in group_map.values():
    tag = g["tag"] or ""
    pill = category_pill(tag)
    search_parts = [g["name"]] + [v.get("variant_label") or v.get("title", "") for v in g["variants"]]
    search_name = " ".join(search_parts)
    first_slug = slug(g["variants"][0]["file"]) if g["variants"] else ""

    variant_links = []
    for v in g["variants"]:
        label = v.get("variant_label") or v.get("title") or v["file"]
        if v.get("plain"):
            variant_links.append(f'<span class="variant-plain">{esc(label)}</span>')
        else:
            variant_links.append(f'<a href="recipes/{v["file"]}">{esc(label)}</a>')
    variants_html = '<div class="card-variants">' + '<span class="variant-sep">/</span>'.join(variant_links) + "</div>"

    inner = f'{pill}<h3 class="card-title">{esc(g["name"])}</h3>{variants_html}'
    li = f'<li class="recipe-card recipe-card--group" data-name="{esc(search_name)}" data-tags="{esc(tag)}" data-slug="{esc(first_slug)}"><div class="card-inner">{inner}</div></li>'
    entries.append({"tag": tag, "sort_key": g["name"].lower(), "html": li})

# --- Sort ---

entries.sort(key=lambda e: (tag_index(e["tag"]), e["sort_key"]))

# --- Generate ---

list_html = "\n".join("    " + e["html"] for e in entries)
template = TEMPLATE.read_text(encoding="utf-8")
output = template.replace("{{RECIPE_LIST}}", list_html)
OUTPUT.write_text(output, encoding="utf-8")
print(f"Built index.html with {len(entries)} entries ({len(recipes)} recipe files)")
