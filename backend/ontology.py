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

# Curated additions. These are explicit aliases, not a claim to reproduce ESCO.
ALIASES.update({
    'Content Marketing':['content marketing'], 'Performance Marketing':['performance marketing','paid acquisition'],
    'Marketing Automation':['marketing automation'], 'HubSpot':['hubspot'], 'Salesforce':['salesforce'],
    'Mailchimp':['mailchimp'], 'Klaviyo':['klaviyo'], 'CRM':['crm','customer relationship management'],
    'A/B Testing':['a/b testing','split testing','ab testing'], 'Conversion Optimization':['cro','conversion rate optimization','conversion optimisation'],
    'Google Tag Manager':['google tag manager','gtm'], 'Looker Studio':['looker studio','google data studio'],
    'Semrush':['semrush'], 'Ahrefs':['ahrefs'], 'Technical SEO':['technical seo'], 'Local SEO':['local seo'],
    'Influencer Marketing':['influencer marketing','creator partnerships'], 'Community Management':['community management'],
    'Brand Strategy':['brand strategy','brand positioning'], 'Storytelling':['storytelling','brand storytelling'],
    'Video Editing':['video editing'], 'Premiere Pro':['premiere pro','adobe premiere'], 'After Effects':['after effects'],
    'CapCut':['capcut'], 'YouTube':['youtube'], 'TikTok':['tiktok'], 'Pinterest':['pinterest'],
    'Shopify':['shopify'], 'E-commerce':['e-commerce','ecommerce'], 'Market Research':['market research'],
    'Competitor Research':['competitor research','competitive analysis'], 'Lead Generation':['lead generation','lead gen'],
    'Demand Generation':['demand generation','demand gen'], 'Product Marketing':['product marketing'],
    'Java':['java'], 'Go':['golang','go programming'], 'Rust':['rust programming','rust'],
    'PostgreSQL':['postgresql','postgres'], 'MongoDB':['mongodb'], 'Redis':['redis'],
    'Next.js':['next.js','nextjs'], 'Vue':['vue','vue.js','vuejs'], 'Angular':['angular'],
    'HTML':['html','html5'], 'CSS':['css','css3'], 'Tailwind CSS':['tailwind','tailwind css'],
    'REST APIs':['rest api','restful apis','rest apis'], 'GraphQL':['graphql'],
    'CI/CD':['ci/cd','continuous integration','continuous delivery'], 'Terraform':['terraform'],
    'Pandas':['pandas'], 'NumPy':['numpy'], 'scikit-learn':['scikit-learn','sklearn'],
    'RAG':['retrieval augmented generation','retrieval-augmented generation','rag'],
    'LLMs':['large language models','llms','large language model'], 'LangChain':['langchain'],
    'Tableau':['tableau'], 'Statistics':['statistics','statistical analysis'], 'Spark':['apache spark','pyspark'],
    'Accessibility':['accessibility','wcag'], 'Prototyping':['prototyping'], 'Design Systems':['design systems'],
})
RELATED.update({
    'Content Marketing':{'Content Strategy':.75,'Content Writing':.5,'SEO':.3},
    'HubSpot':{'CRM':.85,'Marketing Automation':.65,'Email Marketing':.5},
    'Salesforce':{'CRM':.85},'Mailchimp':{'Email Marketing':.8,'Marketing Automation':.45},
    'Google Ads':{'Performance Marketing':.7,'Analytics':.4},'Meta Ads':{'Performance Marketing':.7,'Social Media':.45},
    'Semrush':{'SEO':.6,'Competitor Research':.5},'Ahrefs':{'SEO':.6,'Competitor Research':.5},
    'Technical SEO':{'SEO':.85},'Local SEO':{'SEO':.7},'Premiere Pro':{'Video Editing':.85},
    'CapCut':{'Video Editing':.65,'Short-form Video':.5},'PostgreSQL':{'SQL':.85},
    'Next.js':{'React':.75,'JavaScript':.45},'Pandas':{'Python':.45,'Analytics':.6},
    'scikit-learn':{'Machine Learning':.8,'Python':.5},'RAG':{'LLMs':.6,'AI':.5},
    'Figma':{'Prototyping':.7,'Design Systems':.4},
})
ROLE_FAMILIES['social'] += ['Social Media Manager','Community Manager','Social Media Strategist']
ROLE_FAMILIES['content'] += ['Content Strategist','Content Marketing Manager','Content Marketer','Content Marketing Executive']
ROLE_FAMILIES['marketing'] += ['Digital Marketing Manager','Marketing Manager','Growth Marketing Specialist']
ROLE_FAMILIES['seo'] = ['SEO Executive','SEO Specialist','SEO Manager','Search Engine Optimization Specialist']
ROLE_FAMILIES['performance'] = ['Performance Marketing Manager','Paid Media Specialist','PPC Specialist']


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
