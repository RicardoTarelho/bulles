"""Build a Bulles book from segmented text + sentence translations.

Usage: python build_book.py <book_dir> <app_dir>
<book_dir> holds segmented.json (tales -> paragraphs -> French sentences) and
one tr_<tale>.json per tale with "title" and aligned "en" / "pt" lists.
Writes <app_dir>/data/books/perrault/<tale>.js and returns the library entry.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from levels import level_range

TALES = [  # id, translation file, estimated level, why
    ("chaperon", "tr_chaperon.json", "B1", "short and repetitive, but uses the literary past tense"),
    ("fees", "tr_fees.json", "B2", "literary tenses and some old-fashioned words"),
    ("chat", "tr_chat.json", "B2", "long sentences, literary tenses, old vocabulary"),
    ("cendrillon", "tr_cendrillon.json", "B2", "long sentences, literary tenses, old vocabulary"),
]


def build(book_dir, app_dir):
    seg = json.load(open(os.path.join(book_dir, "segmented.json"), encoding="utf-8"))
    out_dir = os.path.join(app_dir, "data", "books", "perrault")
    os.makedirs(out_dir, exist_ok=True)
    chapters = []
    for (tid, tf, lvl, why), tale in zip(TALES, seg):
        tr = json.load(open(os.path.join(book_dir, tf), encoding="utf-8"))
        flat = [s for p in tale["paras"] for s in p["s"]]
        assert len(flat) == len(tr["en"]) == len(tr["pt"]), tid
        i, paras = 0, []
        for p in tale["paras"]:
            ss = []
            for s in p["s"]:
                ss.append({"fr": s, "en": tr["en"][i], "pt": tr["pt"][i]})
                i += 1
            paras.append({"poem": p["poem"], "s": ss})
        with open(os.path.join(out_dir, tid + ".js"), "w", encoding="utf-8") as f:
            f.write("BULLES_LOAD(" + json.dumps({"ep": "perrault/" + tid, "part": "text", "paras": paras},
                                                 ensure_ascii=False, separators=(",", ":")) + ");\n")
        words = sum(len(s.split()) for s in flat)
        chapters.append({"id": tid, "title": tr["title"], "level": lvl, "levelWhy": why,
                         "sentences": len(flat), "words": words, "minutes": max(2, round(words / 120))})
    return {
        "id": "perrault", "kind": "book", "lang": "fr", "langs": ["fr", "en", "pt"],
        "title": {"fr": "Contes de Perrault", "en": "Perrault's Fairy Tales", "pt": "Contos de Perrault"},
        "author": "Charles Perrault", "year": 1697,
        "blurb": {"en": "Four of the fairy tales that made Little Red Riding Hood, Puss in Boots and Cinderella famous.",
                  "pt": "Quatro dos contos que tornaram famosos o Capuchinho Vermelho, o Gato das Botas e a Gata Borralheira.",
                  "fr": "Quatre contes qui ont rendu célèbres le Petit Chaperon rouge, le Chat botté et Cendrillon."},
        "level": level_range([c["level"] for c in chapters]),
        "source": "https://fr.wikisource.org/wiki/Contes_des_f%C3%A9es_(Montr%C3%A9al,_1886)",
        "sourceName": "Contes des fées, Beauchemin et Valois, Montréal, 1886 (Wikisource)",
        "license": "Public domain",
        "translations": "English and Portuguese translations made with Claude for Bulles.",
        "chapters": chapters,
    }


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1)[:600])
