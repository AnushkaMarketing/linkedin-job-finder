from datetime import datetime, timezone
from urllib.parse import urlsplit
from .models import Job, Verification
from .network import SourceError
from .normalize import jsonld_jobs
from .ontology import norm, role_similarity
from bs4 import BeautifulSoup
import json


def company_claims(html: str, url: str, expected: str) -> dict:
    """Extract attributed public claims, not a registry/identity certification."""
    soup = BeautifulSoup(html, 'html.parser')
    nodes = []
    def walk(value, depth=0):
        if depth > 12: return
        if isinstance(value, list):
            for v in value[:100]: walk(v, depth + 1)
        if isinstance(value, dict):
            types = value.get('@type', [])
            if isinstance(types, str): types = [types]
            if any(t in types for t in ('Organization','Corporation','LocalBusiness','ProfessionalService')): nodes.append(value)
            for key in ('@graph', 'hiringOrganization', 'publisher'): walk(value.get(key), depth + 1)
    for script in soup.find_all('script', type='application/ld+json'):
        try: walk(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError): pass
    matching = [n for n in nodes if norm(n.get('name','')) == norm(expected)]
    if not matching: return {}
    node = matching[0]
    fields = {'name': node.get('name'), 'website': node.get('url'), 'published_address': node.get('address'),
              'industry': node.get('industry'), 'employee_count': node.get('numberOfEmployees'), 'public_profiles': node.get('sameAs')}
    return {k: {'value': v, 'source': url, 'kind': 'published claim; not independently confirmed', 'confidence': .5}
            for k, v in fields.items() if v}


def expired(job: Job) -> bool:
    if not job.valid_through: return False
    try:
        dt = datetime.fromisoformat(job.valid_through.replace('Z', '+00:00'))
        if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except ValueError: return False


async def verify_company(job: Job, network) -> Verification:
    result = Verification()
    if expired(job):
        return Verification(status='Conflicting information', confidence=.1, checks=[{'check': 'Vacancy dates', 'status': 'Expired', 'source': job.source_url}])
    listed = False
    for label, url in [('Job listing', job.source_url), ('Company website', job.company_url)]:
        if not url: result.checks.append({'check': label, 'status': 'Not supplied', 'source': ''}); continue
        try:
            page = await network.get(url, ttl=900 if label == 'Job listing' else 86400, robots=True)
            if page['status'] in (404, 410):
                result.checks.append({'check': label, 'status': 'Not found', 'source': url})
                if label == 'Job listing': result.status = 'Conflicting information'
                continue
            reachable = page['status'] == 200
            if reachable and label == 'Company website':
                result.company_information = company_claims(page['body'], page['url'], job.company)
            result.checks.append({'check': label, 'status': 'Reachable; identity unconfirmed' if reachable else f"HTTP {page['status']}", 'source': page['url']})
            if label == 'Job listing': listed = reachable
            # A separate company domain must corroborate both title and employer.
            if label == 'Company website' and reachable and urlsplit(url).hostname != urlsplit(job.source_url).hostname:
                rows = jsonld_jobs(page['body'], page['url'])
                if any(role_similarity(j.title, job.title) >= .9 and norm(j.company) == norm(job.company) and not expired(j) for j in rows):
                    result.checks.append({'check': 'Independent JobPosting corroboration', 'status': 'Title and employer matched', 'source': url})
                    if listed: result.status = 'Verified'; result.confidence = .85
        except SourceError as exc:
            result.checks.append({'check': label, 'status': exc.state, 'source': url})
        except (ValueError, OSError): result.checks.append({'check': label, 'status': 'Unable to verify', 'source': url})
    if result.status == 'Unable to verify' and listed:
        result.status = 'Partially verified'; result.confidence = .4
    if result.status == 'Conflicting information': result.confidence = .1
    result.checks.extend([
        {'check': 'Business identity', 'status': 'Not independently confirmed; no registry provider configured', 'source': ''},
        {'check': 'Reporting office', 'status': 'Coordinates supplied; confirm with employer' if job.coordinates and job.coordinates.precision == 'office' else 'Exact office not established', 'source': job.coordinates.source if job.coordinates else ''},
        {'check': 'Industry and company size', 'status': 'Published claims shown where available; otherwise unknown', 'source': job.company_url},
        {'check': 'Reputation', 'status': 'No reliable evidence collected; no conclusion', 'source': ''}
    ])
    result.note = 'Verification concerns listing evidence, not company legitimacy. Confirm office, eligibility and vacancy with the employer.'
    return result
