from __future__ import annotations
import json, os, re
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(os.getenv('ELIZA_DATA_DIR', '.')) / 'songwriter_data'
MEMORY_FILE = DATA_DIR / 'memory.json'
PROFILE_FILE = DATA_DIR / 'artist_dna.json'

DEFAULT_MEMORY = {'version':'1.0','updated_at':None,'songs':[],'notes':[]}
DEFAULT_DNA = {
    'version':'1.0','updated_at':None,'identity':'','genres':[],'themes':[],'motifs':[],
    'language_style':[],'hook_patterns':[],'structure_patterns':[],'rhyme_preferences':[],
    'avoid':[],'strengths':[],'growth_areas':[],'signature_phrases':[],'evidence_count':0
}

def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists(): MEMORY_FILE.write_text(json.dumps(DEFAULT_MEMORY,ensure_ascii=False,indent=2),encoding='utf-8')
    if not PROFILE_FILE.exists(): PROFILE_FILE.write_text(json.dumps(DEFAULT_DNA,ensure_ascii=False,indent=2),encoding='utf-8')

def _read(path, default):
    _ensure()
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default.copy()

def _write(path, data):
    _ensure(); path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def memory(): return _read(MEMORY_FILE, DEFAULT_MEMORY)
def dna(): return _read(PROFILE_FILE, DEFAULT_DNA)

def add_song(title, text, mode='SONG', tags=None, metadata=None):
    data=memory(); now=datetime.now(timezone.utc).isoformat()
    item={'id':now.replace(':','').replace('+','_'),'title':title or 'Untitled draft','mode':mode,'text':text,'tags':tags or [],'metadata':metadata or {},'created_at':now}
    data['songs'].insert(0,item); data['songs']=data['songs'][:100]; data['updated_at']=now; _write(MEMORY_FILE,data); return item

def add_note(note):
    data=memory(); now=datetime.now(timezone.utc).isoformat(); data['notes'].insert(0,{'text':note,'created_at':now}); data['notes']=data['notes'][:100]; data['updated_at']=now; _write(MEMORY_FILE,data); return data['notes'][0]

def recent(limit=8): return memory().get('songs',[])[:max(1,min(limit,30))]

def build_local_dna():
    songs=memory().get('songs',[])
    text='\n'.join(s.get('text','') for s in songs)
    themes=[]
    for term,label in [('любов','love'),('расстав','breakup'),('ноч','night'),('город','city'),('голов','mind'),('время','time'),('дорог','road'),('один','solitude')]:
        if len(re.findall(term,text,re.I))>=2: themes.append(label)
    phrases=[]
    for s in songs:
        for line in re.split(r'\n+',s.get('text','')):
            line=re.sub(r'^\[[^\]]+\]\s*','',line).strip(' -—')
            if 4 <= len(line.split()) <= 10 and ('я ' in line.lower() or 'ты ' in line.lower()): phrases.append(line)
    dna0=dna(); dna0.update({'updated_at':datetime.now(timezone.utc).isoformat(),'evidence_count':len(songs),'themes':sorted(set(themes)),'signature_phrases':phrases[:12], 'identity':'Русскоязычный автор, работающий через личную исповедь, контраст внешнего и внутреннего состояния и короткие запоминающиеся hooks.' if songs else ''})
    if songs:
        dna0['strengths']=list(dict.fromkeys((dna0.get('strengths') or [])+['hook-first thinking','эмоциональная конкретика','разговорная подача']))[:8]
        dna0['avoid']=list(dict.fromkeys((dna0.get('avoid') or [])+['пустые клише','перегруженные рифмы','длинные строки без певучести']))[:8]
    _write(PROFILE_FILE,dna0); return dna0
