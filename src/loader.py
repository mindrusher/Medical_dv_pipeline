# Модуль загрузки данных из API НСИ в RAW слой PostgreSQL.

import uuid
import json
import logging

from src.db import get_connection
from src.api import NsiClient
from src.hashing import sha256
from src.config import (
    API_TOKEN,
    API_DATA_URL,
    API_PASSPORT_URL,
    DICTIONARY_OID
)

from typing import Optional, Iterable, Dict, Any
from psycopg2.extensions import connection


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def get_last_version(
    conn: connection
) -> Optional[str]:
    """
        Получает последнюю загруженную версию справочника из RAW слоя.

        Args:
            conn: Соединение с PostgreSQL.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
                SELECT source_version
                FROM nsi.raw_medical_organizations
                ORDER BY loaded_at DESC
                LIMIT 1
            """
        )

        row = cur.fetchone()

        if row:
            return row[0]

        return None

def get_running_load(conn, version):
    """
    Возвращает незавершенную загрузку текущей версии.
    """

    with conn.cursor() as cur:

        cur.execute(
        """
        SELECT
            load_id,
            page_number

        FROM nsi.load_control

        WHERE source_version=%s
        AND status='RUNNING'

        ORDER BY started_at DESC

        LIMIT 1
        """,
        (version,)
        )

        return cur.fetchone()

def create_load(
    conn: connection,
    version: str
) -> str:
    """
        Создает запись о начале загрузки.

        Используется таблица load_control
        для контроля процесса загрузки и восстановления после сбоя.

        Args:
            conn: Соединение с PostgreSQL.
            version: Версия загружаемого справочника.
    """

    load_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO nsi.load_control
                (
                    load_id,
                    source_version,
                    page_number,
                    status
                )

                VALUES
                (%s,%s,%s,%s)
            """,

            (load_id, version, 0, "RUNNING")
        )

    conn.commit()

    return load_id


def mark_page_done(
    conn: connection,
    load_id: str,
    page: int
) -> None:
    """
        Обновляет номер последней успешно обработанной страницы.

        Args:
            conn: Соединение с PostgreSQL.
            load_id: Идентификатор текущей загрузки.
            page: Номер обработанной страницы.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
                UPDATE nsi.load_control
                SET
                page_number=%s
                WHERE load_id=%s
            """,

            (page, load_id)
        )

    conn.commit()


def insert_raw(
    conn: connection,
    records: Iterable[Dict[str, Any]],
    version: str
) -> None:
    """
        Загружает записи справочника в RAW слой.

        Все данные сохраняются максимально близко к исходному виду,
        дополнительно сохраняется полный JSON payload.

        Args:
            conn: Соединение с PostgreSQL.
            records: Набор записей из API.
            version: Версия справочника.
    """

    with conn.cursor() as cur:
        for row in records:
            raw_key = sha256(
                f"{row['id']}{version}"
            )

            cur.execute(
                """
                    INSERT INTO nsi.raw_medical_organizations
                    (
                        raw_hash_key,
                        org_id,
                        full_name,
                        short_name,
                        ogrn,
                        inn,
                        address,
                        ved_affiliation_id,
                        inclusion_date,
                        raw_payload,
                        source_version
                    )

                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

                    ON CONFLICT DO NOTHING
                """,

                (
                    raw_key,
                    row.get("id"),
                    row.get("nameFull"),
                    row.get("nameShort"),
                    row.get("ogrn"),
                    row.get("inn"),
                    None,
                    row.get("moDeptId"),
                    None,
                    json.dumps(row, ensure_ascii=False),
                    version
                )
            )

    conn.commit()


def run_pipeline() -> None:
    """
        Запускает полный цикл загрузки данных из API в RAW слой.

        Выполняет:
        - получение версии справочника;
        - проверку идемпотентности;
        - загрузку страниц API;
        - сохранение данных в PostgreSQL;
        - фиксацию прогресса загрузки.
    """

    client = NsiClient(
        API_TOKEN,
        API_DATA_URL,
        API_PASSPORT_URL
    )

    version = client.get_version(
        DICTIONARY_OID
    )

    logger.info(
        f"Current API version: {version}"
    )

    conn = get_connection()

    last_version = get_last_version(
        conn
    )


    running_load = get_running_load(
        conn,
        version
    )

    logger.info(
        f"Last version: {last_version}"
    )

    logger.info(
        f"Running load: {running_load}"
    )


    if last_version == version and not running_load:


        logger.info(
            "Version already loaded. Skip."
        )


        conn.close()

        return

    if running_load:

        load_id = running_load[0]

        page = running_load[1] + 1

        logger.info(
            f"Continue load {load_id} from page {page}"
        )

    else:

        load_id = create_load(
            conn,
            version
        )

        page = 1

        logger.info(
            f"Start new load {load_id}"
        )

    buffer = []

    for row in client.get_records(
        DICTIONARY_OID,
        start_page=page
    ):
        buffer.append(row)

        if len(buffer) >= 200:
            insert_raw(
                conn,
                buffer,
                version
            )

            mark_page_done(
                conn,
                load_id,
                page
            )

            logger.info(
                f"Loaded page {page}"
            )

            buffer.clear()

            page += 1

    if buffer:
        insert_raw(
            conn,
            buffer,
            version
        )

        mark_page_done(
            conn,
            load_id,
            page
        )

    with conn.cursor() as cur:

        cur.execute(
        """
        UPDATE nsi.load_control

        SET
            status='FINISHED',
            finished_at=now()

        WHERE load_id=%s
        """,
        (load_id,)
        )

    conn.commit()

    conn.close()

    logger.info(
        "Pipeline finished"
    )


if __name__ == "__main__":

    run_pipeline()
