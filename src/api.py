#Клиент для взаимодействия с API Министерства здравоохранения.

import requests
import urllib3

from requests.exceptions import HTTPError
from typing import Optional, Iterable, Dict, Any, Generator

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log
)

import logging



logger = logging.getLogger(__name__)


def is_retryable_error(exception):
    """
    Проверяет, является ли ошибка временной
    и требует ли повторного запроса.
    """

    if isinstance(exception, HTTPError):

        return exception.response.status_code in (
            500,
            502,
            503,
            504
        )

    return False


class NsiClient:
    """
        Клиент для загрузки данных словаря.
    """

    def __init__(
        self,
        token: str,
        data_url: str,
        passport_url: str,
        verify_ssl: bool = False
    ) -> None:

        """
            Инициализация клиента.

            Args:
                token: API токен авторизации.
                data_url: endpoint для загрузки справочника.
                passport_url: endpoint получения метаданных справочника.
                verify_ssl: вкл/выкл проверки SSL сертификатов.
        """

        if not verify_ssl:

            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )

        self.token = token
        self.data_url = data_url
        self.passport_url = passport_url
        self.verify_ssl = verify_ssl

    @retry(
        retry=retry_if_exception(
            is_retryable_error
        ),
        stop=stop_after_attempt(10),
        wait=wait_exponential(
            multiplier=2,
            min=2,
            max=60
        ),
        before_sleep=before_sleep_log(
            logger,
            logging.WARNING
        )
    )
    def _get(
        self,
        url: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:

        """
            Выполняет GET запрос к API.

            Args:
                url: API endpoint.
                params: параметры запроса.

        """

        response = requests.get(
            url,
            params=params,
            timeout=30,
            verify=self.verify_ssl
        )

        response.raise_for_status()

        return response.json()

    def get_passport(
        self,
        oid: str
    ) -> Dict[str, Any]:

        """
            Получение метаданных справочника.

            Args:
                oid: Идентификатор справочника.
        """

        return self._get(
            self.passport_url,
            {
                "userKey": self.token,
                "identifier": oid
            }
        )

    def get_version(
        self,
        oid: str
    ) -> str:

        """
            Получение версии справочника.

            Args:
                oid: Идентификатор справочника.

       """
        data = self.get_passport(oid)

        return data["version"]

    def get_page(
        self,
        oid: str,
        page: int
    ) -> Dict[str, Any]:

        """
            Загрузка страницы справочника.

            Args:
                oid: Идентификатор справочника.
                page: Номер страницы.
        """

        return self._get(
            self.data_url,
            {
                "userKey": self.token,
                "identifier": oid,
                "page": page
            }
        )

    def get_records(
        self,
        oid: str,
        start_page: int = 1
    ) -> Generator[Dict[str, Any], None, None]:

        """
            Итерация по записям справочника.

            Args:
                oid: Идентификатор справочника.
                start_page: Начальный номер страницы.

            Yield:
                Маппинг справочника в виде пар ключ-значение.
        """

        page = start_page

        while True:
            response = self.get_page(
                oid,
                page
            )

            rows = response.get(
                "list",
                []
            )

            if not rows:
                break

            for row in rows:
                yield {
                    item["column"]:
                    item["value"]

                    for item in row
                }

            page += 1
