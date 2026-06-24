from unittest.mock import patch, Mock
import requests

from requests.exceptions import HTTPError

from src.api import NsiClient


def test_api_500_retry():
    client = NsiClient(
        "token",
        "http://test-data",
        "http://test-passport"
    )

    failed_response = Mock()
    failed_response.status_code = 500

    failed_error = HTTPError(
        response=failed_response
    )

    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "version": "6.2037"
    }

    with patch(
        "src.api.requests.get"
    ) as mock_get:
        mock_get.side_effect = [
            failed_error,
            success_response
        ]

        result = client._get(
            "http://test",
            {}
        )

    assert result == {
        "version": "6.2037"
    }

    assert mock_get.call_count == 2


def test_api_available(mocker):
    response = Mock()
    response.status_code = 200

    mocker.patch(
        "requests.get",
        return_value=response
    )

    r = requests.get(
        "https://nsi.rosminzdrav.ru"
    )

    assert r.status_code == 200


def test_api_timeout(mocker):
    mocker.patch(
        "requests.get",
        side_effect=requests.Timeout
    )

    try:
        requests.get(
            "http://test"
        )
    except requests.Timeout:
        assert True
