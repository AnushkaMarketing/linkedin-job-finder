import hashlib
import html
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
from bs4 import BeautifulSoup
from .models import Job, Evidence, Point, Salary
from .ontology import extract_skills, norm, canonical, seniority, role_similarity


def plain(value: str) -> str:
    soup = BeautifulSoup(html.unescape(value or ''), 'html.parser')
    for item in soup(['script', 'style', 'iframe']): item.decompose()
    return soup.get_text('\n', strip=True)[:60_000]


def canonical_url(value: str) -> str:
    if not value: return ''
    p = urlsplit(value)
    keep = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith('utm_') and k not in {'trk', 'ref', 'trackingId'}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), urlencode(sorted(keep)), ''))


def normalize(job: Job) -> Job:
    job.description = plain(job.description)
    job.skills = list(dict.fromkeys(canonical(s) for s in job.skills))
    if not job.skills:
        job.skills = extract_skills(job.description)
        job.evidence['skills'] = Evidence(source=job.source_url or job.source, confidence=.7, kind='inferred', note='Mentioned skills, not necessarily mandatory')
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?\s*\+?\s*years?', job.description, re.I)
    if m and job.experience_min is None and float(m[1]) <= 70 and (not m[2] or float(m[1]) <= float(m[2]) <= 70):
        job.experience_min = float(m[1]); job.experience_max = float(m[2]) if m[2] else None
        job.evidence['experience'] = Evidence(source=job.source_url or job.source, confidence=.65, kind='inferred', note=m[0])
    if job.work_mode == 'unknown':
        if re.search(r'\bhybrid\b', job.description, re.I): job.work_mode = 'hybrid'
        elif re.search(r'\b(?:fully remote|100% remote|work from anywhere)\b', job.description, re.I): job.work_mode = 'remote'
        elif re.search(r'\b(?:on-site|onsite|on site)\b', job.description, re.I): job.work_mode = 'on-site'
        if job.work_mode != 'unknown': job.evidence['work_mode'] = Evidence(source=job.source_url or job.source, confidence=.65, kind='inferred', note='Description phrase; review source')
    job.seniority = job.seniority or seniority(job.title)
    if not job.job_id:
        identity = canonical_url(job.source_url or job.application_url) or '|'.join([norm(job.company), norm(job.title), norm(job.location)])
        job.job_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
    for field in ('title', 'company', 'description', 'location', 'salary', 'application_url', 'coordinates'):
        if field == 'salary' and job.salary.minimum is None and job.salary.maximum is None and not job.salary.text: continue
        if getattr(job, field) and field not in job.evidence:
            job.evidence[field] = Evidence(source=job.source_url or job.source, confidence=.6, kind='user' if job.source == 'Manual import' else 'observed', note='As supplied by source; not independently confirmed')
    return job


def deduplicate(jobs: list[Job]) -> list[Job]:
    kept: list[Job] = []
    def company(value): return re.sub(r'\b(?:private|pvt|ltd|limited|inc|llc)\b', '', norm(value)).strip()
    for job in jobs:
        duplicate = None
        for prior in kept:
            same_id = bool(job.job_id) and job.source == prior.source and job.job_id == prior.job_id
            same_url = bool(job.source_url and canonical_url(job.source_url) == canonical_url(prior.source_url) and norm(job.title) == norm(prior.title))
            # Conservative similarity never merges different cities or seniority levels.
            similar = (company(job.company) == company(prior.company) and bool(job.location) and norm(job.location) == norm(prior.location) and job.seniority == prior.seniority and role_similarity(job.title, prior.title) >= .95)
            if same_id or same_url or similar: duplicate = prior; break
        if duplicate:
            duplicate.corroborating_urls = list(dict.fromkeys(duplicate.corroborating_urls + [u for u in (job.source_url, job.application_url) if u]))
            if len(job.description) > len(duplicate.description):
                duplicate.description = job.description; duplicate.skills = job.skills
        else: kept.append(job)
    return kept


def jsonld_jobs(body: str, url: str) -> list[Job]:
    soup = BeautifulSoup(body, 'html.parser')
    nodes = []
    def walk(value, depth=0):
        if depth > 15: return
        if isinstance(value, list):
            for child in value[:500]: walk(child, depth + 1)
        elif isinstance(value, dict):
            if value.get('@type') == 'JobPosting' or 'JobPosting' in (value.get('@type') if isinstance(value.get('@type'), list) else []): nodes.append(value)
            for key in ('@graph', 'itemListElement', 'item'): walk(value.get(key), depth + 1)
    for script in soup.find_all('script', type='application/ld+json'):
        try: walk(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError): continue
    jobs = []
    for node in nodes[:100]:
        try:
            org = node.get('hiringOrganization') or {}
            loc = node.get('jobLocation') or {}
            if isinstance(loc, list): loc = loc[0] if loc else {}
            address = loc.get('address') or {}
            geo = loc.get('geo') or {}
            coords = Point(latitude=geo['latitude'], longitude=geo['longitude'], precision='office', source=url) if 'latitude' in geo and 'longitude' in geo else None
            sal = node.get('baseSalary') or {}; val = sal.get('value') or {}
            if not isinstance(val, dict): val = {'minValue': val, 'maxValue': val}
            per = str(val.get('unitText', 'unknown')).lower()
            listing_url = urljoin(url, node.get('url') or url)
            identity = hashlib.sha256((listing_url + '|' + str(node.get('title')) + '|' + str(org.get('name'))).encode()).hexdigest()[:20]
            job = Job(job_id=identity, title=node.get('title') or 'Untitled listing', company=org.get('name') or 'Company not stated', source='Company careers JSON-LD', description=node.get('description') or '',
                company_url=org.get('sameAs') or '', source_url=listing_url, application_url=listing_url,
                location=', '.join(str(address.get(k)) for k in ('streetAddress', 'addressLocality', 'addressRegion', 'addressCountry') if address.get(k)) if isinstance(address, dict) else str(address),
                coordinates=coords, work_mode='remote' if node.get('jobLocationType') == 'TELECOMMUTE' else 'unknown',
                salary=Salary(minimum=val.get('minValue'), maximum=val.get('maxValue'), currency=sal.get('currency') or '', period=per if per in {'year', 'month', 'hour'} else 'unknown'),
                employment_type=str(node.get('employmentType') or ''), posted_date=str(node.get('datePosted') or ''), valid_through=str(node.get('validThrough') or ''),
                remote_restrictions=json.dumps(node.get('applicantLocationRequirements') or '', ensure_ascii=False))
            jobs.append(normalize(job))
        except (ValueError, TypeError, AttributeError): continue
    return jobs
