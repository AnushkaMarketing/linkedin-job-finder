from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from urllib.parse import urlsplit


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_max_length=100_000, allow_inf_nan=False)

    @field_validator('*', mode='before')
    @classmethod
    def trim_lists(cls, value):
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return list(dict.fromkeys(v.strip() for v in value if v.strip()))
        return value


class Evidence(Model):
    source: str
    confidence: float = Field(ge=0, le=1)
    kind: Literal['observed', 'user', 'inferred', 'unavailable'] = 'observed'
    note: str = ''
    checked_at: str = Field(default_factory=now)


class Salary(Model):
    minimum: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    currency: str = ''
    period: Literal['year', 'month', 'hour', 'unknown'] = 'year'
    text: str = ''

    @model_validator(mode='after')
    def ordered(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError('Minimum salary must not exceed maximum')
        return self


class Point(Model):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    precision: Literal['office', 'neighborhood', 'city', 'user'] = 'user'
    source: str = 'User supplied coordinates'


class Profile(Model):
    name: str = ''
    experience_years: float | None = Field(default=None, ge=0, le=70)
    current_role: str = ''
    previous_roles: list[str] = Field(default_factory=list, max_length=50)
    skills: list[str] = Field(default_factory=list, max_length=150)
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    seniority: str = ''
    location: str = ''
    preferred_locations: list[str] = Field(default_factory=list)
    salary_expectation: Salary = Field(default_factory=lambda: Salary(currency='INR'))
    work_mode: list[str] = Field(default_factory=list)
    employment_type: list[str] = Field(default_factory=list)
    notice_period: str = ''
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class Preferences(Model):
    roles: list[str] = Field(default_factory=list, max_length=8)
    location: str = ''
    origin: Point | None = None
    radius_km: float = Field(default=15, gt=0, le=20000)
    strict_radius: bool = True
    work_modes: list[Literal['on-site', 'hybrid', 'remote']] = Field(default_factory=lambda: ['on-site', 'hybrid'], min_length=1)
    employment_types: list[str] = Field(default_factory=list)
    experience_min: float | None = Field(default=None, ge=0, le=70)
    experience_max: float | None = Field(default=None, ge=0, le=70)
    salary: Salary = Field(default_factory=lambda: Salary(currency='INR'))
    industries: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=50)

    @model_validator(mode='after')
    def ordered(self):
        if self.experience_min is not None and self.experience_max is not None and self.experience_min > self.experience_max:
            raise ValueError('Experience minimum must not exceed maximum')
        return self


def web_url(value: str) -> str:
    if not value:
        return value
    p = urlsplit(value)
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        raise ValueError('A public http(s) URL without embedded credentials is required')
    return value


class Job(Model):
    job_id: str = ''
    source: str = 'Manual import'
    title: str = Field(min_length=1, max_length=250)
    company: str = Field(min_length=1, max_length=250)
    description: str = Field(default='', max_length=60_000)
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_min: float | None = Field(default=None, ge=0, le=70)
    experience_max: float | None = Field(default=None, ge=0, le=70)
    salary: Salary = Field(default_factory=Salary)
    location: str = ''
    coordinates: Point | None = None
    work_mode: Literal['on-site', 'hybrid', 'remote', 'unknown'] = 'unknown'
    employment_type: str = ''
    seniority: str = ''
    industry: str = ''
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    posted_date: str = ''
    valid_through: str = ''
    application_url: str = ''
    company_url: str = ''
    source_url: str = ''
    remote_restrictions: str = ''
    collected_at: str = Field(default_factory=now)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    corroborating_urls: list[str] = Field(default_factory=list)
    state: Literal['new', 'saved', 'ignored', 'viewed', 'applied'] = 'new'

    _urls = field_validator('application_url', 'company_url', 'source_url')(web_url)


class SourceConfig(Model):
    greenhouse: list[str] = Field(default_factory=list, max_length=8)
    lever: list[str] = Field(default_factory=list, max_length=8)
    career_pages: list[str] = Field(default_factory=list, max_length=8)
    remotive: bool = False
    manual: bool = True

    @field_validator('greenhouse', 'lever')
    @classmethod
    def slugs(cls, values):
        import re
        if any(not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', v) for v in values):
            raise ValueError('Board IDs must contain only letters, digits, hyphens or underscores')
        return values


class LLMConfig(Model):
    enabled: bool = False
    endpoint: str = 'http://127.0.0.1:11434/v1'
    model: str = ''
    api_key: str = ''
    consent: bool = False


class SearchRequest(Model):
    preferences: Preferences
    demo: bool = False


class Factor(Model):
    name: str
    score: float | None = None
    weight: float
    explanation: str


class Verification(Model):
    status: Literal['Verified', 'Partially verified', 'Unable to verify', 'Conflicting information'] = 'Unable to verify'
    confidence: float = Field(default=0, ge=0, le=1)
    checks: list[dict] = Field(default_factory=list)
    company_information: dict = Field(default_factory=dict)
    note: str = 'Public evidence does not establish company legitimacy.'


class RankedJob(Model):
    intelligence: dict = Field(default_factory=dict)
    job: Job
    cv_fit: float | None
    preference_fit: float | None
    priority: float
    coverage: float
    distance_km: float | None
    location_status: str
    factors: list[Factor]
    strengths: list[str]
    gaps: list[str]
    related: list[str]
    analysis: dict
    readiness: list[str]
    verification: Verification = Field(default_factory=Verification)
    llm_advice: dict | None = None
