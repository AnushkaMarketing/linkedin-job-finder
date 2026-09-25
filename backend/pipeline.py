import asyncio
import time
from uuid import uuid4
from .models import Profile, Preferences, SourceConfig, Job, Point, LLMConfig, now
from .connectors import ATS, Remotive, CompanyPages, LinkedIn, linkedin_links
from .normalize import normalize, deduplicate
from .matching import match_job, rank, search_plan
from .ontology import norm, role_similarity
from .geo import location_fit
from .verification import verify_company, expired
from .network import SourceError
from .llm import CompatibleProvider
from .intelligence import retrieve, shortlist_insights
from .learning import profile_key, train, personalized_rank


def demo_jobs() -> list[Job]:
    # Deliberately fictional fixtures: never mixed into discovery or given application links.
    return [normalize(Job(title=title, company=company, source='DEMO · fictional employer',
        description=description, work_mode=mode, location=location,
        coordinates=Point(latitude=lat, longitude=lon, precision='office', source='Fictional demo coordinates') if lat else None,
        experience_min=years, employment_type='Full-time')) for title, company, description, mode, location, lat, lon, years in [
        ('Social Media Manager', 'Demo Signal Studio', 'Required\nSocial media marketing; Content strategy; Copywriting\nPreferred\nSEO\nResponsibilities\nPlan campaigns and report analytics.', 'hybrid', 'Demo office · Noida', 28.515, 77.405, 3),
        ('Content Marketing Specialist', 'Demo Storyworks', 'Required\nContent marketing; SEO; Google Analytics\nResponsibilities\nCreate B2B stories and editorial calendars.', 'on-site', 'Demo office · Noida', 28.54, 77.39, 2),
        ('Digital Marketing Executive', 'Demo Bright Labs', 'Required\nGoogle Ads; Email marketing; SEO\nPreferred\nSocial media marketing', 'remote', 'India · demo restriction', None, None, 1),
        ('Senior Machine Learning Engineer', 'Demo Modelworks', 'Required\nPython; PyTorch; Machine learning; SQL\nResponsibilities\nLead a team building models.', 'remote', 'Worldwide · demo', None, None, 6),
        ('Content Strategist', 'Demo Distant Studio', 'Required\nContent strategy; Copywriting', 'on-site', 'Demo distant office', 28.70, 77.10, 4),
        ('Social Media Executive', 'Demo Unknown Office', 'Required\nSocial media marketing; Canva', 'hybrid', 'Noida · office not supplied', None, None, 1),
    ]]


def exclusion(job: Job, prefs: Preferences, roles: list[str], profile: Profile) -> str:
    if expired(job): return 'Expired vacancy'
    if norm(job.company) in {norm(c) for c in prefs.excluded_companies}: return 'Excluded employer'
    if prefs.work_modes and job.work_mode not in prefs.work_modes: return 'Work mode unavailable or outside selection'
    if not location_fit(job, prefs)[0]: return 'Outside radius or office unverified'
    if prefs.employment_types and job.employment_type and norm(job.employment_type) not in {norm(t) for t in prefs.employment_types}: return 'Employment type'
    if prefs.experience_max is not None and job.experience_min is not None and job.experience_min > prefs.experience_max: return 'Experience range'
    if prefs.experience_min is not None and job.experience_max is not None and job.experience_max < prefs.experience_min: return 'Experience range'
    if prefs.salary.minimum is not None and job.salary.maximum is not None and prefs.salary.currency.upper() == job.salary.currency.upper() and prefs.salary.period == job.salary.period and job.salary.maximum < prefs.salary.minimum: return 'Salary below minimum'
    if prefs.salary.maximum is not None and job.salary.minimum is not None and prefs.salary.currency.upper() == job.salary.currency.upper() and prefs.salary.period == job.salary.period and job.salary.minimum > prefs.salary.maximum: return 'Salary above selected range'
    if roles and max(role_similarity(job.title, r) for r in roles) < .2:
        skills = next(f for f in match_job(profile, job, prefs).factors if f.name == 'Skills')
        if skills.score is None or skills.score < 60: return 'Low role and skill relevance'
    return ''


class Engine:
    def __init__(self, store, network):
        self.store, self.network = store, network
        self.tasks = {}

    def start(self, profile: Profile, prefs: Preferences, sources: SourceConfig, demo=False):
        if any(not t.done() for t in self.tasks.values()): raise ValueError('A search is already running. Cancel it before starting another.')
        self.tasks = {}
        identifier = uuid4().hex
        snapshot = {'id': identifier, 'demo': demo, 'status': 'running', 'stage': 'Planning', 'started_at': now(), 'elapsed': 0,
            'profile_key': profile_key(profile), 'plan': search_plan(profile, prefs), 'preferences': prefs.model_dump(), 'sources': [], 'results': [],
            'counts': {'discovered': 0, 'duplicates': 0, 'eligible': 0, 'checked': 0, 'llm_calls': 0, 'verified': 0}, 'exclusions': {}, 'warnings': [],
            'linkedin': linkedin_links(prefs.roles or profile.preferred_roles, prefs)}
        self.store.put('searches', identifier, snapshot)
        self.tasks[identifier] = asyncio.create_task(self.run(snapshot, profile, prefs, sources))
        # Bound retained histories. Raw CV text is never stored.
        for old in sorted(self.store.items('searches'), key=lambda x: x['started_at'], reverse=True)[20:]: self.store.delete('searches', old['id'])
        return snapshot

    async def cancel(self, identifier):
        task = self.tasks.get(identifier)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def stop(self):
        for key in list(self.tasks): await self.cancel(key)

    async def run(self, snapshot, profile, prefs, sources):
        began = time.monotonic()
        calls, hits = self.network.calls, self.network.hits
        def save():
            snapshot['elapsed'] = round(time.monotonic() - began, 1)
            snapshot['network'] = {'requests': self.network.calls - calls, 'cache_hits': self.network.hits - hits}
            self.store.put('searches', snapshot['id'], snapshot)
        try:
            snapshot['stage'] = 'Discovering'; save()
            jobs = []
            if snapshot['demo']:
                jobs = demo_jobs()
                snapshot['sources'] = [{'source': 'Fictional demo fixtures', 'status': 'Complete', 'count': len(jobs), 'detail': 'No live discovery or verification performed.'}]
            else:
                connectors = [LinkedIn()]
                connectors += [ATS(self.network, k, b) for k in ('greenhouse', 'lever') for b in getattr(sources, k)]
                connectors += [CompanyPages(self.network, url) for url in sources.career_pages]
                if sources.remotive: connectors.append(Remotive(self.network))
                if sources.manual:
                    jobs += [Job.model_validate(j) for j in self.store.items('imports')]
                    snapshot['sources'].append({'source': 'Manual imports', 'status': 'Complete', 'count': len(jobs), 'detail': 'User supplied; independently checked where possible.'})
                gate = asyncio.Semaphore(3)
                async def discover(connector):
                    state = {'source': connector.name, 'status': 'Queued', 'count': 0, 'detail': getattr(connector, 'url', '')}
                    snapshot['sources'].append(state); save()
                    async with gate:
                        state['status'] = 'Searching'; save()
                        try:
                            found = await asyncio.wait_for(connector.search(snapshot['plan']['roles'], prefs), 60)
                            jobs.extend(found); state.update(status='Complete', count=len(found))
                        except SourceError as exc: state.update(status=exc.state, detail=str(exc))
                        except asyncio.TimeoutError: state.update(status='Temporary failure', detail='Source exceeded its 60 second time budget.')
                        except Exception: state.update(status='Temporary failure', detail='Unexpected source response. Other sources continue.')
                        save()
                await asyncio.gather(*(discover(c) for c in connectors))
            snapshot['counts']['discovered'] = len(jobs)
            if len(jobs) > 2500:
                jobs = retrieve(jobs, profile, prefs, 2500)
                snapshot['warnings'].append('Candidate pool limited to 2,500 by BM25 profile/title relevance before detailed analysis.')
            snapshot['stage'] = 'Normalizing and matching'; save()
            unique = deduplicate(jobs)
            snapshot['counts']['duplicates'] = len(jobs) - len(unique)
            eligible = []
            for job in unique:
                reason = exclusion(job, prefs, snapshot['plan']['roles'], profile)
                if reason: snapshot['exclusions'][reason] = snapshot['exclusions'].get(reason, 0) + 1
                else: eligible.append(match_job(profile, job, prefs))
            snapshot['counts']['eligible'] = len(eligible)
            labels = [] if snapshot['demo'] else [x for x in self.store.items('feedback') if x['profile_key'] == snapshot['profile_key']]
            model = train(labels)
            snapshot['learning'] = {k:v for k,v in model.items() if k != 'weights'}
            def rerank(rows): return personalized_rank(rank(rows), model)
            results = rerank(eligible)[:prefs.limit]
            snapshot['stage'] = 'Checking listing evidence'; save()
            gate = asyncio.Semaphore(4)
            async def verify(row):
                async with gate:
                    if not snapshot['demo']:
                        try: row.verification = await asyncio.wait_for(verify_company(row.job, self.network), 30)
                        except asyncio.TimeoutError: row.verification.note = 'Verification timed out. Evidence remains unconfirmed.'
                    else: row.verification.note = 'Fictional demo. No verification attempted.'
                    state = self.store.get('states', row.job.job_id)
                    if state: row.job.state = state['state']
                    snapshot['counts']['checked'] += 1
                    if row.verification.status == 'Verified': snapshot['counts']['verified'] += 1
                    snapshot['results'] = [r.model_dump() for r in rerank(results)]; save()
            await asyncio.gather(*(verify(r) for r in results))
            config = LLMConfig.model_validate(self.store.get('settings', 'llm', {}))
            if config.enabled and config.consent and not snapshot['demo']:
                snapshot['stage'] = 'Optional AI analysis'; save()
                provider = CompatibleProvider(config)
                for row in rerank(results)[:3]:
                    try:
                        snapshot['counts']['llm_calls'] += 1
                        row.llm_advice = await provider.analyze(profile, row.job)
                    except Exception: snapshot['warnings'].append('Optional AI unavailable or response failed evidence validation. Deterministic results retained.'); break
            snapshot['results'] = [r.model_dump() for r in rerank(results)]
            snapshot['insights'] = shortlist_insights(results)
            snapshot['status'] = 'completed'; snapshot['stage'] = 'Research complete'
            if any(s['status'] != 'Complete' for s in snapshot['sources']): snapshot['warnings'].append('Search completed with partial source coverage. See individual source reports.')
            if not results: snapshot['warnings'].append('No eligible jobs were established by the configured sources. Review exclusions, add employer boards or import a listing.')
        except asyncio.CancelledError:
            snapshot['status'] = 'cancelled'; snapshot['stage'] = 'Cancelled'
        except Exception:
            snapshot['status'] = 'failed'; snapshot['stage'] = 'Research interrupted'
            snapshot['warnings'].append('The run could not finish. Completed evidence is retained; retry after reviewing source settings.')
        finally: save()
