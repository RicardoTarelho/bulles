import json, sys, glob
name = sys.argv[1]
parts = sorted(glob.glob(f'tr/parts/{name}.*.json'))
out = json.load(open(parts[0]))
for p in parts[1:]:
    d = json.load(open(p))
    out['en'] += d['en']; out['pt'] += d['pt']
    out.setdefault('who', {}).update(d.get('who', {}))
json.dump(out, open(f'tr/{name}.json', 'w'), ensure_ascii=False, indent=0)
print(name, len(out['en']), len(out['pt']))
