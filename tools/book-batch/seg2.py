"""Segment the downloaded Wikisource texts into paragraphs and sentences.
Writes seg/<book>__<n>.json (one per tale/chapter) and seg/<book>__<n>.txt (numbered, for translating)."""
import json, os, re

books = json.load(open('books.json'))['books']
os.makedirs('seg', exist_ok=True)
SPLIT = re.compile(r'(?<=[.!?…»])\s+(?=[A-ZÀÂÉÈÊÎÔÛÇ—«])')


def sentences(text):
    out = []
    for s in SPLIT.split(text):
        s = s.strip()
        if not s:
            continue
        if len(s.split()) > 40:
            parts = re.split(r'(?<=[;:])\s+', s)
            buf = ''
            for p in parts:
                buf = (buf + ' ' + p).strip()
                if len(buf.split()) >= 12:
                    out.append(buf); buf = ''
            if buf:
                if out and len(buf.split()) < 6: out[-1] += ' ' + buf
                else: out.append(buf)
        else:
            out.append(s)
    # glue tiny fragments like "— Ah !" onto nothing; keep as is
    return out


def is_speaker(p):
    w = p.split()
    return len(w) <= 7 and p[:1].islower() and p.endswith('.') and not re.search(r'[!?«»—]', p)


def is_caps(line):
    letters = [c for c in line if c.isalpha()]
    return letters and sum(c.isupper() for c in letters) / len(letters) > 0.8


def clean(text, book):
    paras = [re.sub(r'[ \t ]+', ' ', p).strip() for p in re.split(r'\n\s*\n', text)]
    paras = [p for p in paras if p]
    title, out = None, []
    for i, p in enumerate(paras):
        line = p.replace('\n', ' ').strip()
        if line.startswith('↑'):  # footnotes
            continue
        if re.search(r'\(Page \d+\.\)', line):  # illustration captions
            continue
        if re.search(r'a paru dans (le|la|les) ', line) and len(line.split()) < 25:
            continue
        if not out and (is_caps(line) or re.fullmatch(r'[IVXLC]+\.?', line)):
            if not re.fullmatch(r'[IVXLC]+\.?', line):
                title = (title + ' ' if title else '') + line
            continue
        if not out and re.match(r'^À (M\.|Mme|Mlle|Madame|Monsieur|[A-Z])', line) and len(line.split()) <= 10:
            continue  # dedication
        if not out and re.fullmatch(r'\(?récit[^)]*\)?', line, re.I):
            continue
        out.append(line)
    # title cleanup: "LA CHÈVRE DE M. SEGUIN" etc.
    return title, out


index = {}
removed = []
for book, items in books.items():
    index[book] = []
    for n, r in enumerate(items, 1):
        title, paras = clean(r['text'], book)
        # merge page-break splits: a paragraph that doesn't end a sentence continues in the next one
        merged = []
        for p in paras:
            if merged and not re.search(r'[.!?…»:;)]$', merged[-1]) and not is_speaker(merged[-1]):
                merged[-1] += ' ' + p
            else:
                merged.append(p)
        segp, spk = [], None
        for p in merged:
            if is_speaker(p):
                spk = p.rstrip('.').strip(); continue
            item = {'poem': False, 's': sentences(p)}
            if spk: item['who'] = spk; spk = None
            segp.append(item)
        # remove illustration captions pasted inside other sentences (they repeat a sentence of the text)
        allS = [x for q in segp for x in q['s']]
        for q in segp:
            for k, x in enumerate(q['s']):
                for c in allS:
                    cc = c.rstrip(' ;:,')
                    if c is x or len(cc.split()) < 6: continue
                    cap = cc[0].upper() + cc[1:]
                    for form in (cap + '.', cap, cc):
                        if form in x and len(x) > len(form) + 10:
                            x = x.replace(form, ' ').replace('  ', ' ').strip(); break
                # short captions: "…un grand Les maçons travaillaient. bassin…" (caption repeats words of the text)
                def drop(m):
                    cap = m.group(1)
                    body = ' '.join(allS).lower()
                    core = cap.rstrip('.').lower()
                    if body.count(core) >= 2 or len(cap.split()) <= 6:
                        removed.append(cap); return ' '
                    return m.group(0)
                x = re.sub(r'(?<=[a-zàâéèêîôûçœ’,]) ([A-ZÀÉÈÊÎÔ][^.!?«»]{2,90}[a-zàâéèêîôûç]\.) (?=[a-zàâéèêîôûçœ])', drop, x)
                q['s'][k] = x
        flat = [s for p in segp for s in p['s']]
        name = f'{book}__{n:02d}'
        json.dump({'book': book, 'n': n, 'source': r.get('real') or r['title'], 'title': title, 'paras': segp},
                  open(f'seg/{name}.json', 'w'), ensure_ascii=False)
        with open(f'seg/{name}.txt', 'w') as f:
            f.write(f'# {title}\n')
            i = 0
            for p in segp:
                f.write('¶' + (' [' + p['who'] + ']' if p.get('who') else '') + '\n')
                for s in p['s']:
                    f.write(f'{i}\t{s}\n'); i += 1
        index[book].append((name, title, len(flat), sum(len(s.split()) for s in flat)))
print('captions removed:', removed)
for b, l in index.items():
    print(b, sum(x[2] for x in l), 'sentences', sum(x[3] for x in l), 'words')
    for x in l: print('   ', x)
