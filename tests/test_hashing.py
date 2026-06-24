from src.hashing import sha256, build_hashdiff


def test_hub_key_deterministic():
    key1 = sha256("7101958")
    key2 = sha256("7101958")

    assert key1 == key2


def test_hashdiff_changes_on_attribute_change():
    data1 = {
        "nameFull": "ООО Тест",
        "inn": "123"
    }

    data2 = {
        "nameFull": "ООО Тест 2",
        "inn": "123"
    }

    assert build_hashdiff(data1) != build_hashdiff(data2)


def test_hashdiff_stable_on_same_data():
    data = {
        "nameFull": "ООО Тест",
        "inn": "123"
    }

    assert build_hashdiff(data) == build_hashdiff(data)
