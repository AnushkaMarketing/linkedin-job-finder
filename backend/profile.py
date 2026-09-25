import re
from datetime import datetime
from .models import Profile, Evidence
from .ontology import extract_skills, seniority


def parse_profile(text: str) -> Profile:
    lines = [line.strip(' \t•-') for line in text.splitlines() if line.strip()]
    profile = Profile(skills=extract_skills(text), warnings=['Review extracted fields before saving. Missing fields remain unknown.'])
    if lines and len(lines[0]) < 90 and not re.search(r'@|https?://|\d{4}', lines[0]):
        profile.name = lines[0]
    years = re.search(r'(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience', text, re.I)
    if years:
        profile.experience_years = float(years[1])
    # Month-qualified employment intervals are unioned, never summed across overlaps.
    month = r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    intervals = []
    education_context = False
    for line in lines:
        if re.fullmatch(r'education|qualifications|certifications', line, re.I): education_context = True
        if re.fullmatch(r'(?:work |professional )?experience|employment', line, re.I): education_context = False
        if education_context: continue
        m = re.search(month + r'\s+(\d{4})\s*[-–—]\s*(?:(present|current)|' + month + r'\s+(\d{4}))', line, re.I)
        if m:
            def mon(v): return datetime.strptime(v[:3].title(), '%b').month
            start = int(m[2]) * 12 + mon(m[1])
            today = datetime.now()
            end = today.year * 12 + today.month if m[3] else int(m[5]) * 12 + mon(m[4])
            if 0 <= end - start <= 840: intervals.append((start, end))
    if not years and intervals:
        months = set()
        for a, b in intervals: months.update(range(a, b))
        profile.experience_years = round(len(months) / 12, 1)
        profile.warnings.append('Experience estimated from date ranges; confirm these are employment periods.')
    roles = [x for x in lines if re.search(r'engineer|developer|executive|manager|specialist|designer|analyst|writer|scientist|intern', x, re.I) and len(x) < 140]
    if roles:
        profile.current_role = roles[0]
        profile.previous_roles = roles[1:10]
        profile.seniority = seniority(roles[0])
    section = ''
    for line in lines:
        if re.fullmatch(r'education|certifications|projects|companies|industries', line, re.I):
            section = line.lower(); continue
        if re.fullmatch(r'skills|experience|summary|contact|professional experience', line, re.I): section = ''
        if section: getattr(profile, section).append(line[:500])
        elif re.search(r'\b(BBA|MBA|B\.?Tech|M\.?Tech|bachelor|master|university|college)\b', line, re.I):
            profile.education.append(line)
    for key in ('name', 'skills', 'experience_years', 'current_role', 'previous_roles', 'education', 'projects', 'certifications'):
        if getattr(profile, key):
            profile.evidence[key] = Evidence(source='Local CV extraction', confidence=.65, kind='inferred', note='Review against original CV; rule-based extraction')
    return profile
