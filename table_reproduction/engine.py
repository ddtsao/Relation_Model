"""SPS integration reusing authors' CompositeDE / RCPS_CoDE framework.

No changes to any upstream file. Reproduction and relation model adapters bind
existing components; the only selection override randomizes exact score ties
as required by the supplement. See protocol.md for unresolved equivalence.
"""
import copy,random,time
import numpy as np
from loguru import logger
from components import Generation,Relation,descending_random_ties
from problems import get_problem
from pymoo.core.population import Population
from pymoo.core.callback import Callback
from pymoo.optimize import minimize
from algorithm.base.composite_de import CompositeDE
from algorithm.saea.rcps import RCPS_CoDE

class ReproductionAdapter:
    def __init__(self,operator,problem,method):
        self.gen=Generation(operator,problem)
        self.trail_vectors_num=3 if operator=='CoDE' or method!='BASE' else 1
    def do(self,problem,pop,n_offsprings,**kwargs):
        X=self.gen.candidates(pop,t=self.trail_vectors_num).reshape(-1,20)
        assert X.shape==(50*self.trail_vectors_num,20)
        return Population.new(X=X)

class ModelAdapter:
    def __init__(self,method):self.method=method;self.fit_count=0
    def fit(self,X,F):self.current=Relation(self.method,X,F);self.fit_count+=1
    def predict(self,X):return self.current.scores(X)
    def score_groups(self,groups):
        if self.method!='FLS':
            return self.predict(groups.reshape(-1,20)).reshape(len(groups),groups.shape[1])
        # XGB inference is row-independent. Reuse the author's league scoring
        # against the exact probabilities from one batched inference call.
        pairs=np.array([np.r_[a,b] for g in groups for a in g for b in g])
        probs=self.current.trainer.predict(pairs,return_prob=True)
        scores=[];t=groups.shape[1]
        class ProbabilityView:
            def __init__(self,expected,values):self.expected=expected;self.values=values
            def predict(self,X,return_prob=False):
                assert return_prob and np.array_equal(X,self.expected)
                return self.values
        for i,g in enumerate(groups):
            scorer=copy.copy(self.current.user)
            sl=slice(i*t*t,(i+1)*t*t)
            scorer.trainer=ProbabilityView(pairs[sl],probs[sl])
            scores.append(scorer.do(g))
        return np.asarray(scores)

class PaperSPS(RCPS_CoDE):
    def __init__(self,method,reproduction):
        super().__init__(pop_size=50,reproduction=reproduction)
        self.model=ModelAdapter(method)
    def preselection_by_relation(self,trials):
        # Same per-parent candidate grouping as upstream rcps.py.
        t=self.reproduction.trail_vectors_num
        groups=[trials[i:i+t] for i in range(0,len(trials),t)]
        scores=self.model.score_groups(np.asarray([g.get('X') for g in groups]))
        indices=[i*t+descending_random_ties(s)[0] for i,s in enumerate(scores)]
        return trials[np.asarray(indices)]

def execute(job,progress=None):
    assert job['framework']=='SPS','SAS explicitly out of current scope'
    logger.remove();random.seed(job['seed']);np.random.seed(job['seed'])
    p=get_problem(job['problem']);budget=job['budget']
    reproduction=ReproductionAdapter(job['operator'],p,job['method'])
    algorithm=CompositeDE(pop_size=50,reproduction=reproduction) if job['method']=='BASE' else PaperSPS(job['method'],reproduction)
    class Recorder(Callback):
        def __init__(self):super().__init__();self.history=[]
        def notify(self,a):
            fe=int(a.evaluator.n_eval);best=float(a.opt.get('F').min())
            X=a.pop.get('X')
            assert fe<=budget and np.isfinite(X).all() and np.all(X>=p.xl) and np.all(X<=p.xu)
            self.history.append({'n_evals':fe,'best_f':best})
            if progress:progress(fe,best)
    started=time.perf_counter()
    res=minimize(p,algorithm,('n_evals',budget),seed=job['seed'],callback=Recorder(),verbose=False)
    elapsed=time.perf_counter()-started
    x=np.asarray(res.X);f=float(np.asarray(res.F).item());calls=int(res.algorithm.evaluator.n_eval)
    history=res.algorithm.callback.history
    assert calls==budget and np.isfinite(f)
    assert all(b['best_f']<=a['best_f']+1e-10 for a,b in zip(history,history[1:]))
    if job['problem']=='YLLF07':
        noise=f-float(np.sum(np.arange(1,21)*x**4));assert -1e-10<=noise<1+1e-10
        verification={'kind':'stored observation noise in [0,1)','noise':noise,'extra_evaluations':0}
    else:
        check=float(p.evaluate(x).item());assert np.isclose(check,f,rtol=1e-12,atol=1e-9)
        verification={'kind':'objective recomputation','value':check,'extra_evaluations':1}
    return dict(**job,engine_version='source-framework-v1',actual_n_evals=calls,best_f=f,
                comparison_value=f+418.9829*20 if job['problem']=='YLLF08' else f,
                comparison_metric='f - (-418.9829*D), provisional paper convention' if job['problem']=='YLLF08' else 'observed best objective',
                best_x=x.tolist(),elapsed_seconds=elapsed,training_calls=0 if job['method']=='BASE' else res.algorithm.model.fit_count,
                history=history,verification=verification)
