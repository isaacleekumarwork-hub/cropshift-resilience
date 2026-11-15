"""Live integration smoke test against the real NASA POWER service.

NETWORK-DEPENDENT. Skipped by default. Run it explicitly:

    python -m pytest tests/test_live_power.py --run-live

It is bounded (one request, ten days, two parameters, at most three attempts)
and repeatable: it asks for a period in 2020 that NASA finalised long ago, and
compares the answer with the response recorded on 14 November 2026.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.data_validation import build_dataset
from src.models import DataOrigin
from src.nasa_client import PowerClient, PowerRequest

pytestmark = pytest.mark.live

LIVE_REQUEST = dict(
    latitude=-1.58,
    longitude=37.24,
    start=date(2020, 1, 1),
    end=date(2020, 1, 10),
    parameters=("T2M", "PRECTOTCORR"),
)


def test_live_retrieval_of_a_small_historical_range(recorded_envelope):
    request = PowerRequest(**LIVE_REQUEST)
    retrieval = PowerClient(timeout=60, max_retries=2).fetch(request)

    assert retrieval.status_code == 200
    assert retrieval.origin is DataOrigin.NETWORK
    assert retrieval.payload["header"]["time_standard"] == "UTC"

    dataset = build_dataset(retrieval)
    assert dataset.quality.accepted
    assert dataset.variables == ("precipitation", "air_temperature_mean")
    for series in dataset.series:
        assert len(series.observations) == 10 and series.missing_count == 0

    # Repeatable: finalised history should match what was recorded earlier.
    recorded = recorded_envelope["payload"]["properties"]["parameter"]
    for parameter, variable in (("T2M", "air_temperature_mean"), ("PRECTOTCORR", "precipitation")):
        live_values = [item.value for item in dataset.get(variable).observations]
        expected = [recorded[parameter][f"202001{day:02d}"] for day in range(1, 11)]
        assert live_values == pytest.approx(expected, abs=0.01)
