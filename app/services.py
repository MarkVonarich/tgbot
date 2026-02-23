from __future__ import annotations

import json
import re
from collections import defaultdict
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
    tokens = [t for t in re.split(r'\s+', txt) if len(t) > 1]
    return tokens


def extract_keywords(text: str) -> list[str]:
    tokens = tokenize(text)
    found = set()
    joined = ' '.join(tokens)
    for kw in TOOL_KEYWORDS:
        if ' ' in kw:
            if kw in joined:
                found.add(kw)
        elif kw in tokens or kw in joined:
            found.add(kw)
    for tok in tokens:
        if tok in {'antifraud', 'fraud', 'analytics', 'аналитик', 'продуктовый'}:
            found.add(tok)
    return sorted(found)


def detect_track(text: str) -> str:
    t = text.lower()
    scores = {}
    for track, pats in TRACK_PATTERNS.items():
        scores[track] = sum(1 for p in pats if re.search(p, t))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'other'


def vacancy_score(text: str, keywords: Iterable[str]) -> int:
    s = 0
    low = text.lower()
    for kw in keywords:
        s += POSITIVE_WEIGHTS.get(kw, 2)
    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, low):
            s -= 15
    return s


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
        results.append(
            {
                'title': title,
                'company': company,
                'url': url,
                'text_raw': c,
                'requirements_raw': req,
                'responsibilities_raw': resp,
                'conditions_raw': cond,
            }
        )
    return results


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
    for ln in lines[start + 1 :]:
        ll = ln.lower()
        if any(h in ll for h in ['требован', 'обязанност', 'услови', 'будет плюсом']) and out:
            break
        out.append(ln)
    return '\n'.join(out).strip()


def build_cover_letter(vacancy: dict, bullets: list[str]) -> str:
    top_results = []
    for b in bullets:
        if '→' in b or '%' in b or '$' in b or 'предотвращ' in b.lower():
            top_results.append(b)
        if len(top_results) >= 2:
            break
    result_txt = '; '.join(top_results[:2]) if top_results else (bullets[0] if bullets else 'реализовал проекты с измеримым эффектом')
    return (
        f"Откликаюсь на позицию {vacancy.get('title', '')} в компании {vacancy.get('company', 'вашей компании')}. "
        f"У меня практический опыт в антифроде, BI-аналитике и построении правил детекта под бизнес-задачи. "
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
<h2>ПРОФИЛЬ</h2>
<p>{profile['summary']}</p>
<h2>НАВЫКИ</h2>
<p>{', '.join(skills)}</p>
<h2>ИНСТРУМЕНТЫ</h2>
<p>{', '.join(tools)}</p>
<h2>ОПЫТ</h2>
{''.join(sections)}
<h2>ОБРАЗОВАНИЕ</h2>
<p>Высшее образование, экономика и аналитика данных (указать фактический вуз и год).</p>
</body></html>
""".strip()


def html_to_text(html: str) -> str:
    t = re.sub(r'<[^>]+>', '\n', html)
    t = re.sub(r'\n+', '\n', t)
    return t.strip()


def save_pdf_single_page(html: str, output_path: Path) -> tuple[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_count = 2
    variant_html = html
    for _ in range(8):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(variant_html)
            pdf_bytes = page.pdf(format='A4', margin={'top': '12mm', 'bottom': '12mm', 'left': '12mm', 'right': '12mm'})
            browser.close()
        output_path.write_bytes(pdf_bytes)
        size = output_path.stat().st_size
        page_count = 1 if size < 240_000 else 2
        if page_count == 1:
            return str(output_path), page_count
        variant_html = re.sub(r'<li>[^<]{0,400}</li>', '', variant_html, count=1)
    return str(output_path), page_count


def diff_blocks(old_ids: list[int], new_ids: list[int]) -> dict:
    old_set, new_set = set(old_ids), set(new_ids)
    return {
        'added': sorted(list(new_set - old_set)),
        'removed': sorted(list(old_set - new_set)),
        'kept': sorted(list(new_set & old_set)),
    }


def parse_json_list(value: str) -> list:
    try:
        return json.loads(value) if value else []
    except json.JSONDecodeError:
        return []


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)
