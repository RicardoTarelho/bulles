# Merge sentences wrongly split after the abbreviation "M." (Monsieur) and rewrite the .txt view.
import json, sys, re
for name in sys.argv[1:]:
    p=f'seg/{name}.json'; d=json.load(open(p)); n=0
    for para in d['paras']:
        out=[]
        for s in para['s']:
            if out and re.search(r'(^|\s)M\.$', out[-1]): out[-1]+=' '+s; n+=1
            else: out.append(s)
        para['s']=out
    json.dump(d,open(p,'w'),ensure_ascii=False,indent=1)
    lines=[f"# {d.get('title')}"]; i=0
    for para in d['paras']:
        lines.append('¶'+(f" [{para['who']}]" if para.get('who') else ''))
        for s in para['s']: lines.append(f"{i}\t{s}"); i+=1
    open(f'seg/{name}.txt','w').write('\n'.join(lines)+'\n')
    print(name,'merged',n,'total',i)
