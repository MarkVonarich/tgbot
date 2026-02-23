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


class UserProfile(Base):
    __tablename__ = 'user_profile'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(300), default='')
    target_title: Mapped[str] = mapped_column(String(300), default='')
    contacts: Mapped[str] = mapped_column(String(500), default='')
    summary: Mapped[str] = mapped_column(Text, default='')
    education: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
