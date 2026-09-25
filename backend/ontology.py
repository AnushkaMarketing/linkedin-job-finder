"""Explicit aliases and directional transferable-skill relationships.

Related skills earn partial credit; they never become user qualifications.
"""
import re
from functools import lru_cache

ALIASES: dict[str, list[str]] = {
    'Python': ['python', 'python 3', 'python programming', 'py'],
    'React': ['react', 'react.js', 'reactjs'], 'JavaScript': ['javascript', 'js', 'ecmascript'],
    'TypeScript': ['typescript', 'ts'], 'SQL': ['sql', 'structured query language'],
    'FastAPI': ['fastapi', 'fast api'], 'Django': ['django'], 'Node.js': ['node.js', 'nodejs'],
    'Machine Learning': ['machine learning', 'ml'], 'Deep Learning': ['deep learning'],
    'PyTorch': ['pytorch'], 'TensorFlow': ['tensorflow'], 'AI': ['artificial intelligence', 'ai'],
    'Computer Vision': ['computer vision'], 'NLP': ['nlp', 'natural language processing'],
    'AWS': ['aws', 'amazon web services'], 'GCP': ['gcp', 'google cloud platform'],
    'Azure': ['azure', 'microsoft azure'], 'Docker': ['docker'], 'Kubernetes': ['kubernetes', 'k8s'],
    'Git': ['git'], 'Excel': ['excel', 'microsoft excel'], 'Power BI': ['power bi', 'powerbi'],
    'SEO': ['seo', 'search engine optimization', 'search engine optimisation'],
    'GA4': ['ga4', 'google analytics 4', 'google analytics'],
    'Search Console': ['google search console', 'search console', 'gsc'],
    'Social Media': ['social media', 'social media marketing', 'social media management'],
    'Copywriting': ['copywriting', 'copy writing'], 'Content Strategy': ['content strategy', 'content planning'],
    'Content Writing': ['content writing', 'content writer', 'blog writing'],
    'LinkedIn Marketing': ['linkedin marketing', 'linkedin campaigns'],
    'Instagram': ['instagram'], 'Short-form Video': ['reels', 'short-form video', 'short form video'],
    'Canva': ['canva'], 'Figma': ['figma'], 'Adobe Photoshop': ['photoshop', 'adobe photoshop'],
    'Meta Business Suite': ['meta business suite', 'facebook business suite'],
    'Google Ads': ['google ads', 'adwords'], 'Meta Ads': ['meta ads', 'facebook ads'],
    'Email Marketing': ['email marketing'], 'WordPress': ['wordpress'],
    'B2B Marketing': ['b2b marketing', 'b2b storytelling', 'b2b communication'],
    'Campaign Management': ['campaign management', 'campaign planning'],
    'Analytics': ['analytics', 'performance reporting', 'data analysis'],
    'Communication': ['communication', 'stakeholder communication'],
    'Leadership': ['leadership', 'team management'], 'UX Research': ['ux research', 'user research'],
}
RELATED: dict[str, dict[str, float]] = {
    'PyTorch': {'Deep Learning': .8, 'Machine Learning': .65, 'AI': .5, 'Computer Vision': .35},
    'TensorFlow': {'Deep Learning': .8, 'Machine Learning': .65},
    'React': {'JavaScript': .55, 'TypeScript': .25}, 'FastAPI': {'Python': .6},
    'GA4': {'Analytics': .8, 'SEO': .3}, 'Search Console': {'SEO': .65, 'Analytics': .5},
    'Copywriting': {'Content Writing': .65, 'Content Strategy': .35},
    'Content Writing': {'Copywriting': .55, 'Content Strategy': .35},
    'Social Media': {'Content Strategy': .45, 'Campaign Management': .45, 'LinkedIn Marketing': .35},
    'Instagram': {'Social Media': .6, 'Short-form Video': .25},
    'Canva': {'Figma': .25, 'Adobe Photoshop': .2},
    'AWS': {'GCP': .3, 'Azure': .3}, 'GCP': {'AWS': .3, 'Azure': .3},
}
ROLE_FAMILIES = {
    'ai': ['AI Engineer', 'Machine Learning Engineer', 'ML Engineer', 'Applied AI Engineer', 'Generative AI Engineer'],
    'software': ['Software Engineer', 'Software Developer', 'Backend Developer', 'Full Stack Developer'],
    'social': ['Social Media Executive', 'Social Media Specialist', 'Social Media Marketer', 'Social Media Marketing Executive'],
    'content': ['Content Writer', 'Content Executive', 'Content Marketing Specialist', 'Copywriter'],
    'marketing': ['Digital Marketing Executive', 'Digital Marketing Specialist', 'Marketing Executive'],
    'design': ['Product Designer', 'UX Designer', 'UI Designer'],
    'data': ['Data Scientist', 'Data Analyst', 'Analytics Engineer'],
}

def norm(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


@lru_cache(maxsize=4096)
def canonical(value: str) -> str:
    key = norm(value)
    return next((name for name, aliases in ALIASES.items() if key in [norm(a) for a in aliases]), value.strip())


def extract_skills(text: str) -> list[str]:
    found = []
    for name, aliases in ALIASES.items():
        if _patterns[name].search(text):
            found.append(name)
    return found


_patterns = {name:re.compile(r'(?<![\w])(?:'+ '|'.join(re.escape(a) for a in aliases) +r')(?![\w])',re.I) for name,aliases in ALIASES.items()}


def relation(owned: list[str], required: str) -> tuple[float, str, str]:
    required = canonical(required)
    values = list(dict.fromkeys(canonical(s) for s in owned))
    if required in values:
        return 1, 'Exact', required
    score, skill = max(((RELATED.get(s, {}).get(required, 0), s) for s in values), default=(0, ''))
    label = 'Strongly related' if score >= .7 else 'Related' if score >= .4 else 'Weakly related' if score else 'Unknown'
    return score, label, skill


def seniority(title: str) -> str:
    for label, terms in [('leadership', r'director|head of|vice president'), ('senior', r'\bsenior\b|\bsr\b|\blead\b|manager'), ('entry', r'intern|junior|graduate|trainee')]:
        if re.search(terms, title, re.I):
            return label
    return ''


def role_family(title: str) -> str:
    n = norm(title)
    return next((family for family, titles in ROLE_FAMILIES.items() if any(norm(t) in n or n == norm(t) for t in titles)), '')


def role_similarity(a: str, b: str) -> float:
    if norm(a) == norm(b):
        return 1
    if role_family(a) and role_family(a) == role_family(b):
        return .85
    x, y = set(norm(a).split()), set(norm(b).split())
    return len(x & y) / max(1, len(x | y))
