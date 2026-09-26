"""Build small per-concept payloads from the existing public source data."""
import json, gzip
from pathlib import Path
from collections import defaultdict
root=Path(__file__).resolve().parents[1]/'web/data'
graph=json.loads((root/'graph.json').read_text())
exercises=json.loads((root/'exercises.json').read_text())
by_id=defaultdict(list)
for ex in exercises['exercises']: by_id[ex['concept_id']].append(ex)
output=root/'concepts'; output.mkdir(exist_ok=True)
for node in graph['nodes']:
    (output/(node['id']+'.json')).write_text(json.dumps({'node':node,'exercises':by_id[node['id']]},ensure_ascii=False,separators=(',',':')))
(root/'exercises.json.gz').write_bytes(gzip.compress((root/'exercises.json').read_bytes(),mtime=0))
print(f"built {len(graph['nodes'])} concept payloads")

blocked=set(json.loads((root/'quality_flags.json').read_text()).get('blocked_concept_ids',[]))
pool=[e for e in exercises['exercises'] if e['concept_id'] not in blocked and e['type']=='multiple_choice' and e.get('answer') in ['A','B','C','D'] and len(e.get('options',[]))==4]
(root/'selftest_pool.json').write_text(json.dumps({'exercises':pool},ensure_ascii=False,separators=(',',':')))
print(f"built {len(pool)} self-test questions")

(root/'graph.json.gz').write_bytes(gzip.compress((root/'graph.json').read_bytes(),mtime=0))
