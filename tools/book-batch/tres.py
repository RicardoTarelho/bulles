# Assemble tr_es/<book>__<chap>.json from parts tr_es/parts/<book>__<chap>.*.json and check the count.
import json, sys, glob
b, c = sys.argv[1], sys.argv[2]; name = f'{b}__{c}'
parts = sorted(glob.glob(f'/home/claude/books2/tr_es/parts/{name}.*.json'))
out = json.load(open(parts[0]))
if b == 'sophie': out['who'] = {**json.load(open('/home/claude/books2/who_es_sophie.json')), **out.get('who', {})}
for p in parts[1:]:
    d = json.load(open(p)); out['es'] += d['es']; out.setdefault('who', {}).update(d.get('who', {}))
s = open(f'/home/claude/w/data/books/{b}/{c}.js').read(); d = json.loads(s[s.index('(')+1:s.rindex(')')])
n = sum(len(p['s']) for p in d['paras']); labs = {p['who']['fr'] for p in d['paras'] if p.get('who')}
miss = [l for l in labs if l not in out.get('who', {}) and (l[:1].lower()+l[1:]) not in out.get('who', {})]
json.dump(out, open(f'/home/claude/books2/tr_es/{name}.json', 'w'), ensure_ascii=False, indent=0)
print(name, 'fr', n, 'es', len(out['es']), 'missing who', miss)
