import json

from anomaly_tools.ffuf import parse_ffuf_json

SAMPLE = json.dumps(
    {
        "results": [
            {
                "url": "https://example.com/admin",
                "status": 200,
                "length": 123,
                "words": 10,
                "lines": 5,
            },
            {"url": "https://example.com/.git", "status": 403, "length": 0, "words": 0, "lines": 0},
        ],
        "config": {"url": "https://example.com/FUZZ"},
    }
)


def test_parse_ffuf_json():
    result = parse_ffuf_json(SAMPLE, targets=["https://example.com"])
    assert len(result.parsed_findings) == 2
    admin = [f for f in result.parsed_findings if "admin" in f["title"]][0]
    assert admin["severity"] in ("info", "low", "medium")
    assert "200" in admin["description"] or "200" in admin["title"]
