"""Finish the library after the book builders have run.

1. Keeps only the four Bulles languages (French, English, Portuguese, Spanish):
   drops German and Italian from the language list, the episodes and their titles.
2. Merges Spanish sentence translations into the built book chapters.

Spanish lives in <work>/tr_es/<book>__<chapter>.json:
    {"title": "...", "who": {"<French speaker label>": "<Spanish>"}, "es": ["...", ...]}
with one entry per sentence, in the same order as the French text.
A book gets "es" in its languages only when every one of its chapters has Spanish.

usage: python3 add_spanish.py <work_dir> <app_dir>
"""
import json, os, re, sys

KEEP = ["fr", "en", "pt", "es"]

BOOK_ES = {
    "perrault": {"title": "Cuentos de Perrault",
                 "blurb": "Cuatro de los cuentos que hicieron famosos a Caperucita Roja, el Gato con Botas y Cenicienta."},
    "sophie": {"title": "Las desgracias de Sofía",
               "blurb": "Una niña que siempre se mete en líos, en capítulos cortos y divertidos para niños."},
    "andersen": {"title": "Cuentos de Andersen",
                 "blurb": "La princesa y el guisante, El traje nuevo del emperador, La pequeña cerillera y otros, en una traducción francesa clásica."},
    "grimm": {"title": "Cuentos de Grimm",
              "blurb": "Los músicos de Bremen, La liebre y el erizo, Juan con suerte y El pescador y su mujer."},
    "daudet": {"title": "Cuentos de Daudet",
               "blurb": "Tres cuentos de las Cartas desde mi molino, ambientados en la Provenza, y el famoso cuento La última clase."},
    "maupassant": {"title": "Cuentos de Maupassant",
                   "blurb": "Tres de sus cuentos más conocidos, todos con un final inesperado: El collar, En el campo y Mi tío Jules."},
}
SERIES_BLURB = {"pt": "Uma jovem bruxa, o seu gato e um mundo de poções e magia.",
                "es": "Una joven bruja, su gato y un mundo de pociones y magia."}
# The established Portuguese title of the Comtesse de Ségur's book
PT_TITLE = {"sophie": "Os Desastres de Sofia"}


def load(p):
    s = open(p, encoding="utf-8").read()
    return s[:s.index("(") + 1], json.loads(s[s.index("(") + 1:s.rindex(")")]), s[s.rindex(")"):]


def save(p, head, d, tail):
    with open(p, "w", encoding="utf-8") as f:
        f.write(head + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + tail)


def main(work, app):
    lp = os.path.join(app, "data", "library.js")
    head, lib, tail = load(lp)
    lib["langs"] = {k: v for k, v in lib["langs"].items() if k in KEEP}
    for se in lib["series"]:
        se["blurb"].update({k: v for k, v in SERIES_BLURB.items() if k not in se["blurb"]})
        for e in se["episodes"]:
            e["langs"] = [l for l in e["langs"] if l in KEEP]
            if isinstance(e.get("title"), dict):
                e["title"] = {k: v for k, v in e["title"].items() if k in KEEP}
    for b in lib.get("books", []):
        if b["id"] in PT_TITLE:
            b["title"]["pt"] = PT_TITLE[b["id"]]
        meta = BOOK_ES.get(b["id"], {})
        if meta:
            b["title"]["es"] = meta["title"]
            b["blurb"]["es"] = meta["blurb"]
        complete = True
        for c in b["chapters"]:
            trp = os.path.join(work, "tr_es", b["id"] + "__" + c["id"] + ".json")
            if not os.path.exists(trp):
                complete = False
                continue
            tr = json.load(open(trp, encoding="utf-8"))
            cp = os.path.join(app, "data", "books", b["id"], c["id"] + ".js")
            h, d, t = load(cp)
            sents = [s for p in d["paras"] for s in p["s"]]
            if len(sents) != len(tr["es"]):
                raise SystemExit(f"{b['id']}/{c['id']}: {len(sents)} fr / {len(tr['es'])} es")
            for s, es in zip(sents, tr["es"]):
                s["es"] = re.sub(r"[ \t]+", " ", es).strip()
            for p in d["paras"]:
                if p.get("who"):
                    w = p["who"]["fr"]
                    es = tr.get("who", {}).get(w) or tr.get("who", {}).get(w[:1].lower() + w[1:])
                    if not es:
                        raise SystemExit(f"{b['id']}/{c['id']}: no Spanish for speaker label {w!r}")
                    p["who"]["es"] = es
            save(cp, h, d, t)
            c["title"]["es"] = tr["title"]
        b["langs"] = [l for l in ["fr", "en", "pt"] + (["es"] if complete else []) if l == "fr" or l in b["langs"] or l == "es"]
        b["translations"] = ("English, Portuguese and Spanish" if complete else "English and Portuguese") + " translations made with Claude for Bulles."
        print(b["id"], "es" if complete else "no es yet", b["langs"])
    save(lp, head, lib, tail)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
