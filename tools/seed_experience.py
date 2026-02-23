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
    ('Медиапоинт', 'Антифрод партнерки', '2023-01', '2025-03', 'marketing_fraud', 'Сформулировал 15+ ТЗ на витрины, дашборды и процесс ручной проверки партнерского трафика.', 'тз,витрина,dwh,dashboard'),
    ('Медиапоинт', 'Антифрод партнерки', '2023-01', '2025-03', 'marketing_fraud', 'Разбирал модели RevShare/CPA, выявлял аномальные источники трафика и нецелевые конверсии.', 'attribution,cpa,revshare,fraud'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Проверял фрод в маркетинговых кампаниях по AppsFlyer/AppMetrica и снижал аномалии на платном трафике.', 'appsflyer,appmetrica,атрибуция,fraud'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'bi_analytics', 'Построил Superset-дашборды для мониторинга validation rules и ручных правил.', 'superset,dashboard,validation rules'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Настраивал алерты по всплескам аномалий и готовил рекомендации продуктовым командам.', 'alerts,fraud,антифрод'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Проводил пост-атрибуционный анализ фрода и предлагал новые validation/hand rules.', 'post-attribution,validation,triggers'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'marketing_fraud', 'Контролировал корректность SDK-версий и влияние на достоверность атрибуции.', 'sdk,appsflyer,атрибуция'),
    ('МТС', 'Старший маркетинговый аналитик', '2025-03', '2025-07', 'bi_analytics', 'Автоматизировал выгрузку отчетности и совместно с командами datahouse/datacrawler стабилизировал поставку данных.', 'etl,dwh,sql,airflow'),
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
        for row in SEED:
            company, role, pf, pt, track, bullet, tools_csv = row
            tools = [x.strip() for x in tools_csv.split(',') if x.strip()]
            kws = sorted(set(extract_keywords(bullet + ' ' + tools_csv)))
            db.add(
                ExperienceBlock(
                    company=company,
                    role=role,
                    period_from=pf,
                    period_to=pt,
                    track=track,
                    situation='',
                    task='',
                    action='',
                    result='',
                    bullet_ready=bullet,
                    tools_json=json.dumps(tools, ensure_ascii=False),
                    keywords_json=json.dumps(kws, ensure_ascii=False),
                    strength=4,
                )
            )
        db.commit()
        print(f'Seed done: {len(SEED)} blocks')
    finally:
        db.close()


if __name__ == '__main__':
    main()
