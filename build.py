#!/usr/bin/env python3
"""Builds index.html from recipe markdown frontmatter. No dependencies."""

import os
import re
import html
from pathlib import Path
from locale import strxfrm

ROOT = Path(__file__).parent
RECIPES_DIR = ROOT / "recipes"
TEMPLATE = ROOT / "template.html"
OUTPUT = ROOT / "index.html"

TAG_ORDER = ["Healthy", "Recettes de tous les jours", "Recettes pour des occasions"]


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


def escape(s):
    return html.escape(s, quote=True)


def first_tag(tags):
    """Return the first tag that matches a known category, or empty string."""
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

# Sort variants within each group
for g in group_map.values():
    g["variants"].sort(key=lambda v: int(v.get("group_order", 99)))

# --- Build unified entry list ---

entries = []

for r in standalone:
    tag = first_tag(r.get("tags"))
    title = r.get("title") or r["file"].replace(".md", "")
    if r.get("plain"):
        li = f'<li class="recipe-item" data-name="{escape(title)}" data-tags="{escape(tag)}"><span class="plain">{escape(title)}</span></li>'
    else:
        li = f'<li class="recipe-item" data-name="{escape(title)}" data-tags="{escape(tag)}"><a href="recipes/{r["file"]}">{escape(title)}</a></li>'
    entries.append({"tag": tag, "sort_key": title.lower(), "html": li})

for g in group_map.values():
    search_parts = [g["name"]] + [v.get("variant_label") or v.get("title", "") for v in g["variants"]]
    search_name = " ".join(search_parts)

    variant_bits = []
    for v in g["variants"]:
        label = v.get("variant_label") or v.get("title") or v["file"]
        if v.get("plain"):
            variant_bits.append(f'<span class="plain">{escape(label)}</span>')
        else:
            variant_bits.append(f'<a href="recipes/{v["file"]}">{escape(label)}</a>')
    variant_html = ' <span class="variant-sep">/</span> '.join(variant_bits)

    li = (
        f'<li class="recipe-item" data-name="{escape(search_name)}" data-tags="{escape(g["tag"] or "")}">'
        f'<span class="plain">{escape(g["name"])}</span> &mdash; {variant_html}</li>'
    )
    entries.append({"tag": g["tag"] or "", "sort_key": g["name"].lower(), "html": li})

# --- Sort: by tag order, then alphabetically ---

entries.sort(key=lambda e: (tag_index(e["tag"]), e["sort_key"]))

# --- Generate index.html ---

list_html = "\n".join("    " + e["html"] for e in entries)
template = TEMPLATE.read_text(encoding="utf-8")
output = template.replace("{{RECIPE_LIST}}", list_html)

OUTPUT.write_text(output, encoding="utf-8")
print(f"Built index.html with {len(entries)} entries ({len(recipes)} recipe files)")
