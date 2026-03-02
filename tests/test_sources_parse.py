from app.sources.jra import JraSource
from app.sources.nar import NarSource


def test_jra_build_records_from_html_extracts_fields():
    src = JraSource()
    html = """
    <tr><td>東京</td><td>11R</td><td>芝 1600m</td><td>馬場:良</td><td>15:45</td><td>18頭</td><td>G1</td></tr>
    """
    rows = src._build_records_from_html([html], "2026-03-01")
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


def test_jra_build_records_from_html_allows_null_optional_fields():
    src = JraSource()
    html = "<tr><td>中山</td><td>1R</td></tr>"
    rows = src._build_records_from_html([html], "2026-03-01")
    assert rows
    row = rows[0]
    assert row["venue"] == "中山"
    assert row["race_no"] == 1
    assert row["distance_m"] is None
    assert row["surface"] is None


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
