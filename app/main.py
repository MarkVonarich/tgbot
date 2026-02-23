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
from .models import ExperienceBlock, ImportLog, ResumeDraft, UserProfile, Vacancy
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


def get_or_create_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).order_by(UserProfile.id.asc()).first()
    if not profile:
        profile = UserProfile(
            full_name='Максим Чиранов',
            target_title='Senior Antifraud / Marketing Fraud Analyst',
            contacts='Москва | Telegram: @your_tg | Email: your@email.com',
            summary='Антифрод-аналитик с опытом в маркетинговом и бонусном фроде, SQL/ClickHouse/Postgres, правилах детекта, алертах и BI-дашбордах.',
            education='Высшее образование (указать вуз, факультет, год).',
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


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


@app.get('/resume/profile', response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    profile = get_or_create_profile(db)
    return templates.TemplateResponse('profile.html', {'request': request, 'profile': profile})


@app.post('/resume/profile')
def profile_save(
    full_name: str = Form(...),
    target_title: str = Form(...),
    contacts: str = Form(...),
    summary: str = Form(...),
    education: str = Form(...),
    db: Session = Depends(get_db),
):
    profile = get_or_create_profile(db)
    profile.full_name = full_name
    profile.target_title = target_title
    profile.contacts = contacts
    profile.summary = summary
    profile.education = education
    db.commit()
    return RedirectResponse('/resume/profile', status_code=303)


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


@app.post('/resume/admin/import/path')
def import_txt_by_path(path: str = Form(...), db: Session = Depends(get_db)):
    src = Path(path).expanduser()
    if not src.exists() or not src.is_file():
        db.add(ImportLog(filename=path, rows_count=0, notes='file not found'))
        db.commit()
        return RedirectResponse('/resume/admin/import', status_code=303)
    dst = IMPORTS_DIR / src.name
    shutil.copy2(src, dst)
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
    db.add(ImportLog(filename=str(src), rows_count=inserted, notes=f'import by path, parsed chunks={len(parsed)}'))
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
    profile = get_or_create_profile(db)
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

    profile_data = {
        'name': profile.full_name,
        'title': profile.target_title,
        'contacts': profile.contacts,
        'summary': profile.summary,
        'education': profile.education,
    }
    html = render_resume_html(profile_data, grouped, skills, tools)
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
