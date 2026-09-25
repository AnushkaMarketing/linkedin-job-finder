from abc import ABC, abstractmethod
from urllib.parse import urlencode
from .models import Job, Salary, Preferences
from .network import Network, SourceError
from .normalize import normalize, plain, jsonld_jobs


class JobSource(ABC):
    name: str
    @abstractmethod
    async def search(self, roles: list[str], preferences: Preferences) -> list[Job]: ...
    @abstractmethod
    async def fetch_job(self, reference: str) -> Job | None: ...
    def normalize_job(self, job: Job) -> Job: return normalize(job)
    def validate(self, job: Job) -> bool: return bool(job.title and job.company)
    async def health_check(self) -> dict: return {'source': self.name, 'status': 'Configured; not contacted yet'}


class ATS(JobSource):
    def __init__(self, network: Network, kind: str, board: str):
        self.network, self.kind, self.board = network, kind, board
        self.name = f'{kind.title()}: {board}'

    async def search(self, roles, preferences):
        if self.kind == 'greenhouse':
            url = f'https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs?content=true'
            data = await self.network.json(url)
            rows = data.get('jobs', [])[:500]
        else:
            url = f'https://api.lever.co/v0/postings/{self.board}?mode=json&limit=500'
            rows = await self.network.json(url)
            if not isinstance(rows, list): raise SourceError('Temporary failure', 'Unexpected board response')
        result = []
        for row in rows[:500]:
            try: result.append(self.from_row(row))
            except (ValueError, TypeError, KeyError): continue
        return result

    def from_row(self, row):
        if self.kind == 'greenhouse':
            return normalize(Job(job_id=f'gh:{self.board}:{row["id"]}', source=self.name, title=row['title'], company=row.get('company_name') or self.board,
                description=row.get('content') or '', location=(row.get('location') or {}).get('name', ''), source_url=row['absolute_url'], application_url=row['absolute_url']))
        cats = row.get('categories') or {}; sal = row.get('salaryRange') or {}; mode = row.get('workplaceType', 'unknown')
        return normalize(Job(job_id=f'lever:{self.board}:{row["id"]}', source=self.name, title=row['text'], company=self.board,
            description='\n'.join([row.get('descriptionPlain') or '', *[plain(x.get('text', '') + '\n' + x.get('content', '')) for x in row.get('lists', [])], row.get('additionalPlain') or '']),
            location=cats.get('location', ''), employment_type=cats.get('commitment', ''), source_url=row['hostedUrl'], application_url=row.get('applyUrl') or row['hostedUrl'],
            work_mode=mode if mode in {'remote', 'on-site', 'hybrid'} else 'unknown', salary=Salary(minimum=sal.get('min'), maximum=sal.get('max'), currency=sal.get('currency') or '', period=sal.get('interval') if sal.get('interval') in {'year', 'month', 'hour'} else 'unknown')))

    async def fetch_job(self, reference):
        if self.kind == 'greenhouse':
            row = await self.network.json(f'https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs/{reference}')
        else: row = await self.network.json(f'https://api.lever.co/v0/postings/{self.board}/{reference}')
        return self.from_row(row)


class Remotive(JobSource):
    name = 'Remotive'
    def __init__(self, network): self.network = network
    async def search(self, roles, preferences):
        # Fetch once per six hours. Expanded titles are filtered locally, not repeated API calls.
        data = await self.network.json('https://remotive.com/api/remote-jobs?limit=500', ttl=21600)
        result = []
        for row in data.get('jobs', [])[:500]:
            try:
                result.append(normalize(Job(job_id='remotive:' + str(row['id']), source=self.name, title=row['title'], company=row['company_name'], description=row.get('description') or '',
                    location=row.get('candidate_required_location') or '', remote_restrictions=row.get('candidate_required_location') or 'Not stated', work_mode='remote',
                    source_url=row['url'], application_url=row['url'], posted_date=row.get('publication_date') or '', employment_type=row.get('job_type') or '', salary=Salary(text=row.get('salary') or '', period='unknown'))))
            except (ValueError, KeyError): continue
        return result
    async def fetch_job(self, reference):
        return next((j for j in await self.search([], Preferences()) if j.job_id == reference), None)


class CompanyPages(JobSource):
    name = 'Company careers pages'
    def __init__(self, network, url): self.network, self.url = network, url
    async def search(self, roles, preferences):
        result = await self.network.get(self.url, robots=True)
        if result['status'] != 200: raise SourceError('Source unavailable', f"Page returned HTTP {result['status']}")
        jobs = jsonld_jobs(result['body'], result['url'])
        if not jobs: raise SourceError('Source unavailable', 'No JobPosting structured data; paste the listing manually')
        return jobs
    async def fetch_job(self, reference):
        rows = await self.search([], Preferences()); return rows[0] if rows else None


class LinkedIn(JobSource):
    name = 'LinkedIn'
    async def search(self, roles, preferences):
        raise SourceError('Authentication required', 'Browser-assisted only. No authorized session bridge is connected; use search links and manual import.')
    async def fetch_job(self, reference):
        raise SourceError('Authentication required', 'Paste the listing you can view; no automated authenticated collection')
    async def health_check(self):
        return {'source': self.name, 'status': 'Authentication required', 'browser': 'Not connected', 'authenticated': False}


def linkedin_links(roles: list[str], preferences: Preferences) -> list[dict]:
    return [{'role': role, 'url': 'https://www.linkedin.com/jobs/search/?' + urlencode({'keywords': role, 'location': preferences.location, 'f_TPR': 'r604800', 'sortBy': 'DD'})} for role in roles[:8]]
