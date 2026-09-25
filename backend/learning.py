"""Small local logistic preference model trained only on explicit relevance labels.

Not a hiring-success model. Cold-start guard, L2 regularization and bounded effects
protect the deterministic criteria. Names and protected attributes are excluded.
"""
import hashlib
import json
import math

FEATURES=('Skills','Experience','Role','Seniority','Industry','Projects','Location','Work mode','Salary')


def profile_key(profile):
    selected={k:getattr(profile,k) for k in ('skills','technical_skills','current_role','experience_years','preferred_roles')}
    return hashlib.sha256(json.dumps(selected,sort_keys=True).encode()).hexdigest()[:20]


def features(row):
    values={f.name:f.score for f in row.factors}
    # Center known factors, use zero for unknown and add evidence coverage.
    return [0 if values.get(k) is None else values[k]/50-1 for k in FEATURES]+[row.coverage/50-1]


def sigmoid(value): return 1/(1+math.exp(-max(-30,min(30,value))))


def train(labels):
    labels=labels[-300:]
    positive=sum(x['label']=='relevant' for x in labels);negative=len(labels)-positive
    if min(positive,negative)<3 or len(labels)<8:return {'ready':False,'labels':len(labels),'positive':positive,'negative':negative,'weights':[]}
    weights=[0.0]*(len(FEATURES)+1)
    # Full-batch deterministic gradient descent; balanced classes, L2 shrinkage.
    for _ in range(180):
        gradient=[0.0]*len(weights)
        for row in labels:
            y=int(row['label']=='relevant');x=row['features']
            error=sigmoid(sum(a*b for a,b in zip(weights,x)))-y
            balance=len(labels)/(2*(positive if y else negative))
            for i,value in enumerate(x):gradient[i]+=error*value*balance
        weights=[w-.12*(g/len(labels)+.12*w) for w,g in zip(weights,gradient)]
    return {'ready':True,'labels':len(labels),'positive':positive,'negative':negative,'weights':weights}


def personalized_rank(results,model):
    for row in results:
        adjustment=0
        if model['ready']:
            preference=sigmoid(sum(a*b for a,b in zip(model['weights'],features(row))))
            adjustment=round((preference-.5)*8,2)
        row.intelligence['priority_adjustment']=adjustment
        row.intelligence['feedback_labels']=model['labels']
        row.priority=round(max(0,min(row.intelligence.get('priority_cap',100),row.priority+adjustment)),1)
    return sorted(results,key=lambda r:(-r.priority,-r.coverage,r.job.title,r.job.job_id))
