"""Build the Bulles library for the whole Pepper&Carrot series.

Usage: python build_series.py <sources_dir> <app_dir>

<sources_dir> holds manifest.json and one folder per episode (as downloaded):
    <episode>/info.json
    <episode>/gfx/<page>.jpg|gif           artwork without text
    <episode>/txt/<lang>/<page>.png        bubbles + lettering for one language
    <episode>/lang/<lang>/*.svg, info.json, transcript.md

Writes into <app_dir>/data/:
    library.js                 the series, its episodes, titles, languages, credits
    covers.js                  small cover pictures for the episode grid
    episodes/<ep>/pages.js     artwork + bubble positions and words (all languages)
    episodes/<ep>/<lang>.js    one language's text layers
Images are embedded as data: URIs so the app also works when opened from disk.
"""
import base64, io, json, os, re, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from build_library import svg_texts, transcript, find_items, norm  # reuse the parsers

SRC, APP = sys.argv[1], sys.argv[2]
LANGS = {"fr": "Français", "en": "English", "pt": "Português", "es": "Español", "de": "Deutsch", "it": "Italiano"}
OUT = os.path.join(APP, "data")


def uri(data, mime):
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def jpg_bytes(im, q=80):
    b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=q, optimize=True, progressive=True); return b.getvalue()


def webp_bytes(im, q=78):
    b = io.BytesIO(); im.convert("RGB").save(b, "WEBP", quality=q, method=5); return b.getvalue()


def png_bytes(im):
    """Text layers: 256-colour palette with alpha keeps them small and crisp."""
    b = io.BytesIO()
    q = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    q.save(b, "PNG", optimize=True)
    return b.getvalue()


def clean(names):
    return [re.sub(r"\s*<.*?>", "", n).strip() for n in names]


def write_js(path, call, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(call + "(" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ");\n")


def scan():
    """Describe each downloaded episode: its pages, their sizes, and the languages complete for it."""
    out = []
    for folder in sorted(d for d in os.listdir(SRC) if re.match(r"ep\d\d_", d)):
        g = os.path.join(SRC, folder, "gfx")
        pages = sorted(os.listdir(g), key=lambda f: (len(f.split(".")[0]), f))
        dims = {f.rsplit(".", 1)[0]: list(Image.open(os.path.join(g, f)).size) for f in pages}
        jpgs = [f.rsplit(".", 1)[0] for f in pages if f.endswith(".jpg")]
        tdir = os.path.join(SRC, folder, "txt")
        langs = [l for l in LANGS if os.path.isdir(os.path.join(tdir, l))
                 and all(os.path.exists(os.path.join(tdir, l, p + ".png")) for p in jpgs)]
        out.append({"folder": folder, "pages": pages, "langs": langs, "dims": dims})
    return out


def build():
    manifest = scan()
    episodes, covers = [], {}
    for m in manifest:
        folder = m["folder"]
        num = int(folder[2:4]); eid = f"ep{num:02d}"; E = f"E{num:02d}"
        src = os.path.join(SRC, folder)
        langs = [l for l in LANGS if l in m["langs"]]
        info = json.load(open(os.path.join(src, "info.json"), encoding="utf-8"))
        cred = {k: clean(v) for k, v in info.get("credits", {}).items() if isinstance(v, list)}
        tcred, trans = {}, {}
        for l in langs:
            li = os.path.join(src, "lang", l, "info.json")
            if os.path.exists(li):
                c = json.load(open(li, encoding="utf-8")).get("credits", {})
                tcred[l] = {k: clean(v) for k, v in c.items() if isinstance(v, list)}
            trans[l] = transcript(os.path.join(src, "lang", l, "transcript.md"))
        pages, layers, titles = [], {l: {} for l in langs}, {}
        for fname in m["pages"]:
            pid = fname.rsplit(".", 1)[0]
            path = os.path.join(src, "gfx", fname)
            if pid == E:  # cover
                im = Image.open(path).convert("RGB"); im.thumbnail((520, 520))
                covers[eid] = uri(webp_bytes(im, 72), "image/webp")
                continue
            W, H = m["dims"][pid]
            if fname.endswith(".gif"):
                page = {"id": pid, "w": W, "h": H, "img": uri(open(path, "rb").read(), "image/gif"), "items": {}, "anim": True}
                pages.append(page); continue
            page = {"id": pid, "w": W, "h": H, "img": uri(webp_bytes(Image.open(path)), "image/webp"), "items": {}}
            for l in langs:
                tp = os.path.join(src, "txt", l, pid + ".png")
                if not os.path.exists(tp):
                    continue
                txt = Image.open(tp).convert("RGBA")
                if txt.size != (W, H):
                    txt = txt.resize((W, H), Image.LANCZOS)
                alpha = np.array(txt)[:, :, 3]
                if alpha.max() == 0:
                    page["items"][l] = []
                    continue
                layers[l][pid] = uri(png_bytes(txt), "image/png")
                texts, (sw, sh) = [], (W, H)
                svg = os.path.join(src, "lang", l, pid + ".svg")
                if os.path.exists(svg):
                    try:
                        texts, (sw, sh) = svg_texts(svg)
                    except Exception as e:  # a broken SVG only costs the words, not the flip
                        print("  svg?", eid, pid, l, e)
                rows = trans[l].get(pid[len(E):], [])
                by_text = {norm(r[2]): r for r in rows}
                items = []
                for x0, y0, x1, y1, _ in find_items(alpha):
                    found = []
                    for t, (px, py) in texts:
                        qx, qy = px * W / sw, py * H / sh
                        if x0 - 6 <= qx <= x1 + 6 and y0 - 6 <= qy <= y1 + 6:
                            r = by_text.get(norm(t))
                            found.append((r[0] if r else 999, r[1] if r else "", t))
                    found.sort()
                    it = {"b": [round(x0 / W, 4), round(y0 / H, 4), round((x1 - x0) / W, 4), round((y1 - y0) / H, 4)]}
                    if found:
                        it["t"] = " ".join(f[2] for f in found)
                        sp = [f[1] for f in found if f[1]]
                        if sp: it["s"] = sp[0]
                    items.append(it)
                items.sort(key=lambda it: (round(it["b"][1] * 8), it["b"][0]))
                page["items"][l] = items
                if pid.endswith("P00") and l not in titles:
                    words = [r[2] for r in sorted(rows)] or [i["t"] for i in items if "t" in i]
                    if words: titles[l] = " ".join(words)
            pages.append(page)
        fallback = re.sub(r"^ep\d\d_", "", folder).replace("-s-", "'s ").replace("-", " ")
        for l in langs:
            titles.setdefault(l, f"Episode {num}: {fallback}")
        write_js(os.path.join(OUT, "episodes", eid, "pages.js"), "BULLES_LOAD", {"ep": eid, "part": "pages", "pages": pages})
        for l in langs:
            write_js(os.path.join(OUT, "episodes", eid, l + ".js"), "BULLES_LOAD", {"ep": eid, "part": l, "layers": layers[l]})
        episodes.append({"id": eid, "n": num, "title": titles, "langs": langs, "pages": len(pages),
                         "credits": cred, "translation": tcred})
        print(eid, len(pages), "pages", langs, "|", titles.get("fr", "")[:50])
    lib = {"langs": LANGS, "series": [{
        "id": "pepper-carrot", "name": "Pepper&Carrot", "author": "David Revoy",
        "blurb": {"en": "A young witch, her cat and a world of potions and magic.",
                  "fr": "Une jeune sorcière, son chat et un monde de potions et de magie."},
        "site": "https://www.peppercarrot.com", "license": "CC BY 4.0",
        "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
        "episodes": episodes}]}
    write_js(os.path.join(OUT, "library.js"), "BULLES_LIBRARY_LOAD", lib)
    write_js(os.path.join(OUT, "covers.js"), "BULLES_COVERS_LOAD", covers)


if __name__ == "__main__":
    build()
