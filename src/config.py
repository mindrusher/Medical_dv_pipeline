import os

from dotenv import load_dotenv


load_dotenv()


API_TOKEN = os.getenv(
    "NSI_TOKEN"
)


DICTIONARY_OID = (
    "1.2.643.5.1.13.13.11.1461"
)


API_DATA_URL = (
    "https://nsi.rosminzdrav.ru/port/rest/data"
)


API_PASSPORT_URL = (
    "https://nsi.rosminzdrav.ru/port/rest/passport"
)
