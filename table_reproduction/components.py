"""External implementations of Supplement Algorithms 1 and 3.

Upstream relation generators, scorers, XGB classifier, VWH reproduction, and
pymoo variation operators are imported, never patched. See protocol.md for
every implementation choice not determined by the supplementary material.
"""
import copy,random,sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Relation'))
from loguru import logger
from pymoo.core.population import Population
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.sampling.lhs import LHS
from pymoo.algorithms.soo.nonconvex.de import Variant
from pymoo.algorithms.soo.nonconvex.ga import FitnessSurvival,GA
from pymoo.operators.control import NoParameterControl
from algorithm.utils.edamodel import VWH
from algorithm.utils.reproduction import CoDE_Reproduction,VWH_Local_Reproduction,VWH_Local_Reproduction_unevaluate,check_boundary,get_random_index
from relation_model.component.generator import FitnessCriteriaGenerator,CategoryCriteriaGenerator
from relation_model.component.trainer import Trainer
from relation_model.component.user import LeagueScoringUser,FitnessCriteriaUser,CategoryCriteriaUser
from problems import get_problem

class PaperCoDE(CoDE_Reproduction):
    """Paper's current-to-rand/1; upstream opt1/opt2 and boundary repair reused."""
    def opt3(self,x_index,xs,lb,ub,x_best):
        inds=get_random_index(x_index,len(xs))
        F=self.parameter_pool[random.randint(0,len(self.parameter_pool)-1)][0]
        K=np.random.random()
        return check_boundary(xs[x_index]+K*(xs[inds[0]]-xs[x_index])+F*(xs[inds[1]]-xs[inds[2]]),lb,ub)

class Relation:
    def __init__(self,method,X,F):
        self.generator=CategoryCriteriaGenerator() if method=='CVS' else FitnessCriteriaGenerator()
        self.trainer=Trainer()
        # Resource limit only: no model hyperparameter tuned to paper outcomes.
        self.trainer.model.set_params(n_jobs=1)
        user={'FLS':LeagueScoringUser,'FVS':FitnessCriteriaUser,'CVS':CategoryCriteriaUser}[method]
        self.user=user(generator=self.generator,trainer=self.trainer)
        data=self.generator.do(X,F)
        self.trainer.do(data['RXs'],data['Rls'])
    def scores(self,X):return np.asarray(self.user.do(X)).ravel()

def descending_random_ties(scores):
    order=np.random.permutation(len(scores))
    return order[np.argsort(-np.asarray(scores)[order],kind='stable')]

class Generation:
    def __init__(self,operator,problem):
        self.operator=operator;self.problem=problem
        self.context=SimpleNamespace(pop_size=50)
        self.sbx=SBX(prob=.5,eta=15,n_offsprings=1)
        self.pm=PM(prob=.9,eta=20)
        self.ga=GA(pop_size=50,crossover=SBX(prob=.5,eta=15),mutation=PM(prob=.9,eta=20))
        self.de=Variant(selection='best',n_diffs=2,F=.5,crossover='bin',CR=.2,jitter=False,prob_mut=.1,control=NoParameterControl)
        self.code=PaperCoDE()
        self.eda=VWH(M=15)
        self.eda.init(D=20,LB=problem.xl.copy(),UB=problem.xu.copy())
        self.eda_plain=VWH_Local_Reproduction(eda=self.eda)
        self.eda_u=VWH_Local_Reproduction_unevaluate(eda=self.eda)
    def once(self,pop,U=None):
        p=self.problem;N=len(pop)
        if self.operator=='EDA':
            return (self.eda_plain.do(p,pop,N,algorithm=self.context) if U is None else self.eda_u.do(p,pop,N,algorithm=self.context,unevaluated_pop=U)).get('X')
        if self.operator=='CoDE':return self.code.do(p,pop,N).get('X').reshape(N,3,20)
        X=pop.get('X')
        pool=X if U is None else np.vstack([X,U])
        if self.operator=='GA':
            if U is None:
                return self.ga.mating.do(p,pop,N,algorithm=self.ga).get('X')
            parents=np.empty((N,2),dtype=int)
            parents[:,0]=np.arange(N)
            for i in range(N):parents[i,1]=np.random.choice(np.delete(np.arange(len(pool)),i))
            q=self.sbx.do(p,Population.new(X=pool),parents=parents)
            return self.pm.do(p,q).get('X')
        if U is None:
            FitnessSurvival().do(p,pop,n_survive=N)
            return self.de.do(p,pop,N,algorithm=self.context).get('X')
        # Same best/2/bin operator, with donor pool P union U. Best is evaluated.
        best=X[np.argmin(pop.get('F'))]
        donors=np.empty_like(X)
        for i in range(N):
            j=np.random.choice(np.delete(np.arange(len(pool)),i),4,replace=False)
            donors[i]=best+.5*(pool[j[0]]-pool[j[1]])+.5*(pool[j[2]]-pool[j[3]])
        from pymoo.operators.repair.bounds_repair import repair_random_init
        from pymoo.operators.crossover.binx import mut_binomial
        donors=repair_random_init(donors,np.tile(best,(N,1)),p.xl,p.xu)
        mask=mut_binomial(N,20,np.full(N,.2),at_least_once=True)
        trial=X.copy();trial[mask]=donors[mask]
        return self.de.mutation.do(p,Population.new(X=trial)).get('X')
    def candidates(self,pop,t=1,U=None):
        if self.operator=='CoDE':return self.once(pop,U)
        return np.stack([self.once(pop,U) for _ in range(t)],axis=1)


