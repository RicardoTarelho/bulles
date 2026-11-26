"""Build Bulles books from segmented text + sentence translations.

Usage: python build_books.py <work_dir> <app_dir>
  <work_dir>/seg/<book>__NN.json   segmented French (paragraphs, sentences, speaker labels)
  <work_dir>/tr/<book>__NN.json    {"title": {fr,en,pt}, "who": {label: [en, pt]}, "en": [...], "pt": [...]}
Only chapters that have a translation file are built, so a book can grow over time.
Writes <app_dir>/data/books/<id>/<NN>.js and merges the books into data/library.js.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from levels import level_range

BOOKS = {
    "sophie": {"title": {"fr": "Les Malheurs de Sophie", "en": "Sophie's Misfortunes", "pt": "As Desgraças de Sofia"},
               "author": "Comtesse de Ségur", "year": 1858, "unit": "chapters", "color": "#2f5d8a",
               "blurb": {"en": "A little girl who keeps getting into trouble, told in short, funny chapters for children.",
                         "pt": "Uma menina que está sempre a meter-se em sarilhos, em capítulos curtos e divertidos para crianças.",
                         "fr": "Une petite fille qui fait sans cesse des bêtises, en courts chapitres pleins d’humour."},
               "level": "A2", "why": "simple everyday vocabulary and lots of dialogue, with some literary past tenses",
               "source": "https://fr.wikisource.org/wiki/Les_Malheurs_de_Sophie", "sourceName": "Les Malheurs de Sophie, Hachette (Wikisource)"},
    "andersen": {"title": {"fr": "Contes d’Andersen", "en": "Andersen's Fairy Tales", "pt": "Contos de Andersen"},
                 "author": "Hans Christian Andersen", "translator": "David Soldi", "year": 1876, "unit": "tales", "color": "#24606b",
                 "blurb": {"en": "The Princess and the Pea, The Emperor's New Clothes, The Little Match Girl and more, in a classic French translation.",
                           "pt": "A Princesa e a Ervilha, O Rei Vai Nu, A Menina dos Fósforos e outros, numa tradução francesa clássica.",
                           "fr": "La Princesse sur un pois, Les Habits neufs du Grand-Duc, La Petite Fille et les allumettes et d’autres."},
                 "level": "B1", "why": "familiar stories, descriptive language, literary past tenses",
                 "source": "https://fr.wikisource.org/wiki/Contes_d%E2%80%99Andersen", "sourceName": "Contes d’Andersen, translated by David Soldi, Hachette, 1876 (Wikisource)"},
    "grimm": {"title": {"fr": "Contes de Grimm", "en": "Grimm's Fairy Tales", "pt": "Contos de Grimm"},
              "author": "Jacob et Wilhelm Grimm", "translator": "Frédéric Baudry", "year": 1864, "unit": "tales", "color": "#5a4a2a",
              "blurb": {"en": "The Town Musicians of Bremen, The Hare and the Hedgehog, Hans in Luck and The Fisherman and His Wife.",
                        "pt": "Os Músicos de Bremen, A Lebre e o Ouriço, João Felizardo e O Pescador e a Mulher.",
                        "fr": "Les Musiciens de Brême, Le Lièvre et le Hérisson, Jean le chanceux et Le Pêcheur et sa femme."},
              "level": "B1", "why": "simple storytelling with repetition, literary past tenses",
              "source": "https://fr.wikisource.org/wiki/Contes_choisis_des_fr%C3%A8res_Grimm", "sourceName": "Contes choisis des frères Grimm, translated by Frédéric Baudry, Hachette, 1864 (Wikisource)"},
    "daudet": {"title": {"fr": "Contes de Daudet", "en": "Daudet's Stories", "pt": "Contos de Daudet"},
               "author": "Alphonse Daudet", "year": 1869, "unit": "stories", "color": "#8a5a1e",
               "blurb": {"en": "Three tales from Letters from My Windmill, set in Provence, and the famous story The Last Lesson.",
                         "pt": "Três contos das Cartas do Meu Moinho, passados na Provença, e o famoso conto A Última Aula.",
                         "fr": "Trois contes des Lettres de mon moulin et la célèbre Dernière Classe."},
               "level": "B2", "why": "rich vocabulary, Provençal words and literary tenses",
               "source": "https://fr.wikisource.org/wiki/Lettres_de_mon_moulin", "sourceName": "Lettres de mon moulin (1869) and Contes du lundi (1873) (Wikisource)"},
    "maupassant": {"title": {"fr": "Contes de Maupassant", "en": "Maupassant's Short Stories", "pt": "Contos de Maupassant"},
                   "author": "Guy de Maupassant", "year": 1884, "unit": "stories", "color": "#3b3b45",
                   "blurb": {"en": "Three of his best-known stories, each with a sting in the tail: The Necklace, In the Fields and My Uncle Jules.",
                             "pt": "Três dos seus contos mais conhecidos, todos com um final inesperado: O Colar, No Campo e O Meu Tio Jules.",
                             "fr": "Trois de ses contes les plus connus : La Parure, Aux champs et Mon oncle Jules."},
                   "level": "B2", "why": "adult literary style, long sentences and literary tenses",
                   "source": "https://fr.wikisource.org/wiki/Auteur:Guy_de_Maupassant", "sourceName": "Contes du jour et de la nuit (1885) and Contes de la bécasse (1883) (Wikisource)"},
}
ORDER = ["sophie", "andersen", "grimm", "daudet", "maupassant"]
CH_LEVEL = {"daudet__04": "B1", "andersen__01": "A2", "andersen__03": "B1", "grimm__02": "B1"}


def tidy(s):
    return re.sub(r"\s{2,}", " ", s).strip()


def build(work, app):
    entries = []
    for bid in ORDER:
        meta = BOOKS[bid]
        chapters = []
        for segf in sorted(glob.glob(os.path.join(work, "seg", bid + "__*.json"))):
            name = os.path.basename(segf)[:-5]
            trf = os.path.join(work, "tr", name + ".json")
            if not os.path.exists(trf):
                continue
            seg = json.load(open(segf, encoding="utf-8"))
            tr = json.load(open(trf, encoding="utf-8"))
            flat = [s for p in seg["paras"] for s in p["s"]]
            if not (len(flat) == len(tr["en"]) == len(tr["pt"])):
                raise SystemExit(f"{name}: {len(flat)} fr / {len(tr['en'])} en / {len(tr['pt'])} pt")
            i, paras = 0, []
            for p in seg["paras"]:
                ss = []
                for s in p["s"]:
                    ss.append({"fr": tidy(s), "en": tidy(tr["en"][i]), "pt": tidy(tr["pt"][i])}); i += 1
                q = {"poem": p.get("poem", False), "s": ss}
                if p.get("who"):
                    w = p["who"]; t = tr.get("who", {}).get(w, [w, w])
                    q["who"] = {"fr": w[:1].upper() + w[1:], "en": t[0], "pt": t[1]}
                paras.append(q)
            cid = name.split("__")[1]
            out_dir = os.path.join(app, "data", "books", bid)
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, cid + ".js"), "w", encoding="utf-8") as f:
                f.write("BULLES_LOAD(" + json.dumps({"ep": bid + "/" + cid, "part": "text", "paras": paras},
                                                     ensure_ascii=False, separators=(",", ":")) + ");\n")
            words = sum(len(s.split()) for s in flat)
            lvl = CH_LEVEL.get(name, meta["level"])
            chapters.append({"id": cid, "title": tr["title"], "level": lvl, "levelWhy": meta["why"],
                             "sentences": len(flat), "words": words, "minutes": max(2, round(words / 120))})
        if not chapters:
            continue
        total = len(glob.glob(os.path.join(work, "seg", bid + "__*.json")))
        e = {"id": bid, "kind": "book", "lang": "fr", "langs": ["fr", "en", "pt"], "title": meta["title"],
             "author": meta["author"], "year": meta["year"], "blurb": meta["blurb"], "unit": meta["unit"],
             "color": meta["color"], "level": level_range([c["level"] for c in chapters]),
             "source": meta["source"], "sourceName": meta["sourceName"], "license": "Public domain",
             "translations": "English and Portuguese translations made with Claude for Bulles.",
             "chapters": chapters, "total": total}
        if meta.get("translator"):
            e["translator"] = meta["translator"]
        entries.append(e)
    return entries


def merge_into_library(app, entries):
    p = os.path.join(app, "data", "library.js")
    src = open(p, encoding="utf-8").read()
    lib = json.loads(src[src.index("(") + 1:src.rindex(")")])
    keep = [b for b in lib.get("books", []) if b["id"] not in {e["id"] for e in entries}]
    lib["books"] = keep + entries
    with open(p, "w", encoding="utf-8") as f:
        f.write("BULLES_LIBRARY_LOAD(" + json.dumps(lib, ensure_ascii=False, separators=(",", ":")) + ");\n")
    return lib


if __name__ == "__main__":
    work, app = sys.argv[1], sys.argv[2]
    entries = build(work, app)
    lib = merge_into_library(app, entries)
    for b in lib["books"]:
        print(b["id"], b["level"], len(b["chapters"]), "/", b.get("total", len(b["chapters"])), b.get("unit", "tales"))
