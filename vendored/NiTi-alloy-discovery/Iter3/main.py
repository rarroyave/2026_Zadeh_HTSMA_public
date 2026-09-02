# -*- coding: utf-8 -*-
"""

@author: Danial Khatamsaz dkhatamsaz@gmail.com

HTMDEC second year design framework with 5 objectives

The order of elements
Ni	Ti	Cu	Hf	Zr	Pd	Co
"""

import numpy as np
import pandas as pd
from pyDOE import *
from copy import deepcopy
from gpModel import gp_model
from sklearn.preprocessing import normalize
import timeit
from sklearn_extra.cluster import KMedoids
from scipy.stats import norm
from multiobjective import EHVI, Pareto_finder, HV_Calc
import timeit
import random
from multiprocessing import Pool
import multiprocessing
from joblib import Parallel, delayed
from reificationFusion import reification
# from priors import o1_prior, o2_prior, o3_prior


""""
Objectives:​

    Minimizing Hysteresis​

    Maximize enthalpy​

    Maximizing Transformation Strain​

Target constraint:​

    Ms > 200 C
"""

iteration=1
N_dim=7
N_obj=3
# N_test=10 # candidates in single fidelity or test in multi-fidelity
# N_training=16 # number of initial training data
# N_prior=2000
Batch_size=29 # use more than 1 for batch BO
N_GP=1000; # if batch BO
# goal = np.ones([1,N_obj]) ## maximizing all objectives
# ref=np.zeros([1,N_obj]) ## reference point
goal = np.array([[0,1,1]])
ref = np.array([[70,0,0]])

# normalizing constants to ensure all objectives are in the same order of magnitude
nz1=4
nz2=2
nz3=1

normal = [nz1,nz2,nz3]

def sigmoid(x):
    return 1 / (1 + np.exp(-2.2*(x-9)))


## load length-scales and design space

# Upper bound is [0.3020    0.1900    0.1600    0.2500    0.2500    0.2500    0.0500]
# Lower bound is [0.0020    0.0020    0.01    0.01    0.01    0.01    0.01]
lhp=pd.DataFrame(pd.read_csv('lhp.csv', header=None)).to_numpy()

feasibles=pd.DataFrame(pd.read_csv('feasibles.csv', header=None)).to_numpy()/100
# infeasibles=pd.DataFrame(pd.read_csv('infeasibles.csv', header=None)).to_numpy()
# p_infeasibles=pd.DataFrame(pd.read_csv('probs.csv', header=None)).to_numpy()

# all_probs = np.concatenate((np.ones([feasibles.shape[0]]),p_infeasibles.reshape(-1)))
# all_space = np.concatenate((feasibles,infeasibles),axis=0)

all_probs = np.ones([feasibles.shape[0]])
all_space = feasibles


## This is the file that contains Batch_size*iter number of compositions that are tested
## This may be different than each source input as they may have less points available
tested_alloys=pd.DataFrame(pd.read_csv('tested_alloys.csv', header=None)).to_numpy()/100

## indices of samples lacking at least 1 objective value
## These should be excluded from ground truth data before Pareto front and hypervolume calculations
o1_incomplete_alloys =[]
o2_incomplete_alloys =[40,42,43,45,49,50]
o3_incomplete_alloys = [22,10,11,29,32,33,45,47,49]

## samples that violated a constraint
violators = [0,1,5,8,21,26] ## only indice 5 exists in the new feasible space

#other bad samples found in secondary screening
# other_bads  = pd.DataFrame(pd.read_csv('other_bad_samples.csv', header=None)).to_numpy()

## Ensure already tested samples are excluded from the search space
zz=[]
for ii in range(tested_alloys.shape[0]):
    ind=np.where((tested_alloys[ii] == all_space).all(1))[0]
    if len(ind.tolist())>0:
        zz.append(ind.tolist()[0])
    
# for ii in range(other_bads.shape[0]):
#     ind=np.where((other_bads[ii] == all_space).all(1))[0][0]
#     zz.append(ind)

space = np.delete(all_space,zz,0)
probs = np.delete(all_probs,zz,0)


## Load data here ######## (inputs, outputs, noises)

# first objective data: Minimizing Hysteresis​
o1_GT_x = np.delete(tested_alloys,violators+o1_incomplete_alloys,0)

o1_tested_y=pd.DataFrame(pd.read_csv('o1_GT_y.csv', header=None)).to_numpy()/nz1
o1_GT_y=np.delete(o1_tested_y,violators+o1_incomplete_alloys,0)

# o1_GT_sd=pd.DataFrame(pd.read_csv('o1_GT_sd.csv', header=None)).to_numpy()/nz1
# o1_GT_sd=np.delete(o1_GT_sd,violators,0)


# second objective data:  Maximize enthalpy​
o2_GT_x = np.delete(tested_alloys,violators+o2_incomplete_alloys,0)

o2_tested_y=pd.DataFrame(pd.read_csv('o2_GT_y.csv', header=None)).to_numpy()/nz2
o2_GT_y=np.delete(o2_tested_y,violators+o2_incomplete_alloys,0)

# o2_GT_sd=pd.DataFrame(pd.read_csv('o2_GT_sd.csv', header=None)).to_numpy()/nz2
# o2_GT_sd=np.delete(o2_GT_sd,violators,0)


# third objective data:Maximize Transformation Strain
o3_GT_x = np.delete(tested_alloys,violators+o3_incomplete_alloys,0)

o3_tested_y=pd.DataFrame(pd.read_csv('o3_GT_y.csv', header=None)).to_numpy()/nz3
o3_GT_y=np.delete(o3_tested_y,violators+o3_incomplete_alloys,0)

# o3_GT_sd=pd.DataFrame(pd.read_csv('o3_GT_sd.csv', header=None)).to_numpy()/nz3
# o3_GT_sd=np.delete(o3_GT_sd,violators,0)


##########################


#####load prior data here if any ######


#### if prior models are different:

## which models have prior?
prior_existence = [[True],[True],[True]]

## prior models if any (put GP.predict_mean as a function if prior is a GP)
# priors_models = [[o1_prior],[o2_prior],[o3_prior]]

## query training data from priors and keep in this prior list
priors_values = [[[]],[[]],[[]]]

hys_prior_tested=pd.DataFrame(pd.read_csv('hys_tested.csv', header=None)).to_numpy().reshape(-1)/nz1
ent_prior_tested=pd.DataFrame(pd.read_csv('ent_tested.csv', header=None)).to_numpy().reshape(-1)/nz2
TS_prior_tested=pd.DataFrame(pd.read_csv('TS_tested.csv', header=None)).to_numpy().reshape(-1)/nz3



priors_values = [[np.delete(hys_prior_tested,violators+o1_incomplete_alloys,0)],[np.delete(ent_prior_tested,violators+o2_incomplete_alloys,0)],[np.delete(TS_prior_tested,violators+o3_incomplete_alloys,0)]]

# priors_values = [[[]],[[]],[[]]]
# ## if input to all models
# inputs = [[o1_GT_x],[o2_GT_x],[o3_GT_x]]

# for j in range(len(prior_existence)):
#     for jj in range(len(prior_existence[j])):
#         if prior_existence[j][jj]:
#             priors_values[j][jj]=priors_models[j][jj](inputs[j][jj])/normal[j]
#         else:
#             priors_values[j][jj]=np.zeros([inputs[j][jj].shape[0]])
            

incomplete_alloys_list = o1_incomplete_alloys+o2_incomplete_alloys+o3_incomplete_alloys+violators
incomplete_alloys = list(set(incomplete_alloys_list))
y1_temp = np.delete(o1_tested_y,incomplete_alloys,0)
y2_temp = np.delete(o2_tested_y,incomplete_alloys,0)
y3_temp = np.delete(o3_tested_y,incomplete_alloys,0)

y=np.concatenate((y1_temp,y2_temp,y3_temp),axis=1)
train_y=y

y_pareto_curr,index=Pareto_finder(train_y,goal)
hv_curr = (HV_Calc(goal,ref,y_pareto_curr)).reshape(1,1)


candidates=[]
improvements=[]
indices=[]

x_test=space
p_test=probs
N_test=x_test.shape[0]


## load test priors here or query prior models

hys_prior_tests=pd.DataFrame(pd.read_csv('hys_prior.csv', header=None)).to_numpy().reshape(-1)/nz1
ent_prior_tests=pd.DataFrame(pd.read_csv('ent_prior.csv', header=None)).to_numpy().reshape(-1)/nz2
TS_prior_tests=pd.DataFrame(pd.read_csv('TS_prior.csv', header=None)).to_numpy().reshape(-1)/nz3

hys_prior_tests = np.delete(hys_prior_tests,zz,0)
ent_prior_tests = np.delete(ent_prior_tests,zz,0)
TS_prior_tests = np.delete(TS_prior_tests,zz,0)

test_priors = [[hys_prior_tests],[ent_prior_tests],[TS_prior_tests]]

# test_priors = [[[],[]],[[]],[[]],[[]],[[]]]

# for j in range(len(prior_existence)):
#     for jj in range(len(prior_existence[j])):
#         if prior_existence[j][jj]:
#             test_priors[j][jj]=priors_models[j][jj](x_test)/normal[j]
#         else:
#             test_priors[j][jj]=np.zeros([N_test])


for i in range(N_GP):
    pd.DataFrame(np.array(i).reshape(1,1)).to_csv("current_GP.csv", header=None, index=None)
                
    
    ##### if prior==True for a model, condition the GP on data-priors
    
    GP_o1_GT=gp_model(o1_GT_x, o1_GT_y.reshape(o1_GT_x.shape[0])-priors_values[0][0], lhp[i], (np.max(o1_GT_y)*0.625)**2, np.mean(o1_GT_y)*0.001, N_dim, 'SE' , mean=0)
    o1 = [GP_o1_GT]
    
    GP_o2_GT=gp_model(o2_GT_x, o2_GT_y.reshape(o2_GT_x.shape[0])-priors_values[1][0], lhp[i], (np.max(o2_GT_y)*0.625)**2, np.mean(o2_GT_y)*0.001, N_dim, 'SE' , mean=0)
    o2 = [GP_o2_GT]
    
    GP_o3_GT=gp_model(o3_GT_x, o3_GT_y.reshape(o3_GT_x.shape[0])-priors_values[2][0], lhp[i], (np.max(o3_GT_y)*0.625)**2, np.mean(o3_GT_y)*0.001, N_dim, 'SE' , mean=0)
    o3 = [GP_o3_GT]
    
    models = [o1,o2,o3]
    
    fused_means=[]
    fused_vars=[]
    fused_sigs=[]
    
    ### if prior==False, then test_priors is vector of zeros
    
    for j in range(N_obj):
        if len(models[j])==1:
            y_t,var_t = models[j][0].predict_var(x_test)
            fused_means.append(deepcopy(y_t)+test_priors[j][0])
            fused_vars.append(deepcopy(var_t))
        else:
            y_t=[]
            var_t=[]
            for z in range(len(models[j])):
                y_temp,var_temp = models[j][z].predict_var(x_test)
                y_t.append(deepcopy(y_temp)+test_priors[j][z])
                var_t.append(deepcopy(var_temp))
            for k in range(1,len(models[j])):
                var_t[k] = var_t[k] + (y_t[0]-y_t[k])**2
            m,v=reification(y_t,var_t)
            fused_means.append(deepcopy(m))
            fused_vars.append(deepcopy(v))
    
    fused_means=np.transpose(np.array(fused_means))
    fused_vars=np.transpose(np.array(fused_vars))
    fused_sigs=abs(fused_vars)**0.5
                
    
    n_jobs=multiprocessing.cpu_count()
    def calc(ii):
        e = EHVI(fused_means[ii].reshape(1,-1),fused_sigs[ii].reshape(1,-1),goal,ref,y_pareto_curr)
        return e

    Ehvi=Parallel(n_jobs)(delayed(calc)(np.array([jj])) for jj in range(N_test))
    
    ### neutral acquisition function
    Ehvi=np.array(Ehvi)
    
    ### constraint-aware and risk-aware acquisition function
    # risk_aware_prob = test_prob**10
    Ehvi = p_test*Ehvi.ravel()
        
    x_star=np.argmax(Ehvi)
    candidates.append(deepcopy(x_test[x_star]))
    improvements.append(deepcopy(Ehvi[x_star]))
    indices.append(x_star)
    
    
kmedoids = KMedoids(n_clusters=Batch_size, method='pam', max_iter=500, random_state=0).fit(candidates)
x_query=kmedoids.cluster_centers_


pd.DataFrame(np.array(indices).reshape(-1,1)).to_csv("all_candidates_indices.csv", header=None, index=None)
pd.DataFrame(x_query).to_csv("x_query.csv", header=None, index=None)
pd.DataFrame(np.array(candidates)).to_csv("all_candidates.csv", header=None, index=None)
pd.DataFrame((np.array(improvements)).reshape(N_GP,1)).to_csv("all_improvements.csv", header=None, index=None)


medoid_indices = kmedoids.medoid_indices_.astype('int')
pd.DataFrame(np.array(medoid_indices).reshape(-1,1)).to_csv("x_query_indices.csv", header=None, index=None)











