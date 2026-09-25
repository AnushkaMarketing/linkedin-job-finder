import pytest
from backend.intelligence import requirements, skill_assessment, retrieve, shortlist_insights
from backend.learning import train, personalized_rank, profile_key
from backend.models import Profile,Job,Preferences
from backend.matching import match_job,rank
from backend.normalize import normalize


def test_alternatives_and_conjunction_are_separate():
    job=Job(title='Developer',company='Example',description='Required\nPython or Java and SQL')
    result=skill_assessment(job,Profile(skills=['Python','SQL']))
    assert result['required_count']==2 and result['score']==100
    assert not result['required_missing']


def test_negated_requirement_not_resurrected_by_normalization():
    job=normalize(Job(title='Developer',company='Example',description='Python is not required'))
    assert job.skills==['Python']
    assert requirements(job)==[]


def test_preferred_is_lower_weight():
    job=Job(title='Developer',company='Example',description='Required\nPython\nPreferred\nKubernetes')
    strong=skill_assessment(job,Profile(skills=['Python']))
    weak=skill_assessment(job,Profile(skills=['Kubernetes']))
    assert strong['score']==75 and weak['score']==25
    assert strong['required_missing']==0 and weak['required_missing']==1


def test_bm25_candidates_retain_relevant_description():
    jobs=[Job(title='Specialist',company='A',description='Account reconciliation invoices'),Job(title='Specialist',company='B',description='Build SEO campaigns and content strategy')]
    found=retrieve(jobs,Profile(skills=['SEO']),Preferences(roles=['Content Strategist']),limit=1)
    assert found[0].company=='B'


def test_learning_needs_both_classes_and_enough_labels():
    assert not train([{'label':'relevant','features':[1]*10}]*20)['ready']
    assert not train([{'label':'relevant','features':[1]*10}]*3+[{'label':'not_relevant','features':[-1]*10}]*3)['ready']


def test_trained_preference_is_deterministic_and_bounded():
    labels=[{'label':'relevant','features':[.8]*10}]*5+[{'label':'not_relevant','features':[-.8]*10}]*5
    model=train(labels)
    assert model['ready'] and model==train(labels)
    row=match_job(Profile(skills=['Python'],current_role='Engineer'),normalize(Job(title='Engineer',company='A',skills=['Python'],work_mode='remote')),Preferences(roles=['Engineer'],work_modes=['remote']))
    base=rank([row])[0].priority
    personalized_rank([row],model)
    assert abs(row.priority-base)<=4.1
    assert row.cv_fit==100  # learning never rewrites qualifications


def test_profile_scope_excludes_identity_and_changes_with_skills():
    assert profile_key(Profile(name='Person A',skills=['Python']))==profile_key(Profile(name='Person B',skills=['Python']))
    assert profile_key(Profile(skills=['Python']))!=profile_key(Profile(skills=['SEO']))


def test_gap_opportunities_are_shortlist_counts():
    p=Profile(skills=['Python']);prefs=Preferences(roles=['Developer'])
    rows=[match_job(p,Job(title='Developer',company=f'C{i}',description='Required\nPython; Kubernetes'),prefs) for i in range(2)]
    insights=shortlist_insights(rows)
    assert insights['gap_opportunities']==[{'skill':'Kubernetes','jobs':2}]


def test_feedback_api_rejects_demo_and_unknown_search(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    with TestClient(create_app(tmp_path),base_url='http://127.0.0.1:8765') as client:
        client.headers['X-Local-Token']=client.get('/api/session').json()['token']
        assert client.get('/api/learning').json()['labels']==0
        assert client.post('/api/feedback',json={'search_id':'unknown','job_id':'x','label':'relevant'}).status_code==422
        assert client.delete('/api/learning').status_code==200


def test_feedback_replacement_training_and_profile_isolation(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    app=create_app(tmp_path)
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        client.headers['X-Local-Token']=client.get('/api/session').json()['token']
        profile=Profile(skills=['Python'],current_role='Developer')
        client.put('/api/profile',json=profile.model_dump())
        rows=[]
        for i in range(8):
            row=match_job(profile,normalize(Job(title='Developer',company=f'Example{i}',skills=['Python'] if i<4 else ['SEO'],work_mode='remote')),Preferences(roles=['Developer']))
            rows.append(row.model_dump())
        app.state.store.put('searches','test',{'demo':False,'profile_key':profile_key(profile),'results':rows})
        for i,row in enumerate(rows):
            response=client.post('/api/feedback',json={'search_id':'test','job_id':row['job']['job_id'],'label':'relevant' if i<4 else 'not_relevant'})
            assert response.status_code==200,response.text
        assert client.get('/api/learning').json()['ready']
        client.post('/api/feedback',json={'search_id':'test','job_id':rows[0]['job']['job_id'],'label':'not_relevant'})
        assert client.get('/api/learning').json()['labels']==8
        profile.skills=['SEO'];client.put('/api/profile',json=profile.model_dump())
        assert client.get('/api/learning').json()['labels']==0
        assert client.post('/api/feedback',json={'search_id':'test','job_id':rows[0]['job']['job_id'],'label':'relevant'}).status_code==422


def test_personalization_never_lifts_must_have_cap():
    row=match_job(Profile(skills=['Python']),Job(title='Engineer',company='A',description='Required\nKubernetes; AWS'),Preferences(roles=['Engineer']))
    row.priority=55;row.intelligence['priority_cap']=55
    model={'ready':True,'labels':10,'weights':[-10]*10}
    personalized_rank([row],model)
    assert row.priority<=55


def test_target_role_alone_is_not_cv_evidence():
    row=match_job(Profile(),Job(title='Developer',company='A'),Preferences(roles=['Developer']))
    assert row.cv_fit is None and row.coverage==0
