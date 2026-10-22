"""Regenerate honest partial/final reports from completed formal results only."""
import csv,html,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import mannwhitneyu,rankdata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from prepare import TABLES,PROBLEMS,snapshot
BASE=Path(__file__).resolve().parent;OUT=BASE/'results'
OUT.mkdir(exist_ok=True)
scope=json.loads((BASE/'active_scope.json').read_text())
PROBLEMS=scope['problems']
EXPECTED_CELLS=len(TABLES)*4*len(PROBLEMS)
EXPECTED_RUNS=EXPECTED_CELLS*30
def csvwrite(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
reference_path=BASE/'paper_reference.csv'
refs=list(csv.DictReader(reference_path.open(encoding='utf-8-sig'))) if reference_path.exists() else []
reference={(r['table'],r['method'],r['problem']):float(r['paper_mean']) for r in refs}
runs=[json.loads(p.read_text()) for p in OUT.glob('T*_s??.json')]
runs=[r for r in runs if r['problem'] in PROBLEMS]
groups=defaultdict(list)
for r in runs:groups[(r['table'],r['method'],r['problem'])].append(r)
csvwrite(OUT/'runs.csv',[{k:v for k,v in r.items() if k not in ['best_x','history','verification']} for r in runs])
rows=[];lookup={}
for table,(_,operator,_) in TABLES.items():
    for problem in PROBLEMS:
        for method in ['BASE','FLS','FVS','CVS']:
            group=groups[(table,method,problem)];v=np.array([r['comparison_value'] for r in group]);raw=np.array([r['best_f'] for r in group])
            paper=reference.get((table,method,problem));uncertain=problem=='YLLF08'
            s=dict(table=table,operator=operator,method=method,problem=problem,n=len(v),expected_n=30,
                   mean=float(v.mean()) if len(v) else None,std=float(v.std(ddof=1)) if len(v)>1 else None,
                   median=float(np.median(v)) if len(v) else None,raw_mean=float(raw.mean()) if len(v) else None,
                   minimum=float(v.min()) if len(v) else None,maximum=float(v.max()) if len(v) else None,
                   paper_mean=paper,difference_percent=100*(v.mean()/paper-1) if len(v) and not uncertain and paper is not None and paper!=0 else None,
                   metric_note='provisional shifted error; paper convention unconfirmed' if uncertain else 'objective value',
                   local_rank=None,improvement_over_local_base_percent=None,local_rank_sum_p=None,local_sign='')
            rows.append(s);lookup[(table,method,problem)]=s
        local=[lookup[(table,m,problem)] for m in ['BASE','FLS','FVS','CVS']]
        if all(s['n']==30 for s in local):
            ranks=rankdata([s['mean'] for s in local])
            baseline=np.array([r['best_f'] for r in groups[(table,'BASE',problem)]])
            for rank,s in zip(ranks,local):
                s['local_rank']=float(rank)
                if s['method']=='BASE':continue
                ours=np.array([r['best_f'] for r in groups[(table,s['method'],problem)]])
                pv=float(mannwhitneyu(ours,baseline,alternative='two-sided',method='asymptotic').pvalue)
                s['local_rank_sum_p']=pv
                s['local_sign']='+' if pv<.05 and ours.mean()<baseline.mean() else ('-' if pv<.05 else 'approximately equal')
                if not uncertain:s['improvement_over_local_base_percent']=100*(1-s['mean']/local[0]['mean']) if local[0]['mean'] else None
csvwrite(OUT/'summary_comparison.csv',rows)
for table in TABLES:csvwrite(OUT/f'table_{table}.csv',[s for s in rows if s['table']==table])
failures=[p for p in OUT.glob('*.error.txt') if any('_'+name+'_' in p.name for name in PROBLEMS)];complete=sum(s['n']==30 for s in rows)
integrity=json.loads((BASE/'upstream_hashes_before.json').read_text())==snapshot()
audit={'successful_runs':len(runs),'expected_runs':EXPECTED_RUNS,'complete_cells':complete,'expected_cells':EXPECTED_CELLS,
       'failed_logs':len(failures),'search_fe':sum(r['actual_n_evals'] for r in runs),
       'post_run_verification_fe':sum(r['verification']['extra_evaluations'] for r in runs),
       'upstream_hashes_match':integrity,'all_expected_runs_complete':len(runs)==EXPECTED_RUNS and complete==EXPECTED_CELLS and not failures,
       'every_completed_run_exact_budget':all(r['actual_n_evals']==2000 for r in runs),
       'distinct_keys':len({(r['table'],r['method'],r['problem'],r['seed']) for r in runs})}
assert integrity and audit['every_completed_run_exact_budget'] and audit['distinct_keys']==len(runs)
(OUT/'audit.json').write_text(json.dumps(audit,indent=2))

fig,axes=plt.subplots(1,4,figsize=(13,7),constrained_layout=True)
for ax,(table,(_,operator,_)) in zip(axes,TABLES.items()):
    matrix=np.full((len(PROBLEMS),3),np.nan)
    for i,p in enumerate(PROBLEMS):
        b=lookup[(table,'BASE',p)]['mean']
        for j,m in enumerate(['FLS','FVS','CVS']):
            s=lookup[(table,m,p)]
            if s['n']==30 and b is not None and b>0 and s['mean']>0 and p!='YLLF08':matrix[i,j]=np.log10(s['mean']/b)
    cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#dddddd')
    im=ax.imshow(matrix,cmap=cmap,vmin=-1,vmax=1,aspect='auto')
    ax.set_xticks(range(3),['FLS','FVS','CVS']);ax.set_yticks(range(len(PROBLEMS)),PROBLEMS);ax.set_title(f'Table {table}: {operator}')
fig.colorbar(im,ax=axes,label='log10(local relation mean / local baseline mean)')
fig.suptitle('SPS LZG01-04 only / 20D / 2000 FE | blue: lower objective; red: higher\nGray: incomplete; 30 runs required per cell')
fig.savefig(OUT/'local_improvement.png',dpi=150);plt.close(fig)

def fmt(x):return '—' if x is None else f'{x:.5g}'
def table(headers,data):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in data)+'\n'
state='已完成全部預定執行' if audit['all_expected_runs_complete'] else '尚未全部完成：目前是進度報告'
text=f'''# SPS Table II–V 重現實驗報告

## 執行狀態：{state}

成功 {len(runs):,}/{EXPECTED_RUNS:,} 次；完整30次欄位 {complete}/{EXPECTED_CELLS}；失敗紀錄 {len(failures)}。成功搜尋共 {audit['search_fe']:,} FE，另有 {audit['post_run_verification_fe']:,} 次事後驗算。作者原始檔SHA256一致：{integrity}。SAS依要求省略。

## 實驗內容

SPS框架、20維、族群50、每次2000次真實評估；GA/EDA/DE/CoDE各比較基準與FLS/FVS/CVS。依使用者最新要求，只做4個作者LZG問題，每組種子1–30，共1920次。所有YLLF已排除，既有YLLF結果僅保留歷史紀錄，不計入本報告。這是Table II–V中LZG四列的重現，不是原表所有問題的完整重現。先前試跑及validation_pilot均不混入。

作者原始碼保持不變；正式程式繼承作者CompositeDE/RCPS_CoDE的迴圈與環境選擇，外部接入算子、XGBoost關係模型與隨機同分處理。這是可追溯的部分重建，不能稱為作者未公開實驗腳本的逐行複製。

## 必須揭露的限制

- CoDE文件為current-to-rand，原码為current-to-best。本輪在外部依文件覆寫第三算子；不可與先前原碼試跑混合。
- GA完整入口未公開，使用pymoo的GA.mating預設與文件SBX/PM參數；GA/EDA/DE基準倍率1、輔助版本倍率3，是本輪明示的組裝解讀。
- CVS cutoff=0.3、EDA cheap local search的Pb/Pc=0.2、XGBoost未指定參數沿用原碼／套件預設。
- 本輪只比較原文的LZG四列，不能據此推論原文全部15題的總體排名。YLL相關公式與尺度疑義不影響本輪四題數據。
- 合併模型推論沿用第一版實作；並行執行用時不是硬體效能比較。

## 如何讀表

每格為「本次mean ± 樣本std；n」。值越低越好。std描述不同種子的波動，不是平均誤差，也不是信賴區間。本交接包不附論文均值或舊實驗數據，因此預設只呈現本機生成結果。CSV中的paper_mean及difference_percent空白代表未提供論文參考值，不是0。可選的paper_reference.csv若提供對應table、method、problem、paper_mean欄位，才會計算論文差異率。

差異率=(本次mean−論文mean)/論文mean×100%；正值代表本次较高。相對本輪基準改善率=(baseline−relation)/baseline×100%。後者不是節省時間或FE的百分比。不同題目不能用原始值直接平均排名。

每列方法排名與原文排名分開。CSV的local_rank_sum_p是本輪30次對本輪基準的雙尾Mann–Whitney/Wilcoxon rank-sum漸近檢定，含ties校正、alpha=0.05，未做多重比較校正，僅探索性結果；沒有作者逐次數據，不能檢定本次是否顯著優於作者。

![本輪關係預選相對基準](results/local_improvement.png)

'''
for t,(_,operator,_) in TABLES.items():
    data=[]
    for p in PROBLEMS:
        values=[]
        for m in ['BASE','FLS','FVS','CVS']:
            s=lookup[(t,m,p)];values.append(f"{fmt(s['mean'])} ± {fmt(s['std'])}; n={s['n']}"+(f"; 論文 {fmt(s['paper_mean'])}" if s['paper_mean'] is not None else ''))
        data.append([p+'*' if p=='YLLF08' else p]+values)
    text+=f'## Table {t}：{operator}\n\n'+table(['問題','BASE','FLS','FVS','CVS'],data)+'\n'
    observations=[]
    for m in ['FLS','FVS','CVS']:
        comparable=[p for p in PROBLEMS if p!='YLLF08' and lookup[(t,m,p)]['n']==30 and lookup[(t,'BASE',p)]['n']==30]
        wins=sum(lookup[(t,m,p)]['mean']<lookup[(t,'BASE',p)]['mean'] for p in comparable)
        if comparable:observations.append(f'{m}在{len(comparable)}個已完成且尺度確定的題目中，有{wins}題平均低於本輪基準')
    text+=('；'.join(observations)+'。這是均值觀察，不等於全部都有顯著差異。' if observations else '各組尚未完成30次，暫不彙總正式勝出題數或統計檢定；上表可供檢視目前均值與波動。')+'\n\n'
text+='''## 檔案\n\nresults/table_II.csv至table_V.csv為本機統計結果；runs.csv為逐次摘要；audit.json為完成度與來源完整性核對；results/status.json為批次進度。未完成或失敗不填0，不換種子補數。\n'''
(BASE/'meeting_report.md').write_text(text,encoding='utf-8')
parts=[];lines=text.splitlines();i=0
while i<len(lines):
    line=lines[i]
    if line.startswith('| '):
        group=[]
        while i<len(lines) and lines[i].startswith('| '):group.append(lines[i]);i+=1
        parts.append('<div class="scroll"><table>')
        for j,row in enumerate(group):
            if j==1:continue
            tag='th' if j==0 else 'td';parts.append('<tr>'+''.join(f'<{tag}>{html.escape(c.strip())}</{tag}>' for c in row.strip('|').split('|'))+'</tr>')
        parts.append('</table></div>');continue
    if line.startswith('!['):parts.append('<img src="'+line.split('](')[1][:-1]+'">')
    elif line.startswith('## '):parts.append('<h2>'+html.escape(line[3:])+'</h2>')
    elif line.startswith('# '):parts.append('<h1>'+html.escape(line[2:])+'</h1>')
    elif line:parts.append('<p>'+html.escape(line)+'</p>')
    i+=1
(BASE/'meeting_report.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>SPS Table II–V</title><style>body{font:16px/1.8 "Microsoft JhengHei",sans-serif;max-width:1400px;margin:32px auto;padding:0 24px;color:#193046}h2{margin-top:35px;border-bottom:2px solid #238b84}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #cdd7dc;padding:8px}th{background:#e6f2f1}img{max-width:100%}</style>'+''.join(parts)+'</html>',encoding='utf-8')
print(json.dumps(audit,indent=2))
