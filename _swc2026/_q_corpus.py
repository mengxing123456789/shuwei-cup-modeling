import json, collections
d = json.load(open(r'E:\数学建模\.mh\corpus.json', encoding='utf-8'))
recs = d['records']
print('n_records', len(recs), 'declared', d['count'])
print('fields', list(recs[0]))
kinds = collections.Counter(r.get('kind') for r in recs)
print('kinds', dict(kinds))
papers = [r for r in recs if r.get('kind') == 'paper']
print('n_papers', len(papers))
# id 字段
idf = [k for k in recs[0] if 'id' in k.lower()]
print('id fields', idf)
want = ['CSHUWEICUP2556821','B201952365','ASHUWEICUP2537139','ASHUWEICUP2518979']
for w in want:
    hits = []
    for r in papers:
        s = json.dumps({k: v for k, v in r.items() if k != 'text'}, ensure_ascii=False)
        if w.lower() in s.lower():
            hits.append(r.get(idf[0]) if idf else s[:60])
    print(w, '->', hits[:3])
