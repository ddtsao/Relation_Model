"""Resumable CPU batch; original source untouched; no outcome-based seed selection."""
import argparse,concurrent.futures,datetime,gc,hashlib,importlib.metadata,json,os,sys,time,traceback
from pathlib import Path
BASE=Path(__file__).resolve().parent
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
os.environ['MPLCONFIGDIR']=str(BASE.parent/'tmp/matplotlib')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['PYTHONUTF8']='1'

def key(j):return f"T{j['table']}_{j['operator']}_{j['method']}_{j['problem']}_s{j['seed']:02d}"
def work(args):
    job,out=args;out=Path(out);name=key(job)
    from engine import execute
    def progress(fe,best):
        (out/(name+'.progress.json')).write_text(json.dumps({'fe':fe,'best':best,'time':time.time(),'pid':os.getpid()}))
    try:
        result=execute(job,progress)
        temp=out/(name+'.tmp');temp.write_text(json.dumps(result),encoding='utf-8');temp.replace(out/(name+'.json'))
        error=out/(name+'.error.txt')
        if error.exists():
            recovered=out/'recovered_errors';recovered.mkdir(exist_ok=True)
            error.replace(recovered/error.name)
        (out/(name+'.progress.json')).unlink(missing_ok=True)
        return name,True,result['elapsed_seconds']
    except Exception:
        (out/(name+'.error.txt')).write_text(traceback.format_exc(),encoding='utf-8')
        return name,False,0
    finally:
        gc.collect()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--seeds',type=int,default=30)
    parser.add_argument('--problems',nargs='*')
    parser.add_argument('--out',default='results')
    args=parser.parse_args()
    from prepare import snapshot
    before=json.loads((BASE/'upstream_hashes_before.json').read_text())
    assert before==snapshot()
    jobs=json.loads((BASE/'plan.json').read_text())
    scope=json.loads((BASE/'active_scope.json').read_text())
    jobs=[j for j in jobs if j['problem'] in scope['problems']]
    jobs=[j for j in jobs if j['seed']<=args.seeds and (not args.problems or j['problem'] in args.problems)]
    out=BASE/args.out;out.mkdir(exist_ok=True)
    hashes={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ['engine.py','components.py','problems.py']}
    manifest=out/'implementation.json'
    if manifest.exists():assert json.loads(manifest.read_text())['sha256']==hashes,'Implementation changed; use a fresh output directory'
    else:manifest.write_text(json.dumps({'sha256':hashes,'python':sys.version,'seed_policy':'1..30; no replacements','source_commit':'03c19d4280b38230e0852054922072f5aa6dcdf5'},indent=2))
    (out/'environment-lock.txt').write_text('\n'.join(sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())))
    pending=[j for j in jobs if not (out/(key(j)+'.json')).exists()]
    status={'requested':len(jobs),'already_completed':len(jobs)-len(pending),'completed_now':0,'failed_now':0,'workers':args.workers,'started':datetime.datetime.now().isoformat(),'scope':'SPS Tables II-V LZG01-04 only; all YLLF excluded; SAS deferred','problems':scope['problems']}
    (out/'status.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status),flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(work,(j,str(out))):j for j in pending}
        for future in concurrent.futures.as_completed(futures):
            name,ok,seconds=future.result()
            status['completed_now' if ok else 'failed_now']+=1
            status['updated']=datetime.datetime.now().isoformat()
            (out/'status.json').write_text(json.dumps(status,indent=2))
            print(f"{status['completed_now']+status['failed_now']}/{len(pending)} {'OK' if ok else 'FAILED'} {name} {seconds:.2f}s",flush=True)
    status['upstream_hashes_match']=before==snapshot();assert status['upstream_hashes_match']
    status['finished']=datetime.datetime.now().isoformat()
    (out/'status.json').write_text(json.dumps(status,indent=2))
    if args.out=='results':
        import subprocess
        subprocess.run([sys.executable,'-B',str(BASE/'analyze.py')],check=True,env=os.environ)
