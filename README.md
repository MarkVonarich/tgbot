# Resume Radar — пошаговый деплой на VPS (FirstVDS) через MobaXterm

Ниже полностью **копипаст-блоки**: команды и **полный код файлов** через `cat > ... <<'EOF'`.
Никаких "найди строку и замени".

---

## Шаг 1. Диагностика VPS и nginx (обязательно)

### Команды (копипаст в MobaXterm)
```bash
set -e
uname -a
cat /etc/os-release
python3 --version || true
nginx -v || true
systemctl --version || true
systemctl is-active nginx || true

echo "--- nginx -T (head) ---"
nginx -T 2>/tmp/nginx_full_dump.txt | head -n 120 || true

echo "--- sites-enabled ---"
ls -la /etc/nginx/sites-enabled || true

echo "--- extract server_name ---"
awk '/server_name/{print NR":"$0}' /tmp/nginx_full_dump.txt | head -n 20 || true

echo "--- public ip ---"
curl -sS ifconfig.me || true
echo
```

### Что должно получиться
- Вы увидите: OS, версии Python/nginx/systemd.
- Будет понятно, какой конфиг nginx активен (`/etc/nginx/sites-enabled/...`).
- Получите домен или внешний IP.

### URL сервиса
- Итоговый URL: `http://<ваш_домен_или_ip>/resume/` (или `https://.../resume/`, если SSL уже включен).

---

## Шаг 2. Создать проект и виртуальное окружение

### Команды
```bash
set -e
mkdir -p /root/resume_radar/{app/templates,app/static,tools,data,imports,out,deploy}
cd /root/resume_radar
python3 -m venv .venv
source /root/resume_radar/.venv/bin/activate
pip install -U pip
```

---

## Шаг 3. Полные файлы проекта

### 3.1 requirements.txt
```bash
cat > /root/resume_radar/requirements.txt <<'EOFREQ'
fastapi==0.115.2
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
jinja2==3.1.4
python-multipart==0.0.12
playwright==1.48.0
EOFREQ
```

### 3.2 app/__init__.py
```bash
cat > /root/resume_radar/app/__init__.py <<'EOFINIT'
EOFINIT
```

### 3.3 app/db.py
```bash
cat > /root/resume_radar/app/db.py <<'EOFDB'
from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path('/root/resume_radar')
DB_PATH = BASE_DIR / 'data' / 'app.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOFDB
```

### 3.4 app/models.py
```bash
cat > /root/resume_radar/app/models.py <<'EOFMODELS'
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Vacancy(Base):
    __tablename__ = 'vacancies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), default='')
    company: Mapped[str] = mapped_column(String(300), default='')
    url: Mapped[str] = mapped_column(String(1000), default='')
    text_raw: Mapped[str] = mapped_column(Text, default='')
    requirements_raw: Mapped[str] = mapped_column(Text, default='')
    responsibilities_raw: Mapped[str] = mapped_column(Text, default='')
    conditions_raw: Mapped[str] = mapped_column(Text, default='')
    keywords_json: Mapped[str] = mapped_column(Text, default='[]')
    track: Mapped[str] = mapped_column(String(100), default='other')
    score: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[str] = mapped_column(String(100), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExperienceBlock(Base):
    __tablename__ = 'experience_blocks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(300), default='')
    role: Mapped[str] = mapped_column(String(300), default='')
    period_from: Mapped[str] = mapped_column(String(20), default='')
    period_to: Mapped[str] = mapped_column(String(20), default='')
    track: Mapped[str] = mapped_column(String(100), default='other')
    situation: Mapped[str] = mapped_column(Text, default='')
    task: Mapped[str] = mapped_column(Text, default='')
    action: Mapped[str] = mapped_column(Text, default='')
    result: Mapped[str] = mapped_column(Text, default='')
    bullet_ready: Mapped[str] = mapped_column(Text, default='')
    tools_json: Mapped[str] = mapped_column(Text, default='[]')
    keywords_json: Mapped[str] = mapped_column(Text, default='[]')
    strength: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResumeDraft(Base):
    __tablename__ = 'resume_drafts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey('vacancies.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    selected_blocks_json: Mapped[str] = mapped_column(Text, default='[]')
    resume_html: Mapped[str] = mapped_column(Text, default='')
    resume_text_plain: Mapped[str] = mapped_column(Text, default='')
    cover_letter_text: Mapped[str] = mapped_column(Text, default='')
    diff_json: Mapped[str] = mapped_column(Text, default='{}')
    pdf_path: Mapped[str] = mapped_column(String(500), default='')


class ImportLog(Base):
    __tablename__ = 'imports'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(300), default='')
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    rows_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default='')
EOFMODELS
```

### 3.5 app/services.py
```bash
cat > /root/resume_radar/app/services.py <<'EOFSRV'
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from playwright.sync_api import sync_playwright

TOOL_KEYWORDS = {
    'sql', 'clickhouse', 'postgres', 'postgresql', 'mysql', 'superset', 'powerbi', 'appsflyer',
    'appmetrica', 'airflow', 'python', 'attribution', 'атрибуция', 'фрод', 'антифрод', 'анти фрод',
    'fraud', 'abuse', 'bonus', 'бонус', 'кэшбек', 'cashback', 'kyc', 'ltv', 'ggr', 'dwh', 'дашборд',
    'витрина', 'triggers', 'триггер', 'validation', 'валидац', 'post-attribution', 'постатрибуц',
    'risk', 'monitoring', 'операцион', 'alerts', 'алерт'
}

TRACK_PATTERNS = {
    'marketing_fraud': [r'appsflyer', r'appmetrica', r'атрибуц', r'mmp', r'validation'],
    'abuse_loyalty': [r'бонус', r'кэшбек', r'cashback', r'промо', r'абьюз', r'multi', r'мульти'],
    'bi_analytics': [r'superset', r'powerbi', r'dwh', r'etl', r'alerts?', r'dashboard', r'clickhouse', r'postgres', r'\bsql\b'],
    'risk_monitoring': [r'\brisk\b', r'операц', r'транзакц', r'мониторинг'],
}

NEGATIVE_PATTERNS = [r'junior', r'стаж[её]р', r'мфо', r'коллект', r'микрозайм']
POSITIVE_WEIGHTS = {
    'appsflyer': 8,
    'appmetrica': 7,
    'attribution': 6,
    'антифрод': 6,
    'фрод': 6,
    'abuse': 7,
    'бонус': 6,
    'кэшбек': 6,
    'superset': 5,
    'powerbi': 5,
    'clickhouse': 6,
    'sql': 4,
    'postgres': 4,
}


def tokenize(text: str) -> list[str]:
    txt = re.sub(r'[^\w\-\sА-Яа-яЁё]', ' ', text.lower())
    txt = txt.replace('антифрод', 'анти фрод антифрод')
    return [t for t in re.split(r'\s+', txt) if len(t) > 1]


def extract_keywords(text: str) -> list[str]:
    tokens = tokenize(text)
    found = set()
    joined = ' '.join(tokens)
    for kw in TOOL_KEYWORDS:
        if (' ' in kw and kw in joined) or (kw in tokens) or (kw in joined):
            found.add(kw)
    return sorted(found)


def detect_track(text: str) -> str:
    t = text.lower()
    scores = {track: sum(1 for p in pats if re.search(p, t)) for track, pats in TRACK_PATTERNS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'other'


def vacancy_score(text: str, keywords: Iterable[str]) -> int:
    s = sum(POSITIVE_WEIGHTS.get(k, 2) for k in keywords)
    low = text.lower()
    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, low):
            s -= 15
    return s


def extract_block(text: str, headers: list[str]) -> str:
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        ll = ln.lower()
        if any(h in ll for h in headers):
            start = i
            break
    if start is None:
        return ''
    out = []
    for ln in lines[start + 1:]:
        ll = ln.lower()
        if any(h in ll for h in ['требован', 'обязанност', 'услови', 'будет плюсом']) and out:
            break
        out.append(ln)
    return '\n'.join(out).strip()


def split_vacancies(raw: str) -> list[dict]:
    chunks = re.split(r'\n(?=https?://hh\.ru/vacancy/|Компания:|Должность:|Вакансия:)', raw, flags=re.I)
    results = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        lines = [x.strip() for x in c.splitlines() if x.strip()]
        url = ''
        title = ''
        company = ''
        for ln in lines[:8]:
            u = re.search(r'https?://hh\.ru/vacancy/\d+', ln)
            if u:
                url = u.group(0)
            if ln.lower().startswith('должность:') or ln.lower().startswith('вакансия:'):
                title = ln.split(':', 1)[1].strip()
            if ln.lower().startswith('компания:'):
                company = ln.split(':', 1)[1].strip()
        if not title and lines:
            title = lines[0][:200]
        req = extract_block(c, [r'требовани', r'что ожидаем', r'мы ждем'])
        resp = extract_block(c, [r'обязанност', r'задач', r'что делать'])
        cond = extract_block(c, [r'услови', r'мы предлагаем', r'будет плюсом'])
        results.append({
            'title': title,
            'company': company,
            'url': url,
            'text_raw': c,
            'requirements_raw': req,
            'responsibilities_raw': resp,
            'conditions_raw': cond,
        })
    return results


def build_cover_letter(vacancy: dict, bullets: list[str]) -> str:
    top_results = [b for b in bullets if ('→' in b or '%' in b or '$' in b or 'предотвращ' in b.lower())][:2]
    result_txt = '; '.join(top_results) if top_results else (bullets[0] if bullets else 'реализовал проекты с измеримым эффектом')
    return (
        f"Откликаюсь на позицию {vacancy.get('title', '')} в компании {vacancy.get('company', 'вашей компании')}. "
        "У меня практический опыт в антифроде, BI-аналитике и построении правил детекта под бизнес-задачи. "
        f"Пример результата: {result_txt}. "
        "Беру задачи под ключ: от аналитики и SQL-выгрузок до дашбордов, алертов и рекомендаций для продуктовых команд. "
        "Буду рад обсудить, как мой опыт поможет усилить вашу команду."
    )


def render_resume_html(profile: dict, grouped: dict[str, list[dict]], skills: list[str], tools: list[str]) -> str:
    sections = []
    for company_role, blocks in grouped.items():
        bullets = ''.join(f'<li>{b["bullet_ready"]}</li>' for b in blocks)
        sections.append(f'<p><b>{company_role}</b></p><ul>{bullets}</ul>')
    return f"""
<!DOCTYPE html>
<html lang='ru'>
<head><meta charset='UTF-8'><style>
body {{ font-family: Arial, sans-serif; font-size: 10.5pt; margin: 20mm 14mm; line-height: 1.25; color: #111; }}
h1 {{ font-size: 15pt; margin: 0 0 4px 0; }}
h2 {{ font-size: 11pt; margin: 9px 0 5px; text-transform: uppercase; }}
p, li {{ margin: 0; padding: 0; }} ul {{ margin: 3px 0 6px 16px; }}
</style></head>
<body>
<h1>{profile['name']}</h1>
<p>{profile['title']} | {profile['contacts']}</p>
<h2>ПРОФИЛЬ</h2><p>{profile['summary']}</p>
<h2>НАВЫКИ</h2><p>{', '.join(skills)}</p>
<h2>ИНСТРУМЕНТЫ</h2><p>{', '.join(tools)}</p>
<h2>ОПЫТ</h2>{''.join(sections)}
<h2>ОБРАЗОВАНИЕ</h2><p>Высшее образование, экономика и аналитика данных.</p>
</body></html>
""".strip()


def html_to_text(html: str) -> str:
    t = re.sub(r'<[^>]+>', '\n', html)
    return re.sub(r'\n+', '\n', t).strip()


def save_pdf_single_page(html: str, output_path: Path) -> tuple[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    variant_html = html
    page_count = 2
    for _ in range(8):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(variant_html)
            pdf_bytes = page.pdf(format='A4', margin={'top': '12mm', 'bottom': '12mm', 'left': '12mm', 'right': '12mm'})
            browser.close()
        output_path.write_bytes(pdf_bytes)
        page_count = 1 if output_path.stat().st_size < 240000 else 2
        if page_count == 1:
            return str(output_path), 1
        variant_html = re.sub(r'<li>[^<]{0,400}</li>', '', variant_html, count=1)
    return str(output_path), page_count


def diff_blocks(old_ids: list[int], new_ids: list[int]) -> dict:
    old_set, new_set = set(old_ids), set(new_ids)
    return {'added': sorted(list(new_set - old_set)), 'removed': sorted(list(old_set - new_set)), 'kept': sorted(list(new_set & old_set))}


def parse_json_list(value: str) -> list:
    try:
        return json.loads(value) if value else []
    except json.JSONDecodeError:
        return []


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)
EOFSRV
```

### 3.6 app/main.py
```bash
cat > /root/resume_radar/app/main.py <<'EOFMAIN'
from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import ExperienceBlock, ImportLog, ResumeDraft, Vacancy
from .services import (
    build_cover_letter,
    detect_track,
    diff_blocks,
    dumps,
    extract_keywords,
    html_to_text,
    parse_json_list,
    render_resume_html,
    save_pdf_single_page,
    split_vacancies,
    vacancy_score,
)

BASE_DIR = Path('/root/resume_radar')
IMPORTS_DIR = BASE_DIR / 'imports'
OUT_DIR = BASE_DIR / 'out'
IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='Resume Radar')
app.mount('/resume/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')


@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)


@app.get('/health', response_class=PlainTextResponse)
def health():
    return 'ok'


@app.get('/resume/', response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    q = request.query_params.get('q', '').strip().lower()
    track = request.query_params.get('track', '').strip()
    vacancies = db.query(Vacancy).order_by(desc(Vacancy.score), desc(Vacancy.created_at)).all()
    if q:
        vacancies = [v for v in vacancies if q in (v.title + ' ' + v.company + ' ' + v.text_raw).lower()]
    if track:
        vacancies = [v for v in vacancies if v.track == track]
    tracks = sorted(set(v.track for v in db.query(Vacancy).all()))
    return templates.TemplateResponse('home.html', {'request': request, 'vacancies': vacancies, 'tracks': tracks, 'q': q, 'track': track})


@app.get('/resume/admin/import', response_class=HTMLResponse)
def import_page(request: Request, db: Session = Depends(get_db)):
    logs = db.query(ImportLog).order_by(desc(ImportLog.imported_at)).limit(20).all()
    return templates.TemplateResponse('import.html', {'request': request, 'logs': logs})


@app.post('/resume/admin/import')
async def import_txt(file: UploadFile, db: Session = Depends(get_db)):
    dst = IMPORTS_DIR / file.filename
    with dst.open('wb') as f:
        shutil.copyfileobj(file.file, f)
    raw = dst.read_text(encoding='utf-8', errors='ignore')
    parsed = split_vacancies(raw)
    inserted = 0
    for item in parsed:
        text = item['text_raw']
        kws = extract_keywords(text)
        track = detect_track(text)
        score = vacancy_score(text, kws)
        db.add(Vacancy(**item, keywords_json=dumps(kws), track=track, score=score))
        inserted += 1
    db.add(ImportLog(filename=file.filename, rows_count=inserted, notes=f'parsed chunks={len(parsed)}'))
    db.commit()
    return RedirectResponse('/resume/', status_code=303)


@app.get('/resume/vacancies/{vacancy_id}', response_class=HTMLResponse)
def vacancy_view(vacancy_id: int, request: Request, db: Session = Depends(get_db)):
    vacancy = db.get(Vacancy, vacancy_id)
    drafts = db.query(ResumeDraft).filter(ResumeDraft.vacancy_id == vacancy_id).order_by(desc(ResumeDraft.id)).all()
    return templates.TemplateResponse('vacancy.html', {'request': request, 'vacancy': vacancy, 'drafts': drafts, 'keywords': parse_json_list(vacancy.keywords_json)})


@app.post('/resume/vacancies/{vacancy_id}/build')
def build_resume(vacancy_id: int, db: Session = Depends(get_db)):
    vacancy = db.get(Vacancy, vacancy_id)
    v_keywords = set(parse_json_list(vacancy.keywords_json))
    blocks = db.query(ExperienceBlock).all()
    scored = []
    for b in blocks:
        b_kw = set(parse_json_list(b.keywords_json))
        overlap = len(v_keywords & b_kw)
        weight = overlap * 3 + b.strength
        if b.track == vacancy.track:
            weight += 4
        scored.append((weight, b))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [x[1] for x in scored[:12]]

    grouped = {}
    for b in selected:
        key = f"{b.company} — {b.role} ({b.period_from} - {b.period_to})"
        grouped.setdefault(key, []).append({'bullet_ready': b.bullet_ready})

    tools = sorted({t for b in selected for t in parse_json_list(b.tools_json)})[:15]
    skills = sorted({k for b in selected for k in parse_json_list(b.keywords_json) if k not in tools})[:18]

    profile = {
        'name': 'Кандидат: Resume Radar User',
        'title': 'Senior Antifraud / Marketing Fraud Analyst',
        'contacts': 'Москва | Telegram/Email добавить перед откликом',
        'summary': 'Антифрод-аналитик с опытом в маркетинговом и бонусном фроде, SQL/ClickHouse/Postgres, витринах правил, алертах и BI-дашбордах.',
    }
    html = render_resume_html(profile, grouped, skills, tools)
    plain = html_to_text(html)

    old = db.query(ResumeDraft).filter(ResumeDraft.vacancy_id == vacancy_id).order_by(desc(ResumeDraft.id)).first()
    old_ids = parse_json_list(old.selected_blocks_json) if old else []
    new_ids = [b.id for b in selected]
    diff = diff_blocks(old_ids, new_ids)

    cover = build_cover_letter({'title': vacancy.title, 'company': vacancy.company}, [b.bullet_ready for b in selected])

    draft = ResumeDraft(
        vacancy_id=vacancy_id,
        selected_blocks_json=dumps(new_ids),
        resume_html=html,
        resume_text_plain=plain,
        cover_letter_text=cover,
        diff_json=dumps(diff),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return RedirectResponse(f'/resume/drafts/{draft.id}', status_code=303)


@app.get('/resume/drafts/{draft_id}', response_class=HTMLResponse)
def view_draft(draft_id: int, request: Request, db: Session = Depends(get_db)):
    draft = db.get(ResumeDraft, draft_id)
    return templates.TemplateResponse('draft.html', {'request': request, 'draft': draft, 'diff': json.loads(draft.diff_json or '{}')})


@app.post('/resume/drafts/{draft_id}/save')
def save_draft(
    draft_id: int,
    resume_html: str = Form(...),
    resume_text_plain: str = Form(...),
    cover_letter_text: str = Form(...),
    db: Session = Depends(get_db),
):
    draft = db.get(ResumeDraft, draft_id)
    draft.resume_html = resume_html
    draft.resume_text_plain = resume_text_plain
    draft.cover_letter_text = cover_letter_text
    db.commit()
    return RedirectResponse(f'/resume/drafts/{draft_id}', status_code=303)


@app.get('/resume/resume/{draft_id}/pdf')
def export_pdf(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(ResumeDraft, draft_id)
    out = OUT_DIR / f'resume_{draft_id}.pdf'
    path, pages = save_pdf_single_page(draft.resume_html, out)
    draft.pdf_path = path if pages == 1 else ''
    db.commit()
    if pages != 1:
        return PlainTextResponse('PDF > 1 page. Уменьшите объем буллетов и повторите.', status_code=409)
    return FileResponse(path, media_type='application/pdf', filename=out.name)


@app.get('/resume/experience', response_class=HTMLResponse)
def experience_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(ExperienceBlock).order_by(desc(ExperienceBlock.created_at)).all()
    return templates.TemplateResponse('experience_list.html', {'request': request, 'items': items})


@app.get('/resume/experience/new', response_class=HTMLResponse)
def experience_new(request: Request):
    return templates.TemplateResponse('experience_form.html', {'request': request, 'item': None})


@app.post('/resume/experience/new')
def experience_create(
    company: str = Form(...),
    role: str = Form(...),
    period_from: str = Form(''),
    period_to: str = Form(''),
    track: str = Form('other'),
    situation: str = Form(''),
    task: str = Form(''),
    action: str = Form(''),
    result: str = Form(''),
    bullet_ready: str = Form(...),
    tools_csv: str = Form(''),
    keywords_csv: str = Form(''),
    strength: int = Form(1),
    db: Session = Depends(get_db),
):
    tools = [x.strip() for x in tools_csv.split(',') if x.strip()]
    kws = [x.strip().lower() for x in keywords_csv.split(',') if x.strip()]
    if not kws:
        kws = extract_keywords(' '.join([bullet_ready, situation, task, action, result]))
    db.add(ExperienceBlock(
        company=company,
        role=role,
        period_from=period_from,
        period_to=period_to,
        track=track,
        situation=situation,
        task=task,
        action=action,
        result=result,
        bullet_ready=bullet_ready,
        tools_json=dumps(tools),
        keywords_json=dumps(kws),
        strength=strength,
    ))
    db.commit()
    return RedirectResponse('/resume/experience', status_code=303)


@app.get('/resume/experience/{item_id}/edit', response_class=HTMLResponse)
def experience_edit(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(ExperienceBlock, item_id)
    return templates.TemplateResponse('experience_form.html', {'request': request, 'item': item})


@app.post('/resume/experience/{item_id}/edit')
def experience_update(
    item_id: int,
    company: str = Form(...),
    role: str = Form(...),
    period_from: str = Form(''),
    period_to: str = Form(''),
    track: str = Form('other'),
    situation: str = Form(''),
    task: str = Form(''),
    action: str = Form(''),
    result: str = Form(''),
    bullet_ready: str = Form(...),
    tools_csv: str = Form(''),
    keywords_csv: str = Form(''),
    strength: int = Form(1),
    db: Session = Depends(get_db),
):
    item = db.get(ExperienceBlock, item_id)
    item.company = company
    item.role = role
    item.period_from = period_from
    item.period_to = period_to
    item.track = track
    item.situation = situation
    item.task = task
    item.action = action
    item.result = result
    item.bullet_ready = bullet_ready
    item.tools_json = dumps([x.strip() for x in tools_csv.split(',') if x.strip()])
    item.keywords_json = dumps([x.strip().lower() for x in keywords_csv.split(',') if x.strip()])
    item.strength = strength
    db.commit()
    return RedirectResponse('/resume/experience', status_code=303)
EOFMAIN
```

### 3.7 app/static/style.css
```bash
cat > /root/resume_radar/app/static/style.css <<'EOFCSS'
body{font-family:Arial,sans-serif;max-width:1100px;margin:20px auto;padding:0 12px;color:#111}
a{color:#1344aa;text-decoration:none}a:hover{text-decoration:underline}
.header{display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.card{border:1px solid #ddd;border-radius:8px;padding:12px;margin:10px 0}
input,textarea,select,button{font:inherit;padding:6px;margin:3px 0}
textarea{width:100%;min-height:90px}
table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #e8e8e8;padding:8px;text-align:left;vertical-align:top}
.small{font-size:12px;color:#555}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
EOFCSS
```

### 3.8 templates
```bash
cat > /root/resume_radar/app/templates/base.html <<'EOFBASE'
<!doctype html><html lang='ru'><head><meta charset='utf-8'><title>Resume Radar</title>
<link rel='stylesheet' href='/resume/static/style.css'></head><body>
<div class='header'>
  <h2 style='margin:0'>Resume Radar</h2>
  <a href='/resume/'>Вакансии</a>
  <a href='/resume/admin/import'>Импорт TXT</a>
  <a href='/resume/experience'>Опыт (CRUD)</a>
  <a href='/health'>Health</a>
</div>
{% block content %}{% endblock %}
</body></html>
EOFBASE

cat > /root/resume_radar/app/templates/home.html <<'EOFHOME'
{% extends 'base.html' %}{% block content %}
<h3>Список вакансий</h3>
<form method='get' action='/resume/'>
  <input name='q' value='{{q}}' placeholder='поиск по тексту/компании/роли'>
  <select name='track'><option value=''>Все track</option>{% for t in tracks %}<option {% if track==t %}selected{% endif %}>{{t}}</option>{% endfor %}</select>
  <button>Фильтровать</button>
</form>
<table><tr><th>ID</th><th>Роль</th><th>Компания</th><th>Track</th><th>Score</th><th></th></tr>
{% for v in vacancies %}<tr><td>{{v.id}}</td><td>{{v.title}}</td><td>{{v.company}}</td><td>{{v.track}}</td><td>{{v.score}}</td><td><a href='/resume/vacancies/{{v.id}}'>Открыть</a></td></tr>{% endfor %}</table>
{% endblock %}
EOFHOME

cat > /root/resume_radar/app/templates/import.html <<'EOFIMPORT'
{% extends 'base.html' %}{% block content %}
<h3>Импорт вакансий из txt</h3>
<form method='post' enctype='multipart/form-data'>
  <input type='file' name='file' accept='.txt' required>
  <button>Загрузить и импортировать</button>
</form>
<p class='small'>Файлы сохраняются в /root/resume_radar/imports/</p>
<h4>Логи импорта</h4>
<table><tr><th>Когда</th><th>Файл</th><th>Строк</th><th>Notes</th></tr>
{% for log in logs %}<tr><td>{{log.imported_at}}</td><td>{{log.filename}}</td><td>{{log.rows_count}}</td><td>{{log.notes}}</td></tr>{% endfor %}</table>
{% endblock %}
EOFIMPORT

cat > /root/resume_radar/app/templates/vacancy.html <<'EOFVAC'
{% extends 'base.html' %}{% block content %}
<div class='card'>
  <h3>{{vacancy.title}}</h3>
  <p><b>Компания:</b> {{vacancy.company}} | <b>Track:</b> {{vacancy.track}} | <b>Score:</b> {{vacancy.score}}</p>
  {% if vacancy.url %}<p><a target='_blank' href='{{vacancy.url}}'>Ссылка HH</a></p>{% endif %}
  <p><b>Keywords:</b> {{keywords|join(', ')}}</p>
  <form method='post' action='/resume/vacancies/{{vacancy.id}}/build'><button>Собрать резюме</button></form>
</div>
<div class='grid'>
  <div class='card'><h4>Требования</h4><pre>{{vacancy.requirements_raw}}</pre></div>
  <div class='card'><h4>Обязанности</h4><pre>{{vacancy.responsibilities_raw}}</pre></div>
</div>
<div class='card'><h4>Условия</h4><pre>{{vacancy.conditions_raw}}</pre></div>
<div class='card'><h4>Черновики по этой вакансии</h4>
{% for d in drafts %}<p><a href='/resume/drafts/{{d.id}}'>Draft #{{d.id}}</a> — {{d.created_at}}</p>{% else %}<p>Пока нет.</p>{% endfor %}</div>
{% endblock %}
EOFVAC

cat > /root/resume_radar/app/templates/draft.html <<'EOFDRAFT'
{% extends 'base.html' %}{% block content %}
<h3>Draft #{{draft.id}}</h3>
<div class='card'>
  <p><a href='/resume/resume/{{draft.id}}/pdf'>Скачать PDF (1 страница)</a></p>
  <h4>Diff буллетов</h4>
  <pre>{{diff}}</pre>
</div>
<form method='post' action='/resume/drafts/{{draft.id}}/save'>
<div class='grid'>
  <div><h4>Resume HTML</h4><textarea name='resume_html' style='min-height:280px'>{{draft.resume_html}}</textarea></div>
  <div><h4>ATS plain text</h4><textarea name='resume_text_plain' style='min-height:280px'>{{draft.resume_text_plain}}</textarea></div>
</div>
<h4>Сопроводительное письмо</h4>
<textarea name='cover_letter_text' style='min-height:140px'>{{draft.cover_letter_text}}</textarea>
<button>Сохранить изменения</button>
</form>
<div class='card'><h4>Preview</h4>{{draft.resume_html|safe}}</div>
{% endblock %}
EOFDRAFT

cat > /root/resume_radar/app/templates/experience_list.html <<'EOFEXPL'
{% extends 'base.html' %}{% block content %}
<h3>Блоки опыта</h3>
<p><a href='/resume/experience/new'>+ Добавить блок</a></p>
<table><tr><th>ID</th><th>Компания/роль/период</th><th>Track</th><th>Bullet</th><th></th></tr>
{% for i in items %}<tr><td>{{i.id}}</td><td>{{i.company}} / {{i.role}} / {{i.period_from}}-{{i.period_to}}</td><td>{{i.track}}</td><td>{{i.bullet_ready}}</td><td><a href='/resume/experience/{{i.id}}/edit'>Редактировать</a></td></tr>{% endfor %}</table>
{% endblock %}
EOFEXPL

cat > /root/resume_radar/app/templates/experience_form.html <<'EOFEXPF'
{% extends 'base.html' %}{% block content %}
<h3>{% if item %}Редактирование{% else %}Новый{% endif %} блока опыта</h3>
<form method='post'>
<input name='company' placeholder='Компания' value='{{item.company if item else ""}}' required><br>
<input name='role' placeholder='Роль' value='{{item.role if item else ""}}' required><br>
<input name='period_from' placeholder='Период от' value='{{item.period_from if item else ""}}'>
<input name='period_to' placeholder='Период до' value='{{item.period_to if item else ""}}'><br>
<input name='track' placeholder='Track' value='{{item.track if item else "other"}}'><br>
<textarea name='situation' placeholder='Situation'>{{item.situation if item else ""}}</textarea>
<textarea name='task' placeholder='Task'>{{item.task if item else ""}}</textarea>
<textarea name='action' placeholder='Action'>{{item.action if item else ""}}</textarea>
<textarea name='result' placeholder='Result'>{{item.result if item else ""}}</textarea>
<textarea name='bullet_ready' placeholder='Готовый буллет' required>{{item.bullet_ready if item else ""}}</textarea>
<input name='tools_csv' placeholder='tools через запятую' value='{{item.tools_json if item else ""}}'><br>
<input name='keywords_csv' placeholder='keywords через запятую' value='{{item.keywords_json if item else ""}}'><br>
<input name='strength' type='number' value='{{item.strength if item else 3}}'><br>
<button>Сохранить</button>
</form>
{% endblock %}
EOFEXPF
```

### 3.9 tools/seed_experience.py
```bash
cat > /root/resume_radar/tools/seed_experience.py <<'EOFSEED'
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, Base, engine
from app.models import ExperienceBlock
from app.services import extract_keywords

Base.metadata.create_all(bind=engine)

SEED = [
    ('Медиапоинт', 'Антифрод аналитик', '2021-02', '2025-03', 'abuse_loyalty', 'Реализовал SQL/Python-сегментацию пользователей для выявления бонусного абьюза → предотвращено потерь $240 000.', 'clickhouse,postgresql,mysql,python,bonus,abuse,ggr'),
    ('Медиапоинт', 'Антифрод аналитик', '2021-02', '2025-03', 'bi_analytics', 'Подготовил и автоматизировал 135+ отчетов и KPI-дашборд в PowerBI для руководства.', 'powerbi,sql,alerts,dashboard'),
    ('Медиапоинт', 'Антифрод аналитик', '2021-02', '2025-03', 'abuse_loyalty', 'Категоризировал фродовых игроков (мультиаккаунт, бонусхантер, дроп) и принимал меры: лимиты, KYC, блокировка.', 'kyc,мультиаккаунт,бонус,антифрод'),
    ('Медиапоинт', 'Антифрод аналитик', '2021-02', '2025-03', 'risk_monitoring', 'Мониторил KPI и отклонения (например GGR<0), запускал точечные проверки и эскалации.', 'ggr,risk,monitoring,alerts'),
    ('Медиапоинт', 'Антифрод партнерки', '2023-01', '2025-03', 'marketing_fraud', 'Развивал fraud score-модель на базе триггеров и весов, увеличив точность ручной валидации.', 'fraud,triggers,score,validation'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Проверял фрод в маркетинговых кампаниях по AppsFlyer/AppMetrica и снижал аномалии на платном трафике.', 'appsflyer,appmetrica,атрибуция,fraud'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'bi_analytics', 'Построил Superset-дашборды для мониторинга validation rules и ручных правил.', 'superset,dashboard,validation rules'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Настраивал алерты по всплескам аномалий и готовил рекомендации продуктовым командам.', 'alerts,fraud,антифрод'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Проводил пост-атрибуционный анализ фрода и предлагал новые validation/hand rules.', 'post-attribution,validation,triggers'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Контролировал корректность SDK-версий и влияние на достоверность атрибуции.', 'sdk,appsflyer,атрибуция'),
    ('Ренессанс Банк', 'Старший антифрод аналитик', '2025-03', '2025-07', 'risk_monitoring', 'Разработал и внедрил 6+ риск-триггеров мониторинга транзакций (ЮЛ/ФЛ) → +15% к точности аномалий.', 'risk,triggers,transactions,fraud'),
    ('Ренессанс Банк', 'Старший антифрод аналитик', '2025-03', '2025-07', 'risk_monitoring', 'Автоматизировал заполнение регуляторных отчетов по СОР (Excel/SAP) → минус 40 минут ручной работы.', 'sap,excel,automation,операционный риск'),
    ('Ренессанс Банк', 'Старший антифрод аналитик', '2025-03', '2025-07', 'risk_monitoring', 'Разбирал спорные кейсы по логам приложений (IP, устройства, действия), формировал доказательную базу для юристов.', 'risk,ip,device,kyc'),
    ('Медиапоинт', 'Антифрод аналитик', '2022-04', '2025-03', 'abuse_loyalty', 'Собирал ClickHouse/Postgres витрины для поиска цепочек мультиаккаунтов и бонусных связей.', 'clickhouse,postgres,multiaccount,bonus'),
    ('Медиапоинт', 'Антифрод аналитик', '2022-08', '2025-03', 'abuse_loyalty', 'Разработал триггеры детекта бонусных злоупотреблений и систему приоритезации ручной проверки.', 'triggers,bonus,abuse,score'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Анализировал источники VK Ads/Xiaomi Ads/Xapads и выявлял паттерны фрода до уровня кампаний.', 'vkads,xiaomi ads,xapads,fraud'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Взаимодействовал с AppsFlyer-менеджером и командами продукта для безопасного изменения anti-fraud правил.', 'appsflyer,validation,product'),
]


def main():
    db = SessionLocal()
    try:
        for company, role, pf, pt, track, bullet, tools_csv in SEED:
            tools = [x.strip() for x in tools_csv.split(',') if x.strip()]
            kws = sorted(set(extract_keywords(bullet + ' ' + tools_csv)))
            db.add(ExperienceBlock(
                company=company,
                role=role,
                period_from=pf,
                period_to=pt,
                track=track,
                bullet_ready=bullet,
                tools_json=json.dumps(tools, ensure_ascii=False),
                keywords_json=json.dumps(kws, ensure_ascii=False),
                strength=4,
            ))
        db.commit()
        print(f'Seed done: {len(SEED)} blocks')
    finally:
        db.close()


if __name__ == '__main__':
    main()
EOFSEED
```

### 3.10 deploy файлы
```bash
cat > /root/resume_radar/deploy/resume-radar.service <<'EOFSVC'
[Unit]
Description=Resume Radar FastAPI service
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/resume_radar
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/root/resume_radar/.venv/bin
ExecStart=/root/resume_radar/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOFSVC

cat > /root/resume_radar/deploy/nginx_resume_location.conf <<'EOFNGX'
location /resume/ {
    proxy_pass http://127.0.0.1:8010;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /health {
    proxy_pass http://127.0.0.1:8010/health;
    proxy_set_header Host $host;
}
EOFNGX
```

---

## Шаг 4. Установка зависимостей и браузера для PDF

### Команды
```bash
set -e
cd /root/resume_radar
source /root/resume_radar/.venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Проверка
```bash
python -c "import fastapi, sqlalchemy, playwright; print('deps ok')"
```

Ожидаемо: `deps ok`.

---

## Шаг 5. Seed опыта (15+ блоков)

### Команды
```bash
set -e
cd /root/resume_radar
source /root/resume_radar/.venv/bin/activate
python /root/resume_radar/tools/seed_experience.py
```

### Ожидаемо
- Вывод типа: `Seed done: 17 blocks` (или больше).

---

## Шаг 6. Проверка локального запуска FastAPI

### Команды
```bash
set -e
cd /root/resume_radar
source /root/resume_radar/.venv/bin/activate
nohup /root/resume_radar/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 >/root/resume_radar/out/local.log 2>&1 &
sleep 2
curl -sS http://127.0.0.1:8010/health
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8010" || true
```

### Ожидаемо
- `curl` вернет: `ok`.

---

## Шаг 7. systemd сервис

### Команды
```bash
set -e
cp /root/resume_radar/deploy/resume-radar.service /etc/systemd/system/resume-radar.service
systemctl daemon-reload
systemctl enable --now resume-radar
systemctl status resume-radar --no-pager
journalctl -u resume-radar -n 80 --no-pager
```

### Ожидаемо
- Сервис `active (running)`.
- В логах нет traceback.

---

## Шаг 8. nginx location /resume/

> Вставляете содержимое `deploy/nginx_resume_location.conf` внутрь вашего `server { ... }`.

### Команды-диагностика + проверка
```bash
set -e
nginx -T 2>/tmp/nginx_all.txt | head -n 60
ls -la /etc/nginx/sites-enabled

# После ручной вставки блока location в активный server{}:
nginx -t
systemctl reload nginx
```

### Проверка URL
```bash
curl -I http://127.0.0.1:8010/health
curl -I http://<ваш_домен_или_ip>/resume/
```

Ожидаемо: HTTP 200/302 (главное, чтобы открывалось).

---

## Шаг 9. Проверка MVP сценария

### 9.1 Импорт вакансий
- Откройте: `http(s)://<домен_или_ip>/resume/admin/import`
- Загрузите: `/root/resume_radar/imports/vacancies_hh.txt`

### 9.2 Список вакансий
- Откройте: `http(s)://<домен_или_ip>/resume/`
- Должны быть вакансии с `track` и `score`.

### 9.3 Опыт CRUD
- Откройте: `http(s)://<домен_или_ip>/resume/experience`
- Добавьте / отредактируйте блок.

### 9.4 Сборка резюме
- Откройте вакансию: `/resume/vacancies/<id>`
- Нажмите «Собрать резюме»
- Проверьте draft, diff, cover letter.

### 9.5 PDF
- На draft нажмите «Скачать PDF».
- Файл сохранится как `/root/resume_radar/out/resume_<draft_id>.pdf`.

---

## Шаг 10. Полезные команды эксплуатации

```bash
systemctl restart resume-radar
systemctl status resume-radar --no-pager
journalctl -u resume-radar -f

nginx -t
systemctl reload nginx

sqlite3 /root/resume_radar/data/app.db '.tables'
sqlite3 /root/resume_radar/data/app.db 'select id,title,company,track,score from vacancies order by score desc limit 20;'
```

