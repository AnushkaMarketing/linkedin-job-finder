import asyncio
import json
import os
import secrets
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode, urlsplit
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .models import Model, Profile, Preferences, SourceConfig, LLMConfig, SearchRequest, Job, Evidence, Point
from .profile import parse_profile
from .storage import Store
from .network import Network, SourceError
from .normalize import normalize
from .connectors import CompanyPages
from .pipeline import Engine
from .learning import profile_key, features, train
from .models import RankedJob

ROOT = Path(__file__).resolve().parents[1]


def create_app(folder: Path | None = None):
    store = Store(folder or Path(os.environ.get('JOB_INTEL_DATA', ROOT / '.local')))
    network = Network(store)
    engine = Engine(store, network)
    token = secrets.token_urlsafe(32)
    # Any interrupted persisted run is explicitly marked after a restart.
    for run in store.items('searches'):
        if run['status'] == 'running':
            run.update(status='interrupted', stage='Server restarted'); store.put('searches', run['id'], run)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await engine.stop()
        store.close()

    app = FastAPI(title='Job Intelligence · local engine', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.engine = store, engine
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.middleware('http')
    async def guard(request: Request, call_next):
        origin = request.headers.get('origin')
        allowed = {'http://127.0.0.1:8765', 'http://localhost:8765', 'http://127.0.0.1:5173', 'http://localhost:5173'}
        if request.url.hostname in {'127.0.0.1', 'localhost', '::1'}: allowed.add(str(request.base_url).rstrip('/'))
        if origin and origin not in allowed: return JSONResponse({'detail': 'Foreign origin blocked'}, 403)
        if request.headers.get('sec-fetch-site') == 'cross-site': return JSONResponse({'detail': 'Cross-site request blocked'}, 403)
        if request.url.path.startswith('/api/') and request.url.path != '/api/session':
            if not secrets.compare_digest(request.headers.get('x-local-token', ''), token): return JSONResponse({'detail': 'Local session required'}, 403)
        # Buffer a strictly bounded body before multipart/JSON parsers see it.
        if request.method in {'POST', 'PUT', 'PATCH'}:
            chunks, total = [], 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > 6_000_000: return JSONResponse({'detail': 'Request exceeds 6 MB'}, 413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'): response.headers['Cache-Control'] = 'no-store'
        else: response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    @app.exception_handler(SourceError)
    async def source_error(request, exc): return JSONResponse({'detail': f'{exc.state}: {exc}'}, 422)

    @app.get('/api/session')
    async def session(): return {'token': token}

    @app.get('/api/bootstrap')
    async def bootstrap():
        llm = store.get('settings', 'llm', LLMConfig().model_dump())
        llm['key_saved'] = bool(llm.pop('api_key', ''))
        history = sorted(store.items('searches'), key=lambda r: r['started_at'], reverse=True)
        return {'profile': store.get('settings', 'profile', Profile().model_dump()), 'preferences': store.get('settings', 'preferences', Preferences().model_dump()),
            'sources': store.get('settings', 'sources', SourceConfig().model_dump()), 'llm': llm,
            'history': [{k: r[k] for k in ('id', 'demo', 'status', 'stage', 'started_at', 'counts')} for r in history],
            'imports': len(store.items('imports')), 'version': '1.0.0'}

    @app.put('/api/profile')
    async def save_profile(profile: Profile):
        for key, value in profile.model_dump().items():
            if value and key not in {'evidence', 'warnings'}: profile.evidence[key] = Evidence(source='User reviewed profile', confidence=1, kind='user')
        store.put('settings', 'profile', profile.model_dump()); return profile

    class TextRequest(Model): text: str

    @app.post('/api/profile/extract')
    async def extract(body: TextRequest):
        if len(body.text.strip()) < 30: raise HTTPException(422, 'Paste at least 30 characters of CV text.')
        return parse_profile(body.text)

    @app.post('/api/profile/upload')
    async def upload(file: UploadFile):
        ext = Path(file.filename or '').suffix.lower()
        if ext not in {'.pdf', '.docx', '.txt'}: raise HTTPException(422, 'Use PDF, DOCX or UTF-8 TXT.')
        content = await file.read(5_000_001); await file.close()
        if len(content) > 5_000_000: raise HTTPException(413, 'CV must be under 5 MB.')
        def parse():
            try:
                result = subprocess.run([sys.executable, '-I', str(ROOT / 'backend/document_worker.py'), ext], input=content, capture_output=True, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
                return json.loads(result.stdout)
            except subprocess.TimeoutExpired: return {'error': 'Document parsing exceeded 15 seconds. Try plain text.'}
            except (ValueError, OSError): return {'error': 'Document could not be read. Try plain text.'}
        result = await asyncio.to_thread(parse)
        if result.get('error'): raise HTTPException(422, result['error'])
        return parse_profile(result['text'])

    @app.put('/api/sources')
    async def sources(config: SourceConfig): store.put('settings', 'sources', config.model_dump()); return config

    @app.put('/api/llm')
    async def llm(config: LLMConfig):
        if config.enabled and (not config.consent or not config.model.strip()): raise HTTPException(422, 'Choose a model and explicitly consent to the described data sharing.')
        old = store.get('settings', 'llm', {})
        # Never reuse a saved key when the destination endpoint changes.
        if not config.api_key and old.get('endpoint') == config.endpoint: config.api_key = old.get('api_key', '')
        store.put('settings', 'llm', config.model_dump()); return {'saved': True}

    @app.post('/api/jobs/import')
    async def import_job(job: Job):
        if len(store.items('imports')) >= 500: raise HTTPException(422, 'Import limit reached (500). Delete local data to reset.')
        job.source = 'Manual import'; job.job_id = ''; job.evidence = {}; job.state = 'new'
        job = normalize(job); store.put('imports', job.job_id, job.model_dump()); return job

    class URLRequest(Model): url: str

    @app.post('/api/jobs/import-url')
    async def import_url(body: URLRequest):
        try: jobs = await asyncio.wait_for(CompanyPages(network, body.url).search([], Preferences()), 30)
        except asyncio.TimeoutError: raise HTTPException(422, 'Page timed out. Paste the job details instead.')
        except ValueError: raise HTTPException(422, 'Use a valid public HTTP(S) job URL.')
        if len(store.items('imports')) + len(jobs) > 500: raise HTTPException(422, 'Import limit reached (500).')
        for job in jobs: store.put('imports', job.job_id, job.model_dump())
        return {'count': len(jobs)}

    class StateRequest(Model): state: Literal['new', 'saved', 'ignored', 'viewed', 'applied']

    @app.put('/api/jobs/{identifier}/state')
    async def job_state(identifier: str, body: StateRequest):
        store.put('states', identifier, {'id': identifier, 'state': body.state}); return body

    @app.post('/api/searches')
    async def search(body: SearchRequest):
        prefs = body.preferences
        if prefs.strict_radius and not prefs.origin and any(m != 'remote' for m in prefs.work_modes): raise HTTPException(422, 'Set your location coordinates or turn off strict radius.')
        profile = Profile.model_validate(store.get('settings', 'profile', {}))
        if body.demo:
            profile = Profile(name='Demo candidate', current_role='Social Media Manager', experience_years=3,
                skills=['Social media marketing', 'Content strategy', 'Copywriting', 'Canva'], previous_roles=['Content Marketing Specialist'])
        if not prefs.roles and not profile.preferred_roles and not profile.current_role: raise HTTPException(422, 'Add at least one target role or a current role in your profile.')
        try: run = engine.start(profile, prefs, SourceConfig.model_validate(store.get('settings', 'sources', {})), body.demo)
        except ValueError as exc: raise HTTPException(409, str(exc))
        if not body.demo: store.put('settings', 'preferences', prefs.model_dump())
        return run

    @app.get('/api/searches/{identifier}')
    async def search_status(identifier: str):
        run = store.get('searches', identifier)
        if not run: raise HTTPException(404, 'Search not found')
        for row in run['results']:
            state = store.get('states', row['job']['job_id'])
            if state: row['job']['state'] = state['state']
        return run

    @app.post('/api/searches/{identifier}/cancel')
    async def cancel(identifier: str): await engine.cancel(identifier); return {'cancelled': True}

    class FeedbackRequest(Model):
        search_id: str
        job_id: str
        label: Literal['relevant', 'not_relevant']

    @app.post('/api/feedback')
    async def feedback(body: FeedbackRequest):
        run = store.get('searches', body.search_id)
        if not run or run.get('demo'): raise HTTPException(422, 'Training labels require a real research result; demo labels are excluded.')
        current = Profile.model_validate(store.get('settings', 'profile', {}))
        key = profile_key(current)
        if run.get('profile_key') != key: raise HTTPException(422, 'Profile changed since this search. Run research again before teaching the engine.')
        result = next((r for r in run['results'] if r['job']['job_id']==body.job_id),None)
        if not result: raise HTTPException(404,'Job not found in this search')
        store.put('feedback',key+':'+body.job_id,{'profile_key':key,'job_id':body.job_id,'label':body.label,'features':features(RankedJob.model_validate(result))})
        return {'saved':True, 'note':'Used on your next search. Re-labelling replaces the previous vote.'}

    @app.get('/api/learning')
    async def learning():
        key=profile_key(Profile.model_validate(store.get('settings','profile',{})))
        model=train([x for x in store.items('feedback') if x['profile_key']==key])
        return {k:v for k,v in model.items() if k!='weights'}

    @app.delete('/api/learning')
    async def reset_learning():
        key=profile_key(Profile.model_validate(store.get('settings','profile',{})))
        for label in store.items('feedback'):
            if label['profile_key']==key:store.delete('feedback',key+':'+label['job_id'])
        return {'reset':True}

    class PlaceRequest(Model): query: str

    @app.post('/api/geocode')
    async def geocode(body: PlaceRequest):
        if len(body.query.strip()) < 3: raise HTTPException(422, 'Enter a city, area, address or PIN.')
        data = await network.json('https://nominatim.openstreetmap.org/search?' + urlencode({'q': body.query[:250], 'format': 'jsonv2', 'limit': 3}), ttl=604800)
        return [{'label': p['display_name'], 'point': Point(latitude=float(p['lat']), longitude=float(p['lon']), precision='user', source='User-selected OpenStreetMap search location').model_dump()} for p in data[:3]]

    @app.delete('/api/data')
    async def erase(): await engine.stop(); store.clear(); return {'deleted': True}

    if (ROOT / 'dist/assets').exists(): app.mount('/assets', StaticFiles(directory=ROOT / 'dist/assets'), name='assets')

    @app.get('/favicon.svg')
    async def favicon(): return FileResponse(ROOT / 'public/favicon.svg')

    @app.get('/')
    async def index():
        if not (ROOT / 'dist/index.html').exists(): raise HTTPException(503, 'Build the interface with npm run build first, or use the Vite dev server.')
        return FileResponse(ROOT / 'dist/index.html')

    return app
