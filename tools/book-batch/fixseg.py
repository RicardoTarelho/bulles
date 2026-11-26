# usage: fixseg.py name 'old=>new' ...  (applies to seg/<name>.json and regenerates nothing else)
import json, sys
name=sys.argv[1]; pairs=[a.split('=>',1) for a in sys.argv[2:]]
p=f'seg/{name}.json'; d=json.load(open(p))
hit={o:0 for o,_ in pairs}
for para in d['paras']:
    out=[]
    for s in para['s']:
        for o,n in pairs:
            if o in s: hit[o]+=1; s=s.replace(o,n)
        out.append(s)
    para['s']=out
json.dump(d,open(p,'w'),ensure_ascii=False,indent=1)
print({k:v for k,v in hit.items()})
