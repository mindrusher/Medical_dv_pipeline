# Модуль построения Tracking Satellite для отслеживания изменений атрибутов.

import logging
from datetime import date, timedelta

from psycopg2.extensions import connection


logger = logging.getLogger(__name__)


def calculate_valid_to(
    new_date: date
) -> date:
    """
        Рассчитывает дату окончания действия предыдущей версии.

        Args:
            new_date: Дата начала действия новой версии.
    """

    return new_date - timedelta(days=1)


def load_tracking(
    conn: connection
) -> None:
    """
        Загружает Tracking Satellite с историей изменений атрибутов.

        Для каждого атрибута организации:
        - проверяет текущую активную версию;
        - если значение изменилось, закрывает старую запись через valid_to;
        - создает новую запись с новым valid_from.

        Реализует SCD Type 2 логику хранения истории.

        Args:
            conn: Соединение с PostgreSQL.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    hub_org_hash_key,
                    full_name,
                    short_name,
                    ogrn,
                    inn,
                    address,
                    ved_affiliation_id,
                    load_date::date
                FROM nsi.sat_organization_attrs
            """
        )

        rows = cur.fetchall()

    attributes = [
        "full_name",
        "short_name",
        "ogrn",
        "inn",
        "address",
        "ved_affiliation_id"
    ]

    with conn.cursor() as cur:
        for row in rows:
            hub_key = row[0]
            values = row[1:-1]
            version_date = row[-1]

            for attr, value in zip(attributes, values):
                cur.execute(
                    """
                        SELECT
                            attribute_value
                        FROM nsi.sat_organization_changes
                        WHERE
                            hub_org_hash_key=%s
                            AND attribute_name=%s
                            AND valid_to IS NULL
                        ORDER BY valid_from DESC
                        LIMIT 1
                    """, (hub_key, attr)
                )

                current = cur.fetchone()

                if current and current[0] == value:
                    continue

                if current:
                    cur.execute(
                        """
                            UPDATE nsi.sat_organization_changes
                            SET valid_to=%s
                            WHERE
                            hub_org_hash_key=%s
                            AND attribute_name=%s
                            AND valid_to IS NULL
                        """,
                        (
                            calculate_valid_to(version_date),
                            hub_key,
                            attr
                        )
                    )

                cur.execute(
                    """
                        INSERT INTO nsi.sat_organization_changes
                        (
                        hub_org_hash_key,
                        attribute_name,
                        attribute_value,
                        valid_from
                        )

                        VALUES
                        (%s,%s,%s,%s)

                    """,
                    (
                    hub_key,
                    attr,
                    value,
                    version_date
                    )
                )

    conn.commit()

    logger.info(
        "Tracking satellite loaded"
    )
