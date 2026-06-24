# Хэш-утилиты для Data Vault

import hashlib


def sha256(
        value: str
    ) -> str:
    """
        Генерирует SHA-256 хэш.

        Args:
            value: строка для хэширования.
    """

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def build_hashdiff(row):
    """
        Создает hashdiff для атрибутов организации.

        Хэш-дифф рассчитывается на основе атрибутов и используется
        для обнаружения изменений в SAT данных.

        Args:
            row: Данные организации.
    """
    values = [
        row.get("nameFull"),
        row.get("nameShort"),
        row.get("ogrn"),
        row.get("inn"),
        row.get("moDeptId"),
        row.get("createDate")
    ]

    return sha256(
        "|".join(
            str(x or "")
            for x in values
        )
    )
