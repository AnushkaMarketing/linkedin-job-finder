import re
from .models import Profile, Job, Preferences, Factor, RankedJob
from .ontology import extract_skills, relation, role_similarity, seniority, norm, ROLE_FAMILIES, role_family
from .geo import location_fit
from .intelligence import skill_assessment, evidence_review

WEIGHTS = {'Skills': 30, 'Experience': 16, 'Role': 16, 'Seniority': 7, 'Industry': 6, 'Education': 5, 'Certifications': 3, 'Trajectory': 9, 'Projects': 8}


def search_plan(profile: Profile, preferences: Preferences) -> dict:
    requested = preferences.roles or profile.preferred_roles or ([profile.current_role] if profile.current_role else [])
    expansions = list(requested)
    for title in requested:
        level = seniority(title)
        for equivalent in ROLE_FAMILIES.get(role_family(title), []):
            if seniority(equivalent) == level and equivalent not in expansions: expansions.append(equivalent)
    return {'roles': expansions[:20], 'requested_roles': requested, 'strategies': [
        {'name': 'Exact roles', 'queries': requested},
        {'name': 'Equivalent titles', 'queries': expansions[len(requested):]},
        {'name': 'Skill context', 'queries': profile.skills[:6]},
        {'name': 'Industry preferences', 'queries': preferences.industries or profile.industries},
        {'name': 'Employer boards and permitted sources', 'queries': ['Configured boards', 'Company JobPosting pages', 'Manual imports']}
    ]}


def analyze_requirements(job: Job) -> dict:
    sections = {k: [] for k in ['required', 'preferred', 'responsibilities', 'qualifications', 'experience', 'technology', 'inferred_signals']}
    section = 'responsibilities'
    for line in re.split(r'[\n;]+', job.description):
        line = line.strip(' •-')
        if not line: continue
        if re.search(r'preferred|nice to have|bonus|desirable', line, re.I): section = 'preferred'
        elif re.search(r'requirements|must have|must-have|required|essential', line, re.I): section = 'required'
        elif re.search(r'qualifications|education', line, re.I): section = 'qualifications'
        elif re.search(r'responsibilities|what you.ll do|duties', line, re.I): section = 'responsibilities'
        sections[section].append(line[:800])
        if re.search(r'\byears?\b', line, re.I): sections['experience'].append(line[:800])
    sections['required'] += job.requirements
    sections['technology'] = job.skills
    for label, expression in [('Leadership expectations', r'lead a team|manage a team|direct reports'), ('Client-facing work', r'client-facing|client meetings'), ('Travel', r'\btravel\b'), ('Shift work', r'night shift|rotating shifts'), ('Relocation', r'\brelocat'), ('Startup environment', r'startup|early.stage')]:
        if match := re.search(expression, job.description, re.I):
            sections['inferred_signals'].append({'signal': label, 'evidence': match[0], 'kind': 'inferred'})
    return sections


def mean(factors: list[Factor]) -> float | None:
    known = [f for f in factors if f.score is not None]
    return round(sum(f.score * f.weight for f in known) / sum(f.weight for f in known), 1) if known else None


def match_job(profile: Profile, job: Job, preferences: Preferences) -> RankedJob:
    analysis = analyze_requirements(job)
    required = extract_skills('\n'.join(analysis['required']))
    preferred = extract_skills('\n'.join(analysis['preferred']))
    criteria = required or job.skills
    assessment = skill_assessment(job, profile)
    strengths, gaps, related = assessment['strengths'], assessment['gaps'], assessment['related']
    factors = [Factor(name='Skills', score=assessment['score'], weight=WEIGHTS['Skills'], explanation='Required groups carry 3x, mentioned 2x, preferred 1x weight. Explicit alternatives need one matching skill; negated requirements excluded.')]
    years = profile.experience_years
    exp = None
    if years is not None and job.experience_min is not None:
        exp = 100 if years >= job.experience_min else max(0, 100 - (job.experience_min - years) * 30)
        if job.experience_max is not None and years > job.experience_max + 2: exp = 75
        if exp == 100: strengths.append('Experience meets the stated minimum')
        elif years < job.experience_min: gaps.append(f'Experience: {job.experience_min:g}+ years requested; profile has {years:g}')
    factors.append(Factor(name='Experience', score=exp, weight=WEIGHTS['Experience'], explanation=f'Profile {years if years is not None else "unknown"}; listing minimum {job.experience_min if job.experience_min is not None else "unknown"} years'))
    targets = preferences.roles or profile.preferred_roles or ([profile.current_role] if profile.current_role else [])
    role = max((role_similarity(job.title, title) for title in targets), default=None)
    factors.append(Factor(name='Role', score=round(role * 100, 1) if role is not None else None, weight=WEIGHTS['Role'], explanation='Canonical title families and token overlap against selected roles'))
    level = profile.seniority or seniority(profile.current_role)
    factors.append(Factor(name='Seniority', score=(100 if level == job.seniority else 30) if level and job.seniority else None, weight=WEIGHTS['Seniority'], explanation=f'Profile: {level or "unknown"}; listing: {job.seniority or "unknown"}'))
    for name, owned, needed in [('Industry', profile.industries, [job.industry] if job.industry else []), ('Education', profile.education, job.education), ('Certifications', profile.certifications, job.certifications)]:
        value = (100 * sum(any(norm(n) in norm(o) for o in owned) for n in needed) / len(needed)) if needed and owned else None
        factors.append(Factor(name=name, score=value, weight=WEIGHTS[name], explanation='Compared explicit structured fields; missing information is unscored'))
    trajectory = max((role_similarity(job.title, r) for r in profile.previous_roles), default=None)
    factors.append(Factor(name='Trajectory', score=round(trajectory * 100, 1) if trajectory is not None else None, weight=WEIGHTS['Trajectory'], explanation='Continuity with previous roles; this is an inference, not a qualification'))
    project_skills = extract_skills('\n'.join(profile.projects))
    project_fit = sum(relation(project_skills, skill)[0] for skill in criteria) / len(criteria) * 100 if project_skills and criteria else None
    factors.append(Factor(name='Projects', score=round(project_fit, 1) if project_fit is not None else None, weight=WEIGHTS['Projects'], explanation='Relevance of technologies explicitly mentioned in your projects; not proof of professional experience'))
    eligible, km, loc = location_fit(job, preferences)
    preference_factors = [Factor(name='Location', score=(100 if eligible else 0) if job.work_mode == 'remote' or (job.coordinates and job.coordinates.precision == 'office' and preferences.origin) else None, weight=35, explanation=loc),
        Factor(name='Work mode', score=(100 if job.work_mode in preferences.work_modes else 0) if job.work_mode != 'unknown' and preferences.work_modes else None, weight=25, explanation=job.work_mode)]
    salary = None
    if preferences.salary.minimum is not None and job.salary.maximum is not None and preferences.salary.currency.upper() == job.salary.currency.upper() and preferences.salary.period == job.salary.period:
        salary = 100 if job.salary.maximum >= preferences.salary.minimum else 0
    preference_factors += [Factor(name='Salary', score=salary, weight=20, explanation='Comparable currency and period required; no currency conversion or invented compensation'),
        Factor(name='Employment', score=(100 if norm(job.employment_type) in [norm(t) for t in preferences.employment_types] else 0) if job.employment_type and preferences.employment_types else None, weight=10, explanation=job.employment_type or 'Not stated'),
        Factor(name='Preferred industry', score=(100 if norm(job.industry) in [norm(i) for i in preferences.industries] else 0) if job.industry and preferences.industries else None, weight=10, explanation=job.industry or 'Not stated')]
    cv, pref = mean(factors), mean(preference_factors)
    coverage = sum(f.weight for f in factors if f.score is not None) / 100
    if not (profile.skills or profile.technical_skills or profile.soft_skills or profile.current_role or profile.previous_roles or profile.projects or profile.education or profile.experience_years is not None):
        cv, coverage = None, 0
        gaps.append('Add and review your profile before interpreting CV fit; a target-role preference is not CV evidence.')
    readiness = [f'Highlight your {x.split(":")[0]} work with a real example.' for x in strengths[:2]]
    readiness += ['Address missing requirements honestly; add experience only if you have it.'] if gaps else []
    if job.remote_restrictions: readiness.append('Confirm remote location and work-authorization eligibility: ' + job.remote_restrictions)
    if 'Unknown' in loc or 'unverified' in loc: readiness.append('Confirm the actual reporting office before applying.')
    if preferred: readiness.append('Preferred skills to review: ' + ', '.join(preferred))
    if project_fit and project_fit > 0: readiness.append('Include a real project example that demonstrates the matched technologies; distinguish project work from employment.')
    return RankedJob(job=job, cv_fit=cv, preference_fit=pref, priority=0, coverage=round(coverage * 100), distance_km=km, location_status=loc,
        factors=factors + preference_factors, strengths=strengths, gaps=gaps, related=related, analysis=analysis, readiness=readiness, intelligence=evidence_review(job, assessment, round(coverage*100)))


def rank(results: list[RankedJob]) -> list[RankedJob]:
    for row in results:
        # Evidence coverage caps the confidence of high scores computed from sparse fields.
        row.priority = round((.65 * (row.cv_fit or 0) * (.5 + row.coverage / 200) + .2 * (row.preference_fit or 0) + .15 * row.verification.confidence * 100), 1)
        required=row.intelligence.get('required_count',0)
        missing=row.intelligence.get('required_missing',0)
        # A high contextual score cannot hide a majority of unsubstantiated must-haves.
        cap=55 if required and missing/required >= .5 else 100
        row.intelligence['priority_cap']=cap
        row.intelligence['priority_cap_reason']='At least half the explicit must-have groups lack profile evidence' if cap<100 else ''
        row.priority=min(row.priority,cap)
    return sorted(results, key=lambda r: (-r.priority, -r.coverage, r.job.title, r.job.job_id))
