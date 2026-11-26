# Move a closing » that starts a sentence back to the end of the previous sentence.
import json, sys
for name in sys.argv[1:]:
    p=f'seg/{name}.json'; d=json.load(open(p)); n=0
    for para in d['paras']:
        s=para['s']
        for i in range(1,len(s)):
            if s[i].startswith('» '):
                s[i-1]=s[i-1].rstrip()+' »'; s[i]=s[i][2:]; n+=1
    json.dump(d,open(p,'w'),ensure_ascii=False,indent=1)
    lines=[f"# {d.get('title')}"]; i=0
    for para in d['paras']:
        lines.append('¶')
        for x in para['s']: lines.append(f"{i}\t{x}"); i+=1
    open(f'seg/{name}.txt','w').write('\n'.join(lines)+'\n'); print(name,n)
