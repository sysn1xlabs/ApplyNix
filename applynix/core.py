"""Offline, extractive application preparation with source provenance."""
import copy
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SKILLS = {
    'Windows': ['windows', 'windows 10', 'windows 11'],
    'Linux': ['linux'], 'Active Directory': ['active directory'],
    'Microsoft 365': ['microsoft 365', 'office 365', 'm365'],
    'Outlook': ['outlook'], 'Teams': ['microsoft teams'],
    'DNS': ['dns'], 'DHCP': ['dhcp'], 'VPN': ['vpn'],
    'TCP/IP': ['tcp/ip', 'tcp ip'], 'PowerShell': ['powershell'],
    'ServiceNow': ['servicenow'], 'Ticketing': ['ticketing', 'ticket management', 'itsm'],
    'ITIL': ['itil'], 'Printers': ['printer', 'printers'],
    'Hardware': ['hardware'], 'SIEM': ['siem'], 'Splunk': ['splunk'],
    'Nessus': ['nessus'], 'Wireshark': ['wireshark'], 'Python': ['python'],
    'AWS': ['aws', 'amazon web services'], 'Azure': ['azure'],
    'SQL': ['sql'], 'Docker': ['docker'], 'Kubernetes': ['kubernetes'],
    'CEH': ['ceh'], 'CompTIA A+': ['comptia a+'],
}
STATUSES = ('TAILORED', 'READY', 'APPLIED', 'HR_CONTACT', 'INTERVIEW', 'REJECTED', 'WITHDRAWN', 'OFFER', 'HIRED')

def mentions(text, term):
    return bool(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I))

def skills_in(text):
    return [name for name, terms in SKILLS.items() if any(mentions(text, t) for t in terms)]

def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError('Profile must be a JSON object.')
    if not isinstance(profile.get('personal'), dict) or not profile['personal'].get('name'):
        raise ValueError('Profile needs personal.name.')
    if not isinstance(profile.get('skills'), list) or not all(isinstance(s, str) and s.strip() for s in profile['skills']):
        raise ValueError('skills must be a list of nonempty strings.')
    if not all(isinstance(v, str) for v in profile['personal'].values()):
        raise ValueError('Personal fields must be strings.')
    for key in ('experience', 'education', 'certifications', 'projects'):
        if not isinstance(profile.get(key, []), list):
            raise ValueError(key + ' must be a list.')
    for row in profile.get('experience', []):
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip() for k in ('company', 'title')):
            raise ValueError('Each experience needs company and title.')
        if not isinstance(row.get('dates', ''), str):
            raise ValueError('Experience dates must be a string.')
        if not isinstance(row.get('bullets', []), list) or not all(isinstance(s, str) for s in row.get('bullets', [])):
            raise ValueError('Experience bullets must be strings.')
    for key in ('education', 'certifications'):
        if not all(isinstance(s, str) for s in profile.get(key, [])):
            raise ValueError(key + ' entries must be strings.')
    if not isinstance(profile.get('summary', ''), str):
        raise ValueError('summary must be a string.')
    return profile

def analyze(text, profile):
    if not isinstance(text, str) or not text.strip() or len(text) > 200000:
        raise ValueError('Job description must contain 1–200000 characters.')
    validate_profile(profile)
    required, preferred, unknown = set(), set(), set()
    lines = text.splitlines()
    section = 'unknown'
    for line in lines:
        low = line.lower().strip()
        if re.match(r'^(required|required skills|requirements|qualifications|must have|essential)\b', low):
            section = 'required'
        elif re.match(r'^(preferred|desirable|nice to have|bonus)\b', low):
            section = 'preferred'
        elif re.match(r'^(responsibilities|duties|benefits|about|what we offer)\b', low):
            section = 'unknown'
        category = 'preferred' if re.search(r'preferred|nice.to.have|desirable|optional', low) else 'required' if re.search(r'\brequired\b|\bmust\b|mandatory|essential', low) else section
        {'required': required, 'preferred': preferred, 'unknown': unknown}[category].update(skills_in(line))
    preferred -= required
    unknown -= required | preferred
    evidenced = set(skills_in('\n'.join(profile['skills'])))
    reqs = [{'skill': s, 'classification': kind, 'matched': s in evidenced}
            for kind, group in [('required', required), ('preferred', preferred), ('unknown', unknown)] for s in sorted(group)]
    weights = {'required': 3, 'preferred': 1, 'unknown': 1}
    denom = sum(weights[r['classification']] for r in reqs)
    score = round(100 * sum(weights[r['classification']] for r in reqs if r['matched']) / denom) if denom else None
    risks = []
    for pattern, label in [(r'registration fee|training fee|security deposit|pay.*to apply', 'Payment request: verify independently.'), (r'\bunpaid\b', 'Unpaid role mentioned.'), (r'citizenship|security clearance|work authori[sz]ation|sponsorship', 'Eligibility requirement: user review needed.'), (r'\b\d+\+?\s*(?:years?|yrs?)', 'Experience requirement: compare dates manually.')]:
        if re.search(pattern, text, re.I):
            risks.append(label)
    def metadata(label):
        match = re.search(r'^(?:' + label + r')\s*:\s*(.+)$', text, re.I | re.M)
        return match.group(1).strip() if match else ''
    return {'company': metadata('company') or 'Unspecified company', 'title': metadata('title|role|job title') or 'Unspecified role', 'location': metadata('location') or 'Unknown', 'requirements': reqs, 'keyword_match': score, 'risks': risks, 'method': 'Weighted vocabulary coverage: required ×3, preferred/unknown ×1. This is not a hiring probability. Experience, eligibility, salary and location are not scored.'}

def fingerprint(profile, text):
    return hashlib.sha256((json.dumps(profile, sort_keys=True, ensure_ascii=False) + '\n' + text).encode()).hexdigest()

def prepare(profile, text, *, _verify=True):
    profile = copy.deepcopy(validate_profile(profile))
    analysis = analyze(text, profile)
    relevant = set(skills_in(text))
    ranked = sorted(enumerate(profile['skills']), key=lambda x: -len(set(skills_in(x[1])) & relevant))
    claims = []
    def claim(value, source):
        claims.append({'text': value, 'source': source})
        return value
    personal = profile['personal']
    out = ['# ' + str(personal['name']), ' | '.join(str(personal[k]) for k in ('email', 'phone', 'location') if personal.get(k)), '']
    if profile.get('summary'):
        out += ['## Summary', claim(profile['summary'], 'summary'), '']
    out += ['## Skills', ', '.join(claim(s, f'skills.{i}') for i, s in ranked), '', '## Experience']
    changes = [{'kind': 'skill_order', 'before': profile['skills'], 'after': [s for _, s in ranked]}]
    for i, job in enumerate(profile.get('experience', [])):
        out += ['### ' + claim(job['title'], f'experience.{i}.title') + ' — ' + claim(job['company'], f'experience.{i}.company')]
        if job.get('dates'):
            out += [claim(job['dates'], f'experience.{i}.dates')]
        bullets = sorted(enumerate(job.get('bullets', [])), key=lambda x: -len(set(skills_in(x[1])) & relevant))
        out += ['- ' + claim(b, f'experience.{i}.bullets.{j}') for j, b in bullets] + ['']
        changes.append({'kind': f'experience.{i}.bullet_order', 'before': job.get('bullets', []), 'after': [b for _, b in bullets]})
    for key in ('education', 'certifications'):
        if profile.get(key):
            out += ['## ' + key.title()] + ['- ' + claim(value, f'{key}.{i}') for i, value in enumerate(profile[key])] + ['']
    bundle = {'analysis': analysis, 'resume': '\n'.join(out), 'claims': claims, 'changes': changes, 'profile_snapshot': profile, 'job_description': text, 'fingerprint': fingerprint(profile, text)}
    if _verify:
        verify(bundle)
    return bundle

def verify(bundle):
    if fingerprint(bundle['profile_snapshot'], bundle['job_description']) != bundle['fingerprint']:
        raise ValueError('Profile/job snapshot integrity failure.')
    for c in bundle['claims']:
        value = bundle['profile_snapshot']
        for part in c['source'].split('.'):
            value = value[int(part)] if isinstance(value, list) else value[part]
        if value != c['text']:
            raise ValueError('Unsupported claim: ' + c['source'])
    expected = prepare(bundle['profile_snapshot'], bundle['job_description'], _verify=False)
    if bundle != expected:
        raise ValueError('Draft differs from grounded source; prepare again.')

def bundle_digest(bundle):
    return hashlib.sha256(json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, created TEXT, company TEXT, title TEXT, status TEXT, bundle TEXT, digest TEXT);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, application_id TEXT, time TEXT, action TEXT, note TEXT);''')
    def save(self, bundle):
        verify(bundle)
        identity = bundle['fingerprint'][:16]
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO applications VALUES (?,?,?,?,?,?,?)', (identity, now(), bundle['analysis']['company'], bundle['analysis']['title'], 'TAILORED', json.dumps(bundle), bundle_digest(bundle)))
            if self.db.execute('SELECT changes()').fetchone()[0]:
                self.db.execute('INSERT INTO events(application_id,time,action,note) VALUES (?,?,?,?)', (identity, now(), 'PREPARED', 'Extractive draft created'))
        return identity
    def list(self):
        return [dict(r) for r in self.db.execute('SELECT id,created,company,title,status FROM applications ORDER BY created DESC')]
    def get(self, identity):
        row = self.db.execute('SELECT * FROM applications WHERE id=?', (identity,)).fetchone()
        if not row:
            raise ValueError('Application not found.')
        result = dict(row)
        result['bundle'] = json.loads(result['bundle'])
        if bundle_digest(result['bundle']) != result['digest']:
            raise ValueError('Stored draft changed; prepare and review again.')
        verify(result['bundle'])
        return result
    def status(self, identity, status, note=''):
        record = self.get(identity)
        if status not in STATUSES:
            raise ValueError('Invalid status.')
        if status == 'READY' and record['status'] != 'TAILORED':
            raise ValueError('Only a tailored draft can be approved.')
        if status == 'APPLIED' and (record['status'] != 'READY' or not note.strip()):
            raise ValueError('Approve first, then provide a manual submission receipt/note.')
        if status not in ('TAILORED', 'READY', 'APPLIED') and record['status'] in ('TAILORED', 'READY'):
            raise ValueError('Record manual submission before recruitment outcomes.')
        with self.db:
            self.db.execute('UPDATE applications SET status=? WHERE id=?', (status, identity))
            self.db.execute('INSERT INTO events(application_id,time,action,note) VALUES (?,?,?,?)', (identity, now(), status, note))
    def events(self, identity):
        self.get(identity)
        return [dict(r) for r in self.db.execute('SELECT time,action,note FROM events WHERE application_id=? ORDER BY id', (identity,))]

def now():
    return datetime.now(timezone.utc).isoformat()

def export(bundle, directory):
    verify(bundle)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'resume.md').write_text(bundle['resume'], encoding='utf-8')
    (directory / 'job-description.txt').write_text(bundle['job_description'], encoding='utf-8')
    (directory / 'review.json').write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding='utf-8')
    import html
    # Plain, print-friendly HTML; browser Print → Save as PDF.
    lines = []
    for line in bundle['resume'].splitlines():
        escaped = html.escape(line)
        level = len(line) - len(line.lstrip('#'))
        lines.append(f'<h{level}>{html.escape(line[level:].strip())}</h{level}>' if 1 <= level <= 3 else '<p>' + escaped + '</p>')
    (directory / 'resume.html').write_text('<!doctype html><meta charset="utf-8"><title>Resume</title><style>body{font:11pt Arial;max-width:760px;margin:40px auto;line-height:1.4}h1{font-size:24pt}h2{font-size:14pt;border-bottom:1px solid #bbb}h3{font-size:12pt}p{margin:5px 0}@media print{body{margin:0}h2,h3{break-after:avoid}}</style>' + ''.join(lines), encoding='utf-8')
