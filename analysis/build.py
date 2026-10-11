"""Rebuild a typed SQLite evidence mart and query outputs using only committed inputs."""
from pathlib import Path
import csv, hashlib, json, sqlite3, sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/output'
sources={}
def record(path): sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
def read_json(path):
 record(path)
 return json.loads(path.read_text())
def read_csv(path):
 record(path)
 with path.open(newline='') as f:return list(csv.DictReader(f))

sys.path.insert(0,str(ROOT/'src'))
from evaldrift.benchmarks import resolution_table
record(ROOT/'src/evaldrift/benchmarks.py');record(ROOT/'src/evaldrift/power.py')
rows=[(r['benchmark'],r['items'],r['typical_accuracy'],r['min_detectable_effect'],r['items_needed_for_claim']) for r in resolution_table()]

OUT.mkdir(exist_ok=True)
db=sqlite3.connect(':memory:')
db.execute('CREATE TABLE observations (benchmark TEXT PRIMARY KEY,items INTEGER CHECK(items>0),accuracy REAL CHECK(accuracy BETWEEN 0 AND 1),mde REAL CHECK(mde>0),required INTEGER CHECK(required>0))')
db.executemany('INSERT INTO observations (benchmark,items,accuracy,mde,required) VALUES (?,?,?,?,?)',rows)
assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert db.execute('SELECT COUNT(*) FROM observations').fetchone()[0]==len(rows)>0
queries=(ROOT/'analysis/questions.sql').read_text().split(';')
outputs=[]
for i,query in enumerate(queries,1):
 if not query.strip():continue
 cursor=db.execute(query)
 path=OUT/f'query_{i}.csv'
 with path.open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow([d[0] for d in cursor.description]);writer.writerows(cursor.fetchall())
 outputs.append(path.name)
manifest={'project':'evaldrift','rows':len(rows),'scope':'Analytic planning at 2 percentage points, 80% power and 95% confidence under independent proportions. MDE is not observed significance.','input_sha256':sources,'query_sha256':hashlib.sha256((ROOT/'analysis/questions.sql').read_bytes()).hexdigest(),'outputs':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in outputs},'quality_checks':['SQL type and domain constraints','row-count reconciliation','SQLite integrity'],'external_services_required':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'project':'evaldrift','rows':len(rows),'outputs':outputs}))
