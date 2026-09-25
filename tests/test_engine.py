import asyncio
import io
import json
import socket
import zipfile
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from backend.models import Job, Profile, Preferences, Point, SourceConfig, Salary, LLMConfig
from backend.profile import parse_profile
from backend.document_worker import extract
from backend.ontology import canonical, relation
from backend.geo import distance, location_fit
from backend.normalize import normalize, deduplicate, jsonld_jobs, canonical_url
from backend.matching import match_job, rank, search_plan
from backend.storage import Store
from backend.network import Network, SourceError, resolve_public
from backend.verification import verify_company
from backend.pipeline import Engine
from backend.main import create_app
from backend.connectors import ATS


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path)
    yield s
    s.close()


def test_profile_dates_union_and_education_excluded():
    p = parse_profile('Demo Candidate\nSocial Media Executive\nExperience\nJun 2023 – Feb 2026\nJan 2024 – Jan 2025\nSkills\nSEO, Python 3, ReactJS\nEducation\nJun 2020 – Jun 2023\nBBA')
    assert p.experience_years == 2.7
    assert p.name == 'Demo Candidate'
    assert {'SEO', 'Python', 'React'} <= set(p.skills)
    assert p.evidence['experience_years'].kind == 'inferred'


def test_missing_profile_not_fabricated():
    p = parse_profile('Candidate\nSkills\nCopywriting')
    assert p.experience_years is None
    assert not p.companies and not p.current_role


@pytest.mark.parametrize('alias,expected', [('Python 3','Python'),('ReactJS','React'),('react.js','React')])
def test_skill_aliases(alias,expected): assert canonical(alias) == expected


def test_related_is_partial():
    score, label, _ = relation(['PyTorch'], 'Deep Learning')
    assert 0 < score < 1 and label != 'Exact'
    assert relation(['Unknown invented skill'], 'Python')[0] == 0


def test_geography_precision_and_boundary():
    origin = Point(latitude=28.505,longitude=77.41)
    assert distance(origin,origin) == 0
    office = Point(latitude=28.515,longitude=77.405,precision='office')
    j = Job(title='Designer',company='Example',coordinates=office,work_mode='hybrid')
    p = Preferences(origin=origin,radius_km=15)
    assert location_fit(j,p)[0]
    j.coordinates.precision='city'
    assert not location_fit(j,p)[0]
    p.strict_radius=False
    assert location_fit(j,p)[0] and 'unverified' in location_fit(j,p)[2]
    j.work_mode='remote'
    assert location_fit(j,Preferences())[0]
    assert distance(Point(latitude=0,longitude=0),Point(latitude=0,longitude=180)) == pytest.approx(20015.11,abs=.1)


def test_dedup_preserves_separate_roles_locations():
    rows = [normalize(Job(title=t,company=c,location=l,source=s,source_url=u)) for t,c,l,s,u in [
        ('Software Engineer','Example Ltd','Noida','A','https://example.com/jobs/1?utm_source=a'),
        ('Software Engineer','Example Ltd','Noida','B','https://example.com/jobs/1?utm_source=b'),
        ('Senior Software Engineer','Example Ltd','Noida','C','https://example.com/jobs/2'),
        ('Software Engineer','Example Ltd','Delhi','C','https://example.com/jobs/3')]]
    assert len(deduplicate(rows)) == 3
    assert canonical_url('https://example.com/jobs/1?utm_source=a')=='https://example.com/jobs/1'


def test_jsonld_multi_job_and_unsafe_url():
    rows = [{'@type':'JobPosting','title':t,'hiringOrganization':{'name':'Example'},'description':'<b>Python</b>'} for t in ['AI Engineer','Designer']]
    rows.append({'@type':'JobPosting','title':'Unsafe','url':'javascript:alert(1)'})
    result = jsonld_jobs('<script type="application/ld+json">'+json.dumps(rows)+'</script>','https://example.com/careers')
    assert len(deduplicate(result))==2
    assert result[0].description=='Python'


def test_match_ranking_and_unknown_fields():
    profile = Profile(skills=['Python','PyTorch'],experience_years=3,current_role='AI Engineer')
    good = normalize(Job(title='AI Engineer',company='Example',description='Required\nPython; Deep Learning; Kubernetes',experience_min=2,work_mode='remote'))
    poor = normalize(Job(title='Accountant',company='Other',skills=['Excel'],experience_min=8,work_mode='remote'))
    prefs=Preferences(roles=['AI Engineer'],work_modes=['remote'])
    a,b=match_job(profile,good,prefs),match_job(profile,poor,prefs)
    assert rank([b,a])[0].job.title=='AI Engineer'
    assert a.related and any('Kubernetes' in gap for gap in a.gaps)
    assert next(f for f in a.factors if f.name=='Salary').score is None
    assert a.coverage < 100
    assert 'AI Engineer' in search_plan(profile,prefs)['roles']


def test_storage_encrypted_persists_and_deletes(tmp_path):
    s=Store(tmp_path);s.put('profile','one',{'name':'SECRET_CANDIDATE','key':'SECRET_API_KEY'})
    assert b'SECRET_CANDIDATE' not in (tmp_path/'intelligence.sqlite').read_bytes()
    s.close();s=Store(tmp_path)
    assert s.get('profile','one')['name']=='SECRET_CANDIDATE'
    s.put('cache','expired',{'a':1},ttl=-1)
    assert s.get('cache','expired') is None
    s.clear();assert s.items('profile')==[];s.close()


@pytest.mark.parametrize('address',['127.0.0.1','10.1.2.3','169.254.169.254','::1','192.168.1.1','0.0.0.0'])
def test_ssrf_private_dns(monkeypatch,address):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',(address,443))])
    with pytest.raises(SourceError):resolve_public('https://evil.example/jobs')


def test_ssrf_mixed_dns_and_invalid_schemes(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('1.1.1.1',443)),(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(SourceError):resolve_public('https://evil.example')
    with pytest.raises(ValueError):resolve_public('file:///etc/passwd')
    with pytest.raises(ValidationError):Job(title='x',company='y',source_url='javascript:alert(1)')


def test_network_redirect_blocks_private_and_rate_limit(store,monkeypatch):
    import backend.network as n
    def resolve(url):
        if '127.0.0.1' in url: raise SourceError('Source unavailable','Private destination')
        return ('example.com','1.1.1.1',443)
    monkeypatch.setattr(n,'resolve_public',resolve)
    monkeypatch.setattr(n,'fetch_pinned',lambda u:{'status':302,'headers':{'Location':'http://127.0.0.1/admin'},'body':'','url':u})
    network=Network(store)
    with pytest.raises(SourceError):asyncio.run(network.get('https://example.com/job'))
    monkeypatch.setattr(n,'fetch_pinned',lambda u:{'status':429,'headers':{},'body':'','url':u})
    with pytest.raises(SourceError,match='429'):asyncio.run(network.get('https://rate.example/job'))
    before=network.calls
    with pytest.raises(SourceError,match='cooldown'):asyncio.run(network.get('https://rate.example/job'))
    assert before==network.calls


class FakeNetwork:
    calls=0;hits=0
    async def get(self,url,**kwargs):
        return {'status':200,'body':'<html>Company page without corroboration</html>','url':url}


def test_reachable_is_not_verified():
    j=Job(title='AI Engineer',company='Example',source_url='https://jobs.example/1',company_url='https://example.com')
    result=asyncio.run(verify_company(j,FakeNetwork()))
    assert result.status=='Partially verified'
    assert result.confidence<.5


def test_conflicting_and_unavailable_verification():
    assert asyncio.run(verify_company(Job(title='x',company='y'),FakeNetwork())).status=='Unable to verify'
    assert asyncio.run(verify_company(Job(title='x',company='y',valid_through='2000-01-01'),FakeNetwork())).status=='Conflicting information'


def test_document_formats_and_bombs():
    assert extract(b'Name\nPython developer','.txt').startswith('Name')
    with pytest.raises(ValueError):extract(b'not a pdf','.pdf')
    with pytest.raises(ValueError):extract(b'x'*5_300_000,'.txt')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Candidate</w:t></w:r></w:p></w:document>')
    assert extract(buf.getvalue(),'.docx')=='Candidate'
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('word/document.xml','x'*1_000_000)
    with pytest.raises(ValueError,match='compression'):extract(buf.getvalue(),'.docx')


def test_ats_normalization():
    gh=ATS(None,'greenhouse','sample')
    row=gh.from_row({'id':1,'title':'Engineer','absolute_url':'https://example.com/job','location':{'name':'Noida'},'content':'Required Python'})
    assert row.company=='sample' and row.posted_date==''
    assert 'Python' in row.skills and row.coordinates is None


def test_pipeline_limit_and_source_failure(store):
    for n in range(65):
        j=normalize(Job(title=f'Python Engineer {n}',company=f'Company {n}',skills=['Python'],work_mode='remote'))
        store.put('imports',j.job_id,j.model_dump())
    async def run():
        engine=Engine(store,FakeNetwork())
        row=engine.start(Profile(skills=['Python'],current_role='Software Engineer'),Preferences(roles=['Python Engineer'],work_modes=['remote']),SourceConfig())
        await engine.tasks[row['id']]
        result=store.get('searches',row['id'])
        assert result['status']=='completed'
        assert len(result['results'])==50
        assert any(s['status']=='Authentication required' for s in result['sources'])
        assert result['counts']['discovered']==65
    asyncio.run(run())


def test_pipeline_cancel_no_fabricated_results(store,monkeypatch):
    async def slow(*a):await asyncio.sleep(20)
    monkeypatch.setattr(ATS,'search',slow)
    async def run():
        engine=Engine(store,FakeNetwork())
        row=engine.start(Profile(),Preferences(roles=['Engineer'],work_modes=['remote']),SourceConfig(greenhouse=['test']))
        await asyncio.sleep(.01)
        await engine.cancel(row['id'])
        assert store.get('searches',row['id'])['status']=='cancelled'
        assert store.get('searches',row['id'])['results']==[]
    asyncio.run(run())


def test_api_session_origin_validation_upload_and_delete(tmp_path):
    with TestClient(create_app(tmp_path),base_url='http://127.0.0.1:8765') as c:
        assert c.get('/api/bootstrap').status_code==403
        assert c.get('/api/session',headers={'Origin':'https://evil.example'}).status_code==403
        assert c.get('/api/session',headers={'Host':'evil.example'}).status_code==400
        token=c.get('/api/session').json()['token'];c.headers['X-Local-Token']=token
        assert c.get('/api/bootstrap').json()['profile']['name']==''
        r=c.post('/api/profile/upload',files={'file':('resume.txt',b'Candidate\nPython developer\n3 years experience\nPython, SQL','text/plain')})
        assert r.status_code==200,r.text
        assert r.json()['experience_years']==3
        assert c.put('/api/profile',json=r.json()).status_code==200
        assert c.post('/api/searches',json={'preferences':{'roles':['Engineer'],'limit':51}}).status_code==422
        assert c.post('/api/profile/upload',files={'file':('evil.exe',b'abc')}).status_code==422
        assert c.put('/api/llm',json={'enabled':True,'consent':False,'model':'model'}).status_code==422
        assert c.delete('/api/data').status_code==200
        assert c.get('/api/bootstrap').json()['profile']['name']==''


def test_demo_does_not_persist_fake_profile_or_preferences(tmp_path):
    with TestClient(create_app(tmp_path),base_url='http://127.0.0.1:8765') as c:
        c.headers['X-Local-Token']=c.get('/api/session').json()['token']
        response=c.post('/api/searches',json={'demo':True,'preferences':{'roles':['Social Media Manager'],'work_modes':['remote'],'limit':10}})
        assert response.status_code==200
        data=c.get('/api/bootstrap').json()
        assert data['profile']['name']=='' and data['preferences']['roles']==[]


def test_model_bounds_and_trimming():
    assert Profile(skills=[' Python ','','Python']).skills==['Python']
    with pytest.raises(ValidationError):Preferences(work_modes=[])
    with pytest.raises(ValidationError):Point(latitude=float('nan'),longitude=77)
    with pytest.raises(ValidationError):Salary(minimum=9,maximum=2)
