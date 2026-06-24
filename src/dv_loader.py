# Модуль загрузки Data Vault слоя из RAW таблицы.

import json
import logging

from src.db import get_connection
from src.hashing import sha256, build_hashdiff
from src.tracking import load_tracking

from datetime import datetime

from typing import Optional, Dict, Any
from psycopg2.extensions import connection


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def parse_date(
    value: Optional[str]
) -> Optional[datetime.date]:
    """
        Преобразует дату из формата API в формат PostgreSQL DATE.

        API возвращает даты в формате DD.MM.YYYY.
        Некорректные или пустые значения преобразуются в None.

        Args:
            value: Дата из JSON.

    """

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%d.%m.%Y"
        ).date()

    except ValueError:
        return None
        

def load_hub(
    conn: connection
) -> None:
    """
        Загружает ключи организаций в HUB.

        HUB содержит уникальные организации.
        Повторная загрузка существующих ключей игнорируется.

        Args:
            conn: Соединение с PostgreSQL.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO nsi.hub_organization
                (
                    hub_org_hash_key,
                    org_id,
                    load_date,
                    record_source
                )

                SELECT DISTINCT

                encode(
                    digest(
                        org_id,
                        'sha256'
                    ),
                    'hex'
                ),

                org_id,
                now(),
                'nsi.rosminzdrav.ru'

                FROM nsi.raw_medical_organizations
                ON CONFLICT DO NOTHING;
            """
        )

    conn.commit()


def build_address(
    payload: Dict[str, Any]
) -> str:
    """
        Формирует адрес организации из полей API.

        Args:
            payload: JSON объект организации.
    """

    parts = [
        payload.get("addrRegionName"),
        payload.get("areaName"),
        payload.get("streetName"),
        payload.get("house")
    ]

    return ", ".join(
        x for x in parts if x
    )


def load_sat(
    conn: connection
) -> None:
    """
        Загружает сателлит атрибутов организаций.

        Использует hashdiff для определения изменений:
        если набор атрибутов изменился, создается новая версия SAT.

        Args:
            conn: Соединение с PostgreSQL.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    raw_payload,
                    org_id
                FROM nsi.raw_medical_organizations
            """
        )

        rows = cur.fetchall()

    new_versions = 0

    with conn.cursor() as cur:
        for payload, org_id in rows:
            diff = build_hashdiff(payload)
            hub_key = sha256(org_id)
            cur.execute(
                """
                    SELECT 1
                    FROM nsi.sat_organization_attrs
                    WHERE hub_org_hash_key=%s
                    AND hashdiff=%s
                    LIMIT 1
                """, (hub_key, diff)
            )

            exists = cur.fetchone()

            if exists:
                continue

            cur.execute(
                """
                    INSERT INTO nsi.sat_organization_attrs
                    (
                        hub_org_hash_key,
                        hashdiff,
                        load_date,
                        full_name,
                        short_name,
                        ogrn,
                        inn,
                        address,
                        ved_affiliation_id,
                        inclusion_date,
                        record_source
                    )

                    VALUES
                    (%s,%s,now(),%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    hub_key,
                    diff,
                    payload.get("nameFull"),
                    payload.get("nameShort"),
                    payload.get("ogrn"),
                    payload.get("inn"),
                    build_address(payload),
                    payload.get("moDeptId"),
                    parse_date(
                        payload.get("createDate")
                    ),
                    "nsi.rosminzdrav.ru"
                )
            )

            new_versions += 1
    
    conn.commit()

    logger.info(
        f"New SAT versions detected: {new_versions}"
    )


def run(
    conn: connection
) -> None:
    """
        Запускает загрузку Data Vault слоя.

        Последовательность:
        - загрузка HUB;
        - загрузка SAT;
        - построение Tracking Satellite.

        Args:
            conn: Соединение с PostgreSQL.
    """

    logger.info(
        "Loading HUB"
    )

    load_hub(conn)

    logger.info(
        "Loading SAT"
    )

    load_sat(conn)

    logger.info(
        "Loading tracking satellite"
    )

    load_tracking(conn)

    conn.close()

    logger.info(
        "DV load finished"
    )


if __name__ == "__main__":

    conn = get_connection()

    run(conn)
