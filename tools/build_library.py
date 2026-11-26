"""Build the Bulles comic library from Pepper&Carrot sources.

Usage: python build_library.py <sources_dir> <app_dir>

For every episode, page and language it:
  * copies the text-free artwork (gfx) into app/comics/<ep>/gfx/
  * scales the language's text layer (txt-only PNG: speech bubbles + lettering)
    to the artwork size and saves it to app/comics/<ep>/txt/<lang>/
  * finds each bubble or caption on the text layer and records its box
  * reads the page SVG + transcript to attach the words and speaker to each box
and writes app/data/library.js (loaded by the app, works offline too).
"""
import json, math, os, re, sys, shutil
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from scipy import ndimage

SRC, APP = sys.argv[1], sys.argv[2]
LANGS = {
    "fr": "Français", "en": "English", "pt": "Português",
    "es": "Español", "de": "Deutsch", "it": "Italiano",
}
EPISODES = [("ep01_Potion-of-Flight", "ep01", "E01", 5), ("ep02_Rainbow-potions", "ep02", "E02", 7)]
NS = {"svg": "http://www.w3.org/2000/svg"}
INK = "{http://www.inkscape.org/namespaces/inkscape}"


# ---------- SVG text positions ----------
def parse_transform(t):
    m = np.eye(3)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", t or ""):
        a = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "matrix":
            n = np.array([[a[0], a[2], a[4]], [a[1], a[3], a[5]], [0, 0, 1]])
        elif name == "translate":
            n = np.array([[1, 0, a[0]], [0, 1, a[1] if len(a) > 1 else 0], [0, 0, 1]])
        elif name == "scale":
            sy = a[1] if len(a) > 1 else a[0]
            n = np.array([[a[0], 0, 0], [0, sy, 0], [0, 0, 1]])
        elif name == "rotate":
            r = math.radians(a[0]); c, s = math.cos(r), math.sin(r)
            n = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(a) == 3:
                n = np.array([[1, 0, a[1]], [0, 1, a[2]], [0, 0, 1]]) @ n @ np.array([[1, 0, -a[1]], [0, 1, -a[2]], [0, 0, 1]])
        else:
            continue
        m = m @ n
    return m


def local(tag):
    return tag.split("}")[-1]


def svg_texts(path):
    """Return [(text, (x, y))] in SVG user units for every text block on the txt layer."""
    root = ET.parse(path).getroot()
    out = []

    def walk(el, m, in_txt):
        m = m @ parse_transform(el.get("transform"))
        tag = local(el.tag)
        is_txt_layer = tag == "g" and (el.get(INK + "label") or "").lower().startswith(("txt", "text"))
        in_txt = in_txt or is_txt_layer
        if in_txt and tag == "flowRoot":
            rect = el.find(".//svg:flowRegion/svg:rect", NS)
            lines = ["".join(p.itertext()).strip() for p in el.iter() if local(p.tag) in ("flowPara", "flowDiv")]
            text = " ".join(l for l in lines if l)
            if rect is not None and text:
                rm = m @ parse_transform(rect.get("transform"))
                cx = float(rect.get("x", 0)) + float(rect.get("width", 0)) / 2
                cy = float(rect.get("y", 0)) + min(float(rect.get("height", 0)) / 2, 60)
                p = rm @ np.array([cx, cy, 1])
                out.append((text, (p[0], p[1])))
            return
        if in_txt and tag == "text":
            spans = [s for s in el.iter() if local(s.tag) == "tspan" and (s.text or "").strip()]
            lines = []
            for s in spans:
                if s.get(f"{{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}}role") == "line" or not lines:
                    lines.append("".join(s.itertext()).strip())
                else:
                    lines[-1] += " " + "".join(s.itertext()).strip()
            text = " ".join(l for l in lines if l) or "".join(el.itertext()).strip()
            first = spans[0] if spans else el
            x = float((first.get("x") or el.get("x") or "0").split()[0])
            y = float((first.get("y") or el.get("y") or "0").split()[0])
            if text:
                p = m @ np.array([x, y, 1])
                out.append((text, (p[0], p[1])))
            return
        for c in el:
            walk(c, m, in_txt)

    walk(root, np.eye(3), False)
    w = float(re.sub(r"[a-z]+$", "", root.get("width", "2481")))
    h = float(re.sub(r"[a-z]+$", "", root.get("height", "3503")))
    return out, (w, h)


def transcript(path):
    """page id -> list of (position, speaker, text, concatenate)."""
    pages, cur = {}, None
    if not os.path.exists(path):
        return pages
    for line in open(path, encoding="utf-8"):
        m = re.match(r"###\s+(P\d+)", line)
        if m:
            cur = pages.setdefault(m.group(1), []); continue
        if cur is None or "|" not in line or line.startswith("Name|") or line.startswith("----"):
            continue
        parts = line.rstrip("\n").split("|")
        if len(parts) >= 4 and parts[1].strip().isdigit():
            cur.append((int(parts[1]), parts[0].strip(), parts[3].strip(), parts[2].strip() == "True"))
    return pages


def norm(s):
    return re.sub(r"\W+", "", s.lower())


# ---------- bubble boxes from the text layer ----------
def find_items(alpha):
    """alpha: HxW uint8. Return list of (x0, y0, x1, y1, density) in pixels."""
    h, w = alpha.shape
    k = 3  # analyse at 1/3 scale
    small = alpha[::k, ::k] > 24
    grown = ndimage.binary_dilation(small, iterations=4)
    lab, n = ndimage.label(grown)
    boxes = []
    for sl in ndimage.find_objects(lab):
        y0, y1 = sl[0].start * k, min(h, sl[0].stop * k)
        x0, x1 = sl[1].start * k, min(w, sl[1].stop * k)
        if (x1 - x0) * (y1 - y0) < 900:
            continue
        sub = alpha[y0:y1, x0:x1]
        boxes.append([x0, y0, x1, y1, float((sub > 200).mean())])
    return boxes


def build():
    os.makedirs(os.path.join(APP, "data"), exist_ok=True)
    comics = []
    for folder, cid, E, npages in EPISODES:
        src = os.path.join(SRC, folder)
        info = json.load(open(os.path.join(src, "info.json"), encoding="utf-8"))
        credits = {"art": [re.sub(r"\s*<.*>", "", a) for a in info["credits"]["art"]],
                   "scenario": [re.sub(r"\s*<.*>", "", a) for a in info["credits"]["scenario"]],
                   "translation": {}}
        trans = {}
        for lang in LANGS:
            li = os.path.join(src, "lang", lang, "info.json")
            if os.path.exists(li):
                c = json.load(open(li, encoding="utf-8")).get("credits", {})
                credits["translation"][lang] = {k: [re.sub(r"\s*<.*>", "", v) for v in vs] for k, vs in c.items()}
            trans[lang] = transcript(os.path.join(src, "lang", lang, "transcript.md"))
        dst = os.path.join(APP, "comics", cid)
        os.makedirs(os.path.join(dst, "gfx"), exist_ok=True)
        ids = [E] + [f"{E}P{i:02d}" for i in range(npages)]
        pages, cover, titles = [], None, {}
        for pid in ids:
            gfx = Image.open(os.path.join(src, "gfx", pid + ".jpg"))
            W, H = gfx.size
            shutil.copy(os.path.join(src, "gfx", pid + ".jpg"), os.path.join(dst, "gfx", pid + ".jpg"))
            page = {"id": pid, "gfx": f"comics/{cid}/gfx/{pid}.jpg", "w": W, "h": H, "items": {}}
            for lang in LANGS:
                tp = os.path.join(src, "txt", lang, pid + ".png")
                if not os.path.exists(tp):
                    continue
                txt = Image.open(tp).convert("RGBA")
                if txt.size != (W, H):
                    txt = txt.resize((W, H), Image.LANCZOS)
                os.makedirs(os.path.join(dst, "txt", lang), exist_ok=True)
                txt.save(os.path.join(dst, "txt", lang, pid + ".png"), optimize=True)
                if pid == E:
                    continue
                alpha = np.array(txt)[:, :, 3]
                boxes = find_items(alpha)
                # words and speakers
                texts, (sw, sh) = [], (W, H)
                svg = os.path.join(src, "lang", lang, pid + ".svg")
                if os.path.exists(svg):
                    texts, (sw, sh) = svg_texts(svg)
                rows = trans[lang].get(pid[len(E):], [])
                byText = {norm(r[2]): r for r in rows}
                items = []
                for b in boxes:
                    x0, y0, x1, y1, dens = b
                    found = []
                    for t, (px, py) in texts:
                        qx, qy = px * W / sw, py * H / sh
                        if x0 - 6 <= qx <= x1 + 6 and y0 - 6 <= qy <= y1 + 6:
                            r = byText.get(norm(t))
                            found.append((r[0] if r else 999, r[1] if r else "", t))
                    found.sort()
                    item = {"b": [round(x0 / W, 4), round(y0 / H, 4), round((x1 - x0) / W, 4), round((y1 - y0) / H, 4)],
                            "bubble": dens > 0.45}
                    if found:
                        item["t"] = " ".join(f[2] for f in found)
                        sp = [f[1] for f in found if f[1]]
                        if sp:
                            item["s"] = sp[0]
                    items.append(item)
                # reading order: by transcript position when known, else top-to-bottom
                items.sort(key=lambda it: (round(it["b"][1] * 8), it["b"][0]))
                page["items"][lang] = items
                if pid.endswith("P00") and rows:
                    titles[lang] = " ".join(r[2] for r in sorted(rows))
            if pid == E:
                cover = {"gfx": page["gfx"], "w": W, "h": H}
            else:
                pages.append(page)
        comics.append({"id": cid, "series": "Pepper&Carrot", "title": titles, "cover": cover,
                       "credits": credits, "pages": pages,
                       "langs": sorted(set.intersection(*[set(p["items"]) for p in pages if p["items"]]))})
    lib = {"langs": LANGS, "comics": comics,
           "source": "https://www.peppercarrot.com", "license": "CC BY 4.0"}
    with open(os.path.join(APP, "data", "library.js"), "w", encoding="utf-8") as f:
        f.write("window.BULLES_LIBRARY = " + json.dumps(lib, ensure_ascii=False, separators=(",", ":")) + ";\n")
    return lib


if __name__ == "__main__":
    lib = build()
    for c in lib["comics"]:
        print(c["id"], c["title"].get("fr"), "| langs", c["langs"])
        for p in c["pages"]:
            print("  ", p["id"], {l: (len(v), sum(1 for i in v if "t" in i)) for l, v in p["items"].items()})
