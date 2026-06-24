from datetime import date
from src.tracking import calculate_valid_to


def test_valid_to_one_day_before_new_valid_from():
    result = calculate_valid_to(
        date(2026,6,22)
    )

    assert result == date(2026,6,21)
