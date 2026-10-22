"""LZG from upstream; YLL equations from Yao, Liu, Lin (1999), Table I.

YLLF08 is optimized in its original negative-objective form. Both raw f and
f+418.9829*D are stored; equivalence of the paper's positive metric is unverified.
YLLF07 contains U[0,1) observation noise. It must not be verified by a fresh draw.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Relation'))
from pymoo.core.problem import Problem
from problem.single.LZG import LZG01,LZG02,LZG03,LZG04

class YLL(Problem):
    def __init__(self,index,n_var=20):
        self.index=index
        bounds={1:100,2:10,3:100,4:100,5:30,6:100,7:1.28,8:500,9:5.12,12:50,13:50}
        super().__init__(n_var=n_var,n_obj=1,xl=-bounds[index],xu=bounds[index])
    def _evaluate(self,x,out,*args,**kwargs):
        i=self.index;d=x.shape[1]
        if i==1:f=np.sum(x*x,axis=1)
        elif i==2:f=np.sum(abs(x),axis=1)+np.prod(abs(x),axis=1)
        elif i==3:f=np.sum(np.cumsum(x,axis=1)**2,axis=1)
        elif i==4:f=np.max(abs(x),axis=1)
        elif i==5:f=np.sum(100*(x[:,1:]-x[:,:-1]**2)**2+(x[:,:-1]-1)**2,axis=1)
        elif i==6:f=np.sum(np.floor(x+.5)**2,axis=1)
        elif i==7:f=np.sum(np.arange(1,d+1)*x**4,axis=1)+np.random.random(len(x))
        elif i==8:f=-np.sum(x*np.sin(np.sqrt(abs(x))),axis=1)
        elif i==9:f=np.sum(x*x-10*np.cos(2*np.pi*x)+10,axis=1)
        elif i==12:
            y=1+(x+1)/4
            f=np.pi/d*(10*np.sin(np.pi*y[:,0])**2+np.sum((y[:,:-1]-1)**2*(1+10*np.sin(np.pi*y[:,1:])**2),axis=1)+(y[:,-1]-1)**2)+np.sum(100*np.maximum(abs(x)-10,0)**4,axis=1)
        elif i==13:
            f=.1*(np.sin(3*np.pi*x[:,0])**2+np.sum((x[:,:-1]-1)**2*(1+np.sin(3*np.pi*x[:,1:])**2),axis=1)+(x[:,-1]-1)**2*(1+np.sin(2*np.pi*x[:,-1])**2))+np.sum(100*np.maximum(abs(x)-5,0)**4,axis=1)
        out['F']=f

def get_problem(name):
    return [LZG01,LZG02,LZG03,LZG04][int(name[-2:])-1](n_var=20) if name.startswith('LZG') else YLL(int(name[-2:]))
