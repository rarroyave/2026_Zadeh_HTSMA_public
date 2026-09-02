# -*- coding: utf-8 -*-
"""

@author: Danial
"""


"""
Based on Mrinalini analysis, points with 2% distance have 80% similarity
So, solving for the length scales results in l = 0.042 in each dimension

Using 1 core and 50GB of memory:
Querying 1000 points takes 2 minutes
Querying 10000 points takes 5 minutes
Querying 50000 points takes 18 minutes

"""

import numpy as np
import pandas as pd
from pyDOE import *
from copy import deepcopy
from gpModel import gp_model

### All GP prediction larger than 9.63 are picked corresponding to 80% feasibility

def sigmoid(x):
    return 1 / (1 + np.exp(-2.2*(x-9)))

N_dim=7

feasibles=pd.DataFrame(pd.read_csv('feasibles.csv', header=None)).to_numpy()/100
space=pd.DataFrame(pd.read_csv('all_space.csv', header=None)).to_numpy()/100
tested_alloys=pd.DataFrame(pd.read_csv('tested_alloys.csv', header=None)).to_numpy()/100

#violators = [0,1,5,8,21,26] out of these only indice 5 is in the updated feasible
violators = [5]

bad_samples = tested_alloys[violators,:]

zz=[]
for ii in range(bad_samples.shape[0]):
    ind=np.where((bad_samples[ii] == feasibles).all(1))[0][0]
    zz.append(ind)



# x=np.delete(feasibles,zz,0)
# y=np.ones([x.shape[0]])*10
x=feasibles
y=np.ones([x.shape[0]])*10
y[zz]=0
sn=np.ones([x.shape[0]])*0.1
lhp=np.ones([N_dim])*0.00425 ## based on kernel calculations of 80% similarity in 2% resolution
GPC=gp_model(x, y, lhp, 1, 0.1, N_dim, 'SE' , mean=0)

p = np.zeros([space.shape[0]])

for i in range(381):
    pd.DataFrame(np.array(i).reshape(1,1)).to_csv("current_loop.csv", header=None, index=None)
    x_test = space[i*10000:(i+1)*10000,:]
    y_t,var_t = GPC.predict_var(x_test)
    p[i*10000:(i+1)*10000]=deepcopy(y_t)
    

pd.DataFrame(np.array(p).reshape(3812408,1)).to_csv("p.csv", header=None, index=None)
 
x_test = space[3810000:3812408,:]
y_t,var_t = GPC.predict_var(x_test)
p[3810000:3812408]=deepcopy(y_t)

pd.DataFrame(np.array(p).reshape(3812408,1)).to_csv("p.csv", header=None, index=None)


zz=[]
for ii in range(feasibles.shape[0]):
    ind=np.where((feasibles[ii] == space).all(1))[0][0]
    zz.append(ind)
    
infeasibles=np.delete(space,zz,0)
p_infeasibles = np.delete(p,zz,0)
p_infeasibles[p_infeasibles>10]=10

infs = infeasibles[p_infeasibles.reshape(-1)>9.63,:] ## corresponding to 80%
p_infs = p_infeasibles[p_infeasibles>9.63]

probs = sigmoid(p_infs)

pd.DataFrame(infs).to_csv("infeasibles.csv", header=None, index=None)
pd.DataFrame(np.array(probs).reshape(-1,1)).to_csv("probs.csv", header=None, index=None)