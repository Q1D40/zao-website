#!/usr/bin/env python3
"""Refresh the static website's brand snapshot. No network or image generation.

Requires Python 3, fonttools[woff], and cwebp. Run from the website checkout:
    python3 scripts/sync-brand.py [--brand ../brand]
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

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
        ("social/share/zao-opengraph-keyvisual-light.png", "assets/images/zao-share.png"),
    ]:
        save(target, (brand / source).read_bytes(), source)
    source = "icons/web/favicon.svg"
    icon = ET.fromstring((brand / source).read_bytes())
    icon.find(SVG + "style").text = (":root{color:LIGHT}@media(prefers-color-scheme:dark){:root{color:DARK}}"
                                     .replace("LIGHT", tokens["colors"]["vermilion"])
                                     .replace("DARK", tokens["colors"]["chalk"]))
    save("assets/brand/favicon.svg", ET.tostring(icon, encoding="utf-8") + b"\n", source,
         adaptation="Canonical geometry; vermilion in light mode, chalk in dark mode.")
    for source, name in [("visuals/zao-keyvisual-light-wide.png", "zao-keyvisual-wide.webp"),
                         ("visuals/zao-keyvisual-light-portrait.png", "zao-keyvisual-portrait.webp")]:
        target = assets / "images" / name
        subprocess.run(["cwebp", "-quiet", "-q", "88", "-m", "6", "-metadata", "none",
                        str(brand / source), "-o", str(target)], check=True)
        save(f"assets/images/{name}", target.read_bytes(), source,
             adaptation="WebP quality 88; original dimensions; metadata omitted.")
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
    (assets / "sources.json").write_text(json.dumps({
        "brand_version": tokens["version"], "source_repository": "../brand",
        "refresh": "python3 scripts/sync-brand.py", "files": records,
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"brand": tokens["version"], "assets": len(records),
                      "webfont_bytes": sum(r["bytes"] for p, r in records.items() if p.endswith(".woff2"))}))

if __name__ == "__main__":
    main()
