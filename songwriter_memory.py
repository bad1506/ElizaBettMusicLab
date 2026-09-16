from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from storage_backend import get_storage_backend

DEFAULT_MEMORY = {'version':'1.0','updated_at':None,'songs':[],'notes':[]}
DEFAULT_DNA = {
    'version':'1.0','updated_at':None,'identity':'','genres':[],'themes':[],'motifs':[],
    'language_style':[],'hook_patterns':[],'structure_patterns':[],'rhyme_preferences':[],
    'avoid':[],'strengths':[],'growth_areas':[],'signature_phrases':[],'evidence_count':0
}


def _paths(user_id: str = 'local'):
    data_dir = get_storage_backend(Path(__file__).resolve().parent).user_root(user_id) / 'songwriter_data'
    return data_dir, data_dir / 'memory.json', data_dir / 'artist_dna.json'


def _ensure(user_id='local'):
    data_dir, memory_file, profile_file = _paths(user_id)
    data_dir.mkdir(parents=True, exist_ok=True)
    if not memory_file.exists(): memory_file.write_text(json.dumps(DEFAULT_MEMORY, ensure_ascii=False, indent=2), encoding='utf-8')
    if not profile_file.exists(): profile_file.write_text(json.dumps(DEFAULT_DNA, ensure_ascii=False, indent=2), encoding='utf-8')


def _read(path, default, user_id='local'):
    _ensure(user_id)
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default.copy()


def _write(path, data, user_id='local'):
    _ensure(user_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def memory(user_id='local'):
    return _read(_paths(user_id)[1], DEFAULT_MEMORY, user_id)


def dna(user_id='local'):
    return _read(_paths(user_id)[2], DEFAULT_DNA, user_id)


def add_song(title, text, mode='SONG', tags=None, metadata=None, user_id='local'):
    data = memory(user_id); now = datetime.now(timezone.utc).isoformat()
    item = {'id': now.replace(':','').replace('+','_'), 'title': title or 'Untitled draft', 'mode': mode, 'text': text, 'tags': tags or [], 'metadata': metadata or {}, 'created_at': now}
    data['songs'].insert(0, item); data['songs'] = data['songs'][:100]; data['updated_at'] = now
    _write(_paths(user_id)[1], data, user_id); return item


def add_note(note, user_id='local'):
    data = memory(user_id); now = datetime.now(timezone.utc).isoformat()
    data['notes'].insert(0, {'text': note, 'created_at': now}); data['notes'] = data['notes'][:100]; data['updated_at'] = now
    _write(_paths(user_id)[1], data, user_id); return data['notes'][0]


def recent(limit=8, user_id='local'):
    return memory(user_id).get('songs', [])[:max(1, min(limit, 30))]


def build_local_dna(user_id='local'):
    songs = memory(user_id).get('songs', [])
    text = '\n'.join(s.get('text','') for s in songs)
    themes = []
    for term, label in [('любов','love'),('расстав','breakup'),('ноч','night'),('город','city'),('голов','mind'),('время','time'),('дорог','road'),('один','solitude')]:
        if len(re.findall(term, text, re.I)) >= 2: themes.append(label)
    phrases = []
    for s in songs:
        for line in re.split(r'\n+', s.get('text','')):
            line = re.sub(r'^\[[^\]]+\]\s*','',line).strip(' -—')
            if 4 <= len(line.split()) <= 10 and ('я ' in line.lower() or 'ты ' in line.lower()): phrases.append(line)
    dna0 = dna(user_id)
    dna0.update({'updated_at':datetime.now(timezone.utc).isoformat(),'evidence_count':len(songs),'themes':sorted(set(themes)),'signature_phrases':phrases[:12], 'identity':'Русскоязычный автор, работающий через личную исповедь, контраст внешнего и внутреннего состояния и короткие запоминающиеся hooks.' if songs else ''})
    if songs:
        dna0['strengths'] = list(dict.fromkeys((dna0.get('strengths') or []) + ['hook-first thinking','эмоциональная конкретика','разговорная подача']))[:8]
        dna0['avoid'] = list(dict.fromkeys((dna0.get('avoid') or []) + ['пустые клише','перегруженные рифмы','длинные строки без певучести']))[:8]
    _write(_paths(user_id)[2], dna0, user_id); return dna0
