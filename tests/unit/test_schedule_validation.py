import pytest
from backend.models import Schedule
from pydantic import ValidationError

def test_recurring_schedule_requires_day():
    with pytest.raises(ValidationError):
        Schedule(
            routine_id="r1",
            schedule_type="recurring",
            day_of_week=None
        )

def test_specific_date_schedule_requires_date():
    with pytest.raises(ValidationError):
        Schedule(
            routine_id="r1",
            schedule_type="specific_date",
            specific_date=None
        )

def test_valid_recurring_schedule():
    s = Schedule(
        routine_id="r1",
        schedule_type="recurring",
        day_of_week=0
    )
    assert s.day_of_week == 0

def test_valid_specific_date_schedule():
    s = Schedule(
        routine_id="r1",
        schedule_type="specific_date",
        specific_date="2026-05-23"
    )
    assert s.specific_date == "2026-05-23"
