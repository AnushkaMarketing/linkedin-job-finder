"""Inspectable retrieval and requirement reasoning. No external model or CV transfer."""
import math
import re
from collections import Counter
from datetime import datetime, timezone
from .ontology import extract_skills, relation, norm

STOP = set('a an the and or to of in for with on at by is are be as you your we our will have experience role work team required preferred'.split())


def tokens(text):
    return [t for t in norm(text).split() if len(t) > 1 and t not in STOP]


def retrieve(jobs, profile, preferences, limit=2500):
    """BM25 with title boosting and explicit ontology expansion. Retrieval, not qualification."""
    query = tokens(' '.join(preferences.roles or profile.preferred_roles or [profile.current_role]) + ' ' + ' '.join(profile.skills))
    documents = [tokens((j.title+' ') * 3 + j.description[:12000] + ' ' + ' '.join(j.skills)) for j in jobs]
    counts = [Counter(d) for d in documents]
    frequency = Counter(t for d in documents for t in set(d))
    average = sum(map(len, documents))/max(1,len(documents)) or 1
    def score(index):
        counts_i = counts[index]; length = len(documents[index]); value = 0
        for term in set(query):
            tf = counts_i[term]
            idf = math.log(1+(len(jobs)-frequency[term]+.5)/(frequency[term]+.5))
            value += idf * tf * 2.2 / (tf + 1.2*(.25+.75*length/average))
        return value
    order = sorted(range(len(jobs)),key=lambda i:(-score(i),i))[:limit]
    return [jobs[i] for i in order]


def requirements(job):
    groups=[]; section='mentioned'; exempt=set()
    for sentence in re.split(r'[\n;]+',job.description):
        sentence=sentence.strip(' •-')
        if not sentence: continue
        # Clause-level polarity: a negated skill is not counted as a requirement.
        if re.search(r'not required|not necessary|no (?:prior )?.*?experience (?:needed|required)|no need',sentence,re.I):
            exempt.update(extract_skills(sentence))
            continue
        if re.search(r'preferred|nice.to.have|bonus|desirable|optional',sentence,re.I):section='preferred'
        elif re.search(r'required|requirements|essential|must.have|must have',sentence,re.I):section='required'
        elif re.search(r'responsibilities|what you.ll do|duties|about us|benefits',sentence,re.I):section='mentioned'
        for clause in re.split(r'\s+and\s+',sentence,flags=re.I):
            skills=extract_skills(clause)
            if not skills:continue
            alternatives=bool(re.search(r'\bor\b|either',clause,re.I)) and len(skills)>1
            for group in ([skills] if alternatives else [[s] for s in skills]):
                groups.append({'skills':group,'importance':section,'operator':'any' if alternatives else 'all','evidence':sentence[:800]})
    for requirement in job.requirements:
        for skill in extract_skills(requirement):groups.append({'skills':[skill],'importance':'required','operator':'all','evidence':requirement[:800]})
    if not groups:
        groups=[{'skills':[s],'importance':'mentioned','operator':'all','evidence':'Structured source skill'} for s in job.skills if s not in exempt]
    unique={}
    priority={'required':3,'mentioned':2,'preferred':1}
    for group in groups:
        key=tuple(sorted(group['skills']))
        if key not in unique or priority[group['importance']]>priority[unique[key]['importance']]:unique[key]=group
    return list(unique.values())


def skill_assessment(job,profile):
    groups=requirements(job); strengths=[];gaps=[];related=[];weighted=total=0
    owned=profile.skills+profile.technical_skills+profile.soft_skills
    for group in groups:
        best=max((relation(owned,s) for s in group['skills']),default=(0,'Unknown',''))
        score,label,via=best
        group.update(score=round(score*100),relationship=label,via=via)
        weight={'required':3,'mentioned':2,'preferred':1}[group['importance']]
        weighted+=score*weight;total+=weight
        skill=' or '.join(group['skills'])
        if score==1:strengths.append(f'{skill}: exact skill match'+(' (one alternative is sufficient)' if group['operator']=='any' else ''))
        elif score:related.append(f'{skill}: {label.lower()} via {via}; not an exact match')
        else:gaps.append(f"{skill}: {group['importance']}, not in profile")
    required=[g for g in groups if g['importance']=='required']
    missing=[g for g in required if not g['score']]
    return {'groups':groups,'score':round(100*weighted/total,1) if total else None,'strengths':strengths,'gaps':gaps,'related':related,
            'required_count':len(required),'required_missing':len(missing),'required_missing_skills':[' or '.join(g['skills']) for g in missing]}


def evidence_review(job,assessment,coverage):
    flags=[]; questions=[]
    if assessment['required_missing']:flags.append(f"{assessment['required_missing']} must-have requirement groups have no profile evidence")
    if coverage<50:flags.append('Limited profile/listing evidence; compare the missing fields before trusting the score')
    if not job.posted_date:questions.append('When was this vacancy first posted, and is it still accepting applications?')
    else:
        try:
            posted=datetime.fromisoformat(job.posted_date.replace('Z','+00:00'))
            if not posted.tzinfo:posted=posted.replace(tzinfo=timezone.utc)
            days=(datetime.now(timezone.utc)-posted).days
            if days>60:flags.append(f'Listing was posted {days} days ago; vacancy may need reconfirmation')
        except ValueError:questions.append('Posting date could not be interpreted; confirm vacancy freshness.')
    if not job.coordinates and job.work_mode!='remote':questions.append('What is the exact reporting office?')
    if job.salary.minimum is None and job.salary.maximum is None:questions.append('What is the approved compensation range?')
    if re.search(r'(?:pay|payment|fee).{0,35}(?:interview|registration|training|apply)',job.description,re.I):
        flags.append('Possible candidate-payment language: inspect the original context; this alone is not a fraud determination')
    return {'version':'2.0','requirements':assessment['groups'],'required_count':assessment['required_count'],
        'required_missing':assessment['required_missing'],'flags':flags,'questions':questions,'priority_adjustment':0,
        'method':'Weighted requirements, explicit alternatives, coverage-aware factors; feedback adjustment bounded to four points'}


def shortlist_insights(results):
    gaps=Counter(s for row in results for g in row.intelligence.get('requirements',[]) if g['importance']=='required' and not g['score'] for s in [' or '.join(g['skills'])])
    return {'gap_opportunities':[{'skill':s,'jobs':n} for s,n in gaps.most_common(5)],
            'needs_office_confirmation':sum(r.distance_km is None and r.job.work_mode!='remote' for r in results),
            'low_evidence':sum(r.coverage<50 for r in results),'employers':len({norm(r.job.company) for r in results}),
            'note':'Patterns in this shortlist only, not a labour-market forecast. Add skills only after gaining real experience.'}
