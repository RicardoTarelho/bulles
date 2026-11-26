# Print the French sentences of a built chapter, numbered, with speaker labels, for translating.
import json, sys
b, c = sys.argv[1], sys.argv[2]
s = open(f'/home/claude/w/data/books/{b}/{c}.js').read(); d = json.loads(s[s.index('(')+1:s.rindex(')')])
i = 0; who = []
for p in d['paras']:
    if p.get('who'): who.append(p['who']['fr']); print(f"  [{p['who']['fr']}]")
    for x in p['s']: print(f"{i}\t{x['fr']}"); i += 1
print('WHO', sorted(set(who)))
