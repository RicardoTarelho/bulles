# Rewrites the books paragraph of a Bulles README from data/library.js
import json, re, sys
readme, libjs = sys.argv[1], sys.argv[2]
src = open(libjs, encoding='utf-8').read()
lib = json.loads(src[src.index('(')+1: src.rindex(')')])
books = lib['books']
NAMES = {"fr": "French", "en": "English", "pt": "Portuguese", "es": "Spanish"}
every = [l for l in NAMES if all(l in b["langs"] for b in books)]
lst = lambda ls: ", ".join(NAMES[l] for l in ls[:-1]) + " or " + NAMES[ls[-1]]
lines = ["**Books**, from public-domain French editions on Wikisource. Read any of them in " + lst(every) + ",",
         "and tap a sentence to see it in another of those languages. The French is the original;",
         "the other languages were translated sentence by sentence with Claude for Bulles.", ""]
for b in books:
    unit = b.get('unit') or 'tales'
    n = len(b['chapters']); tot = b.get('total', n)
    count = f"{n} {unit}" if n == tot else f"{n} of {tot} {unit} so far"
    tr = f", French translation by {b['translator']}" if b.get('translator') else ""
    names = ", ".join(c['title']['en'] if isinstance(c['title'],dict) else c['title'] for c in b['chapters']) if n <= 6 else ""
    lines.append(f"- *{b['title']['fr'] if isinstance(b['title'],dict) else b['title']}* by {b['author']} ({b['year']}{tr}), {b['level']}: {count}" + (f" ({names})" if names else "") + ".")
block = "\n".join(lines) + "\n"
t = open(readme, encoding='utf-8').read()
t = re.sub(r"\*\*(Contes de Perrault|Books)\*\*.*?\n\n(?=Every comic)", block + "\n", t, flags=re.S)
t = t.replace("`tools/build_book.py` builds the book from its text and translations;",
  "`tools/build_book.py` builds the Perrault tales and `tools/build_books.py` the other books, from the texts and translations in `tools/book-batch/`;")
open(readme, 'w', encoding='utf-8').write(t)
