"""Prepare LZG-only jobs and verify the vendored source without Git or PDFs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
TABLES={'II':('SPS','GA',2000),'III':('SPS','EDA',2000),'IV':('SPS','DE',2000),'V':('SPS','CoDE',2000)}
PROBLEMS=['LZG01','LZG02','LZG03','LZG04']

def snapshot():
    manifest=json.loads((ROOT/'vendor_manifest.json').read_text(encoding='utf-8'))
    folder=ROOT/'Relation'
    files=[p for p in folder.rglob('*') if p.is_file() and not any(x in {'.git','__pycache__'} for x in p.relative_to(folder).parts) and p.suffix not in {'.pyc','.pyo'} and p.name!='.DS_Store']
    actual={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in files}
    expected=manifest['files']
    if actual!=expected:
        changed=sorted(k for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k))
        raise RuntimeError('Bundled Relation files differ from vendor_manifest.json: '+', '.join(changed))
    return {'Relation':actual}

if __name__=='__main__':
    current=snapshot()
    path=OUT/'upstream_hashes_before.json'
    if path.exists():
        if json.loads(path.read_text())!=current:
            raise RuntimeError('Source differs from this experiment snapshot; use a separate experiment directory.')
    else:path.write_text(json.dumps(current,indent=2))
    scope=json.loads((OUT/'active_scope.json').read_text(encoding='utf-8'))
    if scope['problems']!=PROBLEMS:
        raise ValueError('This handoff reproduces LZG01-04 only.')
    plan=[dict(table=t,framework=f,operator=o,method=m,problem=p,seed=s,budget=b,dimension=20)
          for s in range(1,31) for p in PROBLEMS for t,(f,o,b) in TABLES.items()
          for m in ['BASE','FLS','FVS','CVS']]
    (OUT/'plan.json').write_text(json.dumps(plan,indent=2))
    print(f'{len(plan)} planned runs; {sum(j["budget"] for j in plan):,} search FE. No PDF or Git required.')
