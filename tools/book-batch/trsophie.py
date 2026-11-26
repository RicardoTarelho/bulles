# Write tr/sophie__NN.json from en/pt lists in tr/parts/sophie__NN.*.json, adding all speaker labels.
import json, sys, glob
n=sys.argv[1]; name=f'sophie__{n}'
who=json.load(open('who_sophie.json'))
seg=json.load(open(f'seg/{name}.json'))
parts=sorted(glob.glob(f'tr/parts/{name}.*.json'))
out=json.load(open(parts[0]))
for p in parts[1:]:
    d=json.load(open(p)); out['en']+=d['en']; out['pt']+=d['pt']
labs={p['who'] for p in seg['paras'] if p.get('who')}
missing=[l for l in labs if l not in who]
out['who']={l:who[l] for l in labs if l in who}
n_fr=sum(len(p['s']) for p in seg['paras'])
json.dump(out,open(f'tr/{name}.json','w'),ensure_ascii=False,indent=0)
print(name,'fr',n_fr,'en',len(out['en']),'pt',len(out['pt']),'missing who',missing)
