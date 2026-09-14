# import libraries
import numpy as np
import pandas as pd
from CBFV import composition
from functools import reduce
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import catboost as cb

# cleaning the raw data

df = pd.read_csv("raw_data.csv", engine='python')
df = df[['Ag(at%)', 'Al(at%)', 'Au(at%)', 'B(at%)', 'Bi(at%)', 'Ce(at%)', 'Co(at%)', 'Cr(at%)', 'Cu(at%)', 'Dy(at%)', 'Er(at%)', 'Fe(at%)', 'Gd(at%)', 'Hf(at%)', 'In(at%)', 'La(at%)', 'Mn(at%)', 'Mo(at%)', 'Nb(at%)', 'Nd(at%)', 'Ni(at%)', 'Pb(at%)', 'Pd(at%)', 'Pr(at%)', 'Pt(at%)', 'Re(at%)', 'Rh(at%)', 'Sb(at%)', 'Sc(at%)', 'Si(at%)', 'Sn(at%)', 'Ta(at%)', 'Te(at%)', 'Ti(at%)', 'Tl(at%)', 'V(at%)', 'W(at%)', 'Y(at%)', 'Zr(at%)', 'Processing_BPHT_Temp', 'Processing_BPHT_Time', 'Processing_Rolling_Temp',	'Processing_HR_Red', 'Processing_CR_Red', 'Processing_Extrusion_Temp', 'Processing_Extrusion_Area_Reduction(%)', 'Processing_APHT_Temp', 'Processing_APHT_Time', 'Processing_APHT_Method', 'Processing_FinalHT_Temp', 'Processing_FinalHT_Time', 'Processing_FinalHT_Method', 'SME_Mf', 'SME_Ms', 'SME_As', 'SME_Af']]

new_df = df[ df.SME_Mf.notna() & df.SME_Ms.notna() & df.SME_As.notna() & df.SME_Af.notna()].drop_duplicates().reset_index(drop=True)
new_df.columns = [x.replace('(at%)', '') for x in new_df.columns]
new_df['Processing_CR_Red'] = new_df['Processing_CR_Red'].fillna(0)
new_df = new_df[(new_df.SME_Af > new_df.SME_Ms) & (new_df.SME_Af > new_df.SME_As) & (new_df.SME_Ms > new_df.SME_Mf) &(new_df.SME_As > new_df.SME_Mf)].reset_index(drop=True)
new_df.loc[:,'Total'] = new_df[new_df.iloc[:,:39].columns.to_list()].sum(axis=1)
new_df = new_df[(new_df.Total < 100.5) & (new_df.Total > 99.5)].reset_index(drop=True)
new_df = new_df.iloc[: , :-1]   

# Convert element list to empirical formula
all_formula_lst = []
dictio = new_df.iloc[:,0:39].to_dict('split')
for i in range(len(dictio['data'])):
    elements_lst = []
    fractions_lst = []
    for j in range(39):
        if dictio['data'][i][j] != 0:
            elements_lst.append(dictio['columns'][j])
            fractions_lst.append(dictio['data'][i][j])
    alloy_dict = dict(zip(elements_lst, fractions_lst))
        
    all_formula_lst.append(alloy_dict)

def iszero(a):
    return abs(a)<1e-9

def gcd(a,b):
    if iszero(b):
        return a
    return gcd(b,a%b)

def gcdarr(arr):
    return reduce(gcd,arr)

def correctratios(arr):
    arrgcd = gcdarr(arr)
    return [round(a/arrgcd) for a in arr]

def from_dict_list(dl):
    res=[0]*len(dl)
    for ii,i in enumerate(dl):
        vals_cor=correctratios(i.values())
        st=''
        for j,k in zip(i.keys(),vals_cor):
            st=st+j+str(k)
        res[ii]=st
    
    return res
        
lista_form=from_dict_list(all_formula_lst)
formula_df =  pd.DataFrame(np.array(lista_form), columns=['formula'])
formula_df = pd.concat([formula_df, new_df.iloc[:,39:]], axis=1)

# Generating the categorical features
formula_df['family'] = formula_df.formula.replace('\d+', '', regex=True).replace("AlNiTiZr","NiTiZrAl").replace("NiRhTi","NiTiRh").replace("CuNiPdTi", "NiTiPdCu").replace("NiPdPtTi", "NiTiPdPt").replace("NbNiTiZr", "NiTiNbZr").replace("HfNiTiZr", "NiTiHfZr").replace("NiPdTaTi", "NiTiPdTa").replace("CuNiTi","NiTiCu").replace("NiPtTi","NiTiPt").replace("HfNiTi","NiTiHf").replace("AuCuNiTi", "NiTiCuAu").replace("AuNiTi", "NiTiAu").replace("BNiPdTi","NiTiPdB").replace("BNiTiZr","NiTiZrB").replace("CoCuNiTi","NiTiCuCo").replace("CoInMnNi","NiMnCoIn").replace("CoNiPdTi","NiTiPdCo").replace("CuFeHfNiTi","NiTiHfFeCu").replace("CuHfNiTi","NiTiHfCu").replace("CuHfNiTiZr","NiTiHfZrCu").replace("CuNbNiTi","NiTiCuNb").replace("CuNiTiZr","NiTiCuZr").replace("HfNiPdTi","NiTiPdHf").replace("NbNiTi","NiTiNb").replace("NiPdScTi","NiTiPdSc").replace("NiPdTi", "NiTiPd")

formula_df['niti_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTi" in x else "No")
formula_df['nitihf_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiHf" in x else ( "Yes" if "Ni" in x and "Ti" in x and "Hf" in x else "No"))
formula_df['nitipd_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiPd" in x else ( "Yes" if "Ni" in x and "Ti" in x and "Pd" in x else "No"))
formula_df['niticu_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiCu" in x else ( "Yes" if "Ni" in x and "Ti" in x and "Cu" in x else "No"))
formula_df['nitinb_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiNb" in x else ( "Yes" if "Ni" in x and "Ti" in x and "Nb" in x else "No"))
formula_df['nitizr_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiZr" in x else ( "Yes" if "Ni" in x and "Ti" in x and "Zr" in x else "No"))
formula_df['nitib_bas'] = formula_df.family.apply(lambda x: "Yes" if "NiTiB" in x else ( "Yes" if "Ni" in x and "Ti" in x and "B" in x else "No"))


# creating validation set and training/test set
X_val  = formula_df.groupby('formula').filter(lambda x : len(x)<2).reset_index(drop = True)
formula_df = formula_df.groupby('formula').filter(lambda x : len(x)>1).reset_index(drop = True)

# Generate composition features

y= formula_df[['SME_Ms', 'SME_Mf', 'SME_As', 'SME_Af']]
formula_df = formula_df.drop(columns=['SME_Ms', 'SME_As', 'SME_Af']).rename({'SME_Mf': 'target'}, axis=1)
X, _, _, _ = composition.generate_features(formula_df, elem_prop='jarvis', extend_features=True, sum_feat = True)
X

# Training ML model

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state =42)
dtrain = cb.Pool(X_train, label=y_train, cat_features = ['family', 'niti_bas','nitihf_bas','nitipd_bas','niticu_bas','nitinb_bas','nitizr_bas','nitib_bas'])
dvalid = cb.Pool(X_test, label=y_test, cat_features = ['family', 'niti_bas','nitihf_bas','nitipd_bas','niticu_bas','nitinb_bas','nitizr_bas','nitib_bas'])

params = {'learning_rate': 0.2092, 'depth': 6, 'l2_leaf_reg': 0.05992, 'bagging_temperature' : 0.5562,
          'loss_function': 'MultiRMSE',  'eval_metric': 'MultiRMSE', 'silent':True}

new_model = cb.CatBoostRegressor(**params)
new_model.fit(dtrain, eval_set=dvalid, use_best_model=True)

print('Training performance')
print('RMSE: {}'.format((np.sqrt(mean_squared_error(y_train, new_model.predict(X_train))))))
print('MAE: {}'.format(mean_absolute_error(y_train, new_model.predict(X_train))))
print('R2: {}'.format(r2_score(y_train, new_model.predict(X_train))))
print('Testing performance')
print('RMSE: {}'.format((np.sqrt(mean_squared_error(y_test, new_model.predict(X_test))))))
print('MAE: {}'.format(mean_absolute_error(y_test, new_model.predict(X_test))))
print('R2: {}'.format(r2_score(y_test, new_model.predict(X_test))))
