#!/usr/bin/env python3
"""Refresh the static website's brand snapshot. No network or image generation.

Requires Python 3, fonttools[woff], cairosvg, and cwebp. Run from the website checkout:
    python3 scripts/sync-brand.py [--brand ../brand]
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", SVG[1:-1])

class TextCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def font_subset(path, family, characters):
    font = TTFont(path, recalcTimestamp=False)
    if "fvar" in font:
        axes = {axis.axisTag for axis in font["fvar"].axes}
        limits = {"wght": (400, 400, 600)}
        if "opsz" in axes:
            limits["opsz"] = 14
        font = instantiateVariableFont(font, limits, inplace=True)
    names = {1: family, 2: "Regular", 3: f"{family}-Website-Subset-1",
             4: family, 6: family.replace(" ", ""), 16: family,
             17: "Regular", 25: family.replace(" ", "")}
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    # Reload the instantiated font before subsetting its lazy variation tables.
    normalized = io.BytesIO()
    font.save(normalized)
    font = TTFont(io.BytesIO(normalized.getvalue()), recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.notdef_glyph = True
    options.notdef_outline = True
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17, 25]
    options.name_languages = [0x409]
    options.drop_tables += ["meta"]
    worker = subset.Subsetter(options=options)
    worker.populate(text=characters)
    worker.subset(font)
    font.flavor = "woff2"
    output = io.BytesIO()
    font.save(output)
    return output.getvalue()

def share_card(brand):
    """Compose the website's share card from brand vectors, type and approved art."""
    root = ET.Element(SVG + "svg", {"width": "1200", "height": "630", "viewBox": "0 0 1200 630", "role": "img", "aria-labelledby": "share-title"})
    ET.SubElement(root, SVG + "title", {"id": "share-title"}).text = "造 ZAO · Agent 开发引擎 · 打造你的 Agent。"
    ET.SubElement(root, SVG + "desc").text = "造官网分享图 · 开源 Agent 开发引擎。"
    ET.SubElement(root, SVG + "rect", {"width": "1200", "height": "630", "fill": "#F5EFE9"})
    defs = ET.SubElement(root, SVG + "defs")
    gradient = ET.SubElement(defs, SVG + "linearGradient", {"id": "art-fade", "x1": "0", "y1": "0", "x2": "1", "y2": "0"})
    for offset, opacity in [("0", "0"), ("0.28", "1"), ("1", "1")]:
        ET.SubElement(gradient, SVG + "stop", {"offset": offset, "stop-color": "white", "stop-opacity": opacity})
    mask = ET.SubElement(defs, SVG + "mask", {"id": "art-mask"})
    ET.SubElement(mask, SVG + "rect", {"x": "210", "width": "1120", "height": "630", "fill": "url(#art-fade)"})
    picture = base64.b64encode((ROOT / "assets/images/zao-keyvisual-wide.webp").read_bytes()).decode()
    ET.SubElement(root, SVG + "image", {"x": "210", "y": "0", "width": "1120", "height": "630", "href": "data:image/webp;base64," + picture, "mask": "url(#art-mask)"})
    identity = ET.fromstring((brand / "logo/zao-lockup-primary.svg").read_bytes())
    identity.attrib.update({"x": "72", "y": "40", "width": "150", "height": "58"})
    identity.attrib.pop("role", None)
    identity.attrib.pop("aria-labelledby", None)
    for child in list(identity):
        if child.tag in [SVG + "title", SVG + "desc"]:
            identity.remove(child)
    root.append(identity)
    fonts = {"cn": TTFont(brand / "fonts/noto-sans-sc/NotoSansSC-Regular.ttf"),
             "cn-bold": TTFont(brand / "fonts/noto-sans-sc/NotoSansSC-SemiBold.ttf"),
             "latin": TTFont(brand / "fonts/inter/Inter-Regular.ttf"),
             "latin-bold": TTFont(brand / "fonts/inter/Inter-SemiBold.ttf")}
    def text(value, x, baseline, size, fill="#24211F", bold=False, tracking=0):
        for character in value:
            kind = "latin" if ord(character) < 128 else "cn"
            font = fonts[kind + ("-bold" if bold else "")]
            glyphs = font.getGlyphSet()
            glyph = font.getBestCmap().get(ord(character), ".notdef")
            scale = size / font["head"].unitsPerEm
            pen = SVGPathPen(glyphs)
            glyphs[glyph].draw(pen)
            if pen.getCommands():
                ET.SubElement(root, SVG + "path", {"d": pen.getCommands(), "fill": fill,
                    "transform": f"translate({x:.3f} {baseline}) scale({scale:.6f} {-scale:.6f})"})
            x += glyphs[glyph].width * scale + tracking
    text("开源 Agent 开发引擎", 80, 245, 17, "#68605B", bold=True)
    text("打造你的", 76, 323, 60, bold=True, tracking=-2)
    text("Agent", 75, 413, 96, bold=True, tracking=-3)
    text(".", 344, 413, 75, "#D94A35", bold=True)
    for font in fonts.values():
        font.close()
    return ET.tostring(root, encoding="utf-8") + b"\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", type=Path, default=ROOT.parent / "brand")
    brand = parser.parse_args().brand.resolve()
    tokens = json.loads((brand / "guide/tokens.json").read_text())
    assets = ROOT / "assets"
    for directory in ["brand", "images", "fonts"]:
        (assets / directory).mkdir(parents=True, exist_ok=True)
    records = {}
    def save(relative, data, source, **extra):
        (ROOT / relative).write_bytes(data)
        records[relative] = {"source": source, "source_sha256": sha256((brand / source).read_bytes()),
                             "sha256": sha256(data), "bytes": len(data), **extra}
    for source, target in [
        ("logo/zao-lockup-primary.svg", "assets/brand/zao-lockup-primary.svg"),
        ("icons/web/favicon.ico", "favicon.ico"),
        ("icons/web/apple-touch-icon-180.png", "assets/brand/apple-touch-icon.png"),
    ]:
        data = (brand / source).read_bytes()
        if source.endswith(".svg"):
            vector = ET.fromstring(data)
            description = vector.find(SVG + "desc")
            if description is not None:
                description.text = "造 ZAO · Agent 开发引擎"
            data = ET.tostring(vector, encoding="utf-8") + b"\n"
        save(target, data, source, **({"adaptation": "Canonical geometry; product description updated for the website."} if source.endswith(".svg") else {}))
    source = "icons/web/favicon.svg"
    icon = ET.fromstring((brand / source).read_bytes())
    icon.find(SVG + "style").text = (":root{color:LIGHT}@media(prefers-color-scheme:dark){:root{color:DARK}}"
                                     .replace("LIGHT", tokens["colors"]["vermilion"])
                                     .replace("DARK", tokens["colors"]["chalk"]))
    for description in icon.iter(SVG + "desc"):
        if description.text:
            description.text = "造 ZAO · Agent 开发引擎"
    save("assets/brand/favicon.svg", ET.tostring(icon, encoding="utf-8") + b"\n", source,
         adaptation="Canonical geometry; vermilion in light mode, chalk in dark mode.")
    for source, name in [("visuals/zao-keyvisual-light-wide.png", "zao-keyvisual-wide.webp"),
                         ("visuals/zao-keyvisual-light-portrait.png", "zao-keyvisual-portrait.webp")]:
        target = assets / "images" / name
        subprocess.run(["cwebp", "-quiet", "-q", "88", "-m", "6", "-metadata", "none",
                        str(brand / source), "-o", str(target)], check=True)
        save(f"assets/images/{name}", target.read_bytes(), source,
             adaptation="WebP quality 88; original dimensions; metadata omitted.")
    card = share_card(brand)
    card_source = "assets/images/zao-share.svg"
    (ROOT / card_source).write_bytes(card)
    png = cairosvg.svg2png(bytestring=card, output_width=1200, output_height=630)
    (assets / "images/zao-share.png").write_bytes(png)
    records[card_source] = {"source_repository": ".", "source": "scripts/sync-brand.py", "source_sha256": sha256(Path(__file__).read_bytes()), "sha256": sha256(card), "bytes": len(card), "adaptation": "Site-specific composition from canonical brand geometry, outlined brand fonts and the approved key visual."}
    records["assets/images/zao-share.png"] = {"source_repository": ".", "source": card_source, "source_sha256": sha256(card), "sha256": sha256(png), "bytes": len(png), "adaptation": "CairoSVG rendering, 1200 × 630 pixels."}
    collector = TextCollector()
    collector.feed((ROOT / "index.html").read_text())
    characters = "".join(collector.parts) + "".join(chr(n) for n in range(32, 127)) + "·，。—（）"
    for directory, filename, family, target in [
        ("noto-sans-sc", "NotoSansSC-VF.ttf", "ZAO Web Sans SC", "zao-sans-sc.woff2"),
        ("inter", "Inter-VF.ttf", "ZAO Web Inter", "zao-inter.woff2"),
    ]:
        source = f"fonts/{directory}/{filename}"
        data = font_subset(brand / source, family, characters)
        save(f"assets/fonts/{target}", data, source,
             adaptation="Renamed WOFF2 subset; weights 400–600; source license and copyright retained.")
        source = f"fonts/{directory}/OFL.txt"
        save(f"assets/fonts/{directory}-OFL.txt", (brand / source).read_bytes(), source)
    html = (ROOT / "index.html").read_text()
    css = (ROOT / "styles/main.css").read_text()
    for filename in ["zao-sans-sc.woff2", "zao-inter.woff2"]:
        version = records[f"assets/fonts/{filename}"]["sha256"][:12]
        pattern = re.escape(filename) + r"(?:\?v=[a-zA-Z0-9-]+)?"
        html = re.sub(pattern, filename + "?v=" + version, html)
        css = re.sub(pattern, filename + "?v=" + version, css)
    (ROOT / "styles/main.css").write_text(css)
    for filename, path in [("styles/main.css", ROOT / "styles/main.css")]:
        html = re.sub(re.escape(filename) + r"(?:\?v=[a-zA-Z0-9-]+)?", filename + "?v=" + sha256(path.read_bytes())[:12], html)
    html = re.sub(r"assets/images/zao-share.png(?:\?v=[a-zA-Z0-9-]+)?", "assets/images/zao-share.png?v=" + sha256(png)[:12], html)
    (ROOT / "index.html").write_text(html)
    (assets / "sources.json").write_text(json.dumps({
        "brand_version": tokens["version"], "source_repository": "../brand",
        "refresh": "python3 scripts/sync-brand.py", "files": records,
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"brand": tokens["version"], "assets": len(records),
                      "webfont_bytes": sum(r["bytes"] for p, r in records.items() if p.endswith(".woff2"))}))

if __name__ == "__main__":
    main()
