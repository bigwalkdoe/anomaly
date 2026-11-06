from anomaly_tools.nmap import parse_nmap_xml

SAMPLE_XML = """<?xml version="1.0"?>
<nmaprun scanner="nmap" args="nmap -sV -oX - 127.0.0.1">
<host><status state="up"/>
<address addr="127.0.0.1" addrtype="ipv4"/>
<ports>
<port protocol="tcp" portid="22"><state state="open"/>
<service name="ssh" product="OpenSSH" version="9.0"/></port>
<port protocol="tcp" portid="80"><state state="open"/>
<service name="http" product="nginx" version="1.24"/></port>
</ports>
</host>
</nmaprun>
"""


def test_parse_nmap_xml_finds_open_ports():
    result = parse_nmap_xml(SAMPLE_XML, targets=["127.0.0.1"])
    assert result.exit_code == 0
    assert len(result.parsed_findings) >= 2
    titles = " ".join(f["title"] for f in result.parsed_findings)
    assert "22" in titles
    assert "ssh" in titles.lower() or "OpenSSH" in titles
    assert all("severity" in f for f in result.parsed_findings)
