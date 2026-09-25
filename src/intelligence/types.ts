export type Salary = {
  minimum: number | null;
  maximum: number | null;
  currency: string;
  period: "year" | "month" | "hour" | "unknown";
  text: string;
};
export type Point = {
  latitude: number;
  longitude: number;
  precision: "office" | "neighborhood" | "city" | "user";
  source: string;
};
export type Evidence = {
  source: string;
  confidence: number;
  kind: string;
  note: string;
  checked_at: string;
};
export type Profile = {
  name: string;
  experience_years: number | null;
  current_role: string;
  previous_roles: string[];
  skills: string[];
  technical_skills: string[];
  soft_skills: string[];
  industries: string[];
  education: string[];
  certifications: string[];
  projects: string[];
  companies: string[];
  preferred_roles: string[];
  seniority: string;
  location: string;
  preferred_locations: string[];
  salary_expectation: Salary;
  work_mode: string[];
  employment_type: string[];
  notice_period: string;
  evidence: Record<string, Evidence>;
  warnings: string[];
};
export type Mode = "on-site" | "hybrid" | "remote";
export type Preferences = {
  roles: string[];
  location: string;
  origin: Point | null;
  radius_km: number;
  strict_radius: boolean;
  work_modes: Mode[];
  employment_types: string[];
  experience_min: number | null;
  experience_max: number | null;
  salary: Salary;
  industries: string[];
  excluded_companies: string[];
  limit: number;
};
export type Sources = {
  greenhouse: string[];
  lever: string[];
  career_pages: string[];
  remotive: boolean;
  manual: boolean;
};
export type LLM = {
  enabled: boolean;
  endpoint: string;
  model: string;
  api_key?: string;
  consent: boolean;
  key_saved?: boolean;
};
export type JobState = "new" | "saved" | "ignored" | "viewed" | "applied";
export type Job = {
  job_id: string;
  source: string;
  title: string;
  company: string;
  description: string;
  skills: string[];
  experience_min: number | null;
  experience_max: number | null;
  salary: Salary;
  location: string;
  coordinates: Point | null;
  work_mode: Mode | "unknown";
  employment_type: string;
  posted_date: string;
  application_url: string;
  company_url: string;
  source_url: string;
  remote_restrictions: string;
  collected_at: string;
  evidence: Record<string, Evidence>;
  state: JobState;
  corroborating_urls: string[];
};
export type Factor = {
  name: string;
  score: number | null;
  weight: number;
  explanation: string;
};
export type Ranked = {
  intelligence?: {
    version: string;
    requirements: {
      skills: string[];
      importance: string;
      operator: string;
      evidence: string;
      score: number;
      relationship: string;
      via: string;
    }[];
    required_count: number;
    required_missing: number;
    flags: string[];
    questions: string[];
    priority_adjustment: number;
    priority_cap?: number;
    priority_cap_reason?: string;
    feedback_labels?: number;
    method: string;
  };
  job: Job;
  cv_fit: number | null;
  preference_fit: number | null;
  priority: number;
  coverage: number;
  distance_km: number | null;
  location_status: string;
  factors: Factor[];
  strengths: string[];
  gaps: string[];
  related: string[];
  analysis: Record<
    string,
    (string | { signal: string; evidence: string; kind: string })[]
  >;
  readiness: string[];
  verification: {
    status: string;
    confidence: number;
    checks: { check: string; status: string; source: string }[];
    company_information?: Record<
      string,
      { value: unknown; source: string; kind: string; confidence: number }
    >;
    note: string;
  };
  llm_advice: {
    summary: string;
    kind: string;
    evidence_quotes: string[];
    questions_to_ask: string[];
  } | null;
};
export type Run = {
  insights?: {
    gap_opportunities: { skill: string; jobs: number }[];
    needs_office_confirmation: number;
    low_evidence: number;
    employers: number;
    note: string;
  };
  id: string;
  demo: boolean;
  status: string;
  stage: string;
  started_at: string;
  elapsed: number;
  plan: {
    roles: string[];
    requested_roles: string[];
    strategies: { name: string; queries: string[] }[];
  };
  preferences: Preferences;
  sources: { source: string; status: string; count: number; detail: string }[];
  results: Ranked[];
  counts: Record<string, number>;
  exclusions: Record<string, number>;
  warnings: string[];
  linkedin: { role: string; url: string }[];
  network?: { requests: number; cache_hits: number };
};
export type History = Pick<
  Run,
  "id" | "demo" | "status" | "stage" | "started_at" | "counts"
>;
export type Bootstrap = {
  profile: Profile;
  preferences: Preferences;
  sources: Sources;
  llm: LLM;
  history: History[];
  imports: number;
  version: string;
};
