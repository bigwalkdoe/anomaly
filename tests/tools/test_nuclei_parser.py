import json

from anomaly_tools.nuclei import parse_nuclei_output

SAMPLE = "\n".join(
    [
        json.dumps(
            {
                "template-id": "cve-2021-test",
                "info": {
                    "name": "Test CVE",
                    "severity": "high",
                    "description": "desc",
                    "remediation": "fix",
                },
                "host": "https://example.com",
                "matched-at": "https://example.com/path",
            }
        ),
        json.dumps(
            {
                "template-id": "exposure",
                "info": {"name": "Info Leak", "severity": "medium", "description": "d"},
                "host": "https://example.com",
            }
        ),
    ]
)


def test_parse_nuclei_output_maps_severity_and_fields():
    result = parse_nuclei_output(SAMPLE, targets=["https://example.com"])
    assert len(result.parsed_findings) == 2
    high = [f for f in result.parsed_findings if f["severity"] == "high"][0]
    assert high["title"] == "Test CVE"
    assert high["remediation"] == "fix"
    assert high["fingerprint"] or "cve-2021-test" in str(high)
