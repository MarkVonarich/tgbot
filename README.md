# Resume Radar MVP (FastAPI + SQLite)

MVP сервис для:
- импорта вакансий из TXT,
- хранения и CRUD блоков опыта,
- сборки резюме под вакансию без LLM,
- генерации сопроводительного,
- PDF экспорта (1 страница через Playwright).

## Локальный запуск в `/root/resume_radar`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Проверка:
```bash
curl -sS http://127.0.0.1:8010/health
```

## Seed опыта

```bash
python tools/seed_experience.py
```

## Что уже реализовано

- `/resume/` список вакансий + фильтр и поиск.
- `/resume/admin/import` загрузка `txt`, парсинг вакансий, keywords/track/score.
- `/resume/experience` CRUD блоков опыта.
- `/resume/vacancies/{id}` карточка вакансии + кнопка «Собрать резюме».
- `/resume/drafts/{id}` редактор draft + diff + сопроводительное.
- `/resume/resume/{draft_id}/pdf` экспорт PDF с контролем одной страницы.

## Деплой-файлы

- `deploy/resume-radar.service` — systemd unit.
- `deploy/nginx_resume_location.conf` — блок `location /resume/` для текущего server{}.
