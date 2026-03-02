from app.sources.jra import JraSource
from app.sources.nar import NarSource


def test_jra_build_records_from_json_extracts_required_fields():
    src = JraSource()
    payloads = [
        {
            "venue": "東京",
            "raceNo": "11R",
            "course": "芝 1600m",
            "going": "良",
            "start": "15:45",
            "field": "18頭",
            "grade": "G1",
        }
    ]
    rows = src._build_records_from_json(payloads, "2026-03-01")
    assert rows
    row = rows[0]
    assert row["venue"] == "東京"
    assert row["race_no"] == 11
    assert row["distance_m"] == 1600
    assert row["surface"] == "芝"
    assert row["going"] == "良"
    assert row["start_time"] == "15:45"
    assert row["field_size"] == 18
    assert row["grade"] == "G1"


def test_nar_build_records_from_json_extracts_required_fields():
    src = NarSource()
    payloads = [
        {
            "venue": "大井",
            "raceNo": "9R",
            "course": "ダート 1200m",
            "going": "稍重",
            "start": "18:20",
            "field": "12頭",
        }
    ]
    rows = src._build_records_from_json(payloads, "2026-03-01")
    assert rows
    row = rows[0]
    assert row["venue"] == "大井"
    assert row["race_no"] == 9
    assert row["distance_m"] == 1200
    assert row["surface"] == "ダート"
    assert row["going"] == "稍重"
    assert row["start_time"] == "18:20"
    assert row["field_size"] == 12
