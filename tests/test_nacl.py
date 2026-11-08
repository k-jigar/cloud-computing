import os
import json
import pytest
from tools.nacl_sim import load_rules, decide

def test_nacl_rules_sample():
    rules_path = "network/nacl.json"
    assert os.path.exists(rules_path), "network/nacl.json must exist"
    
    rules = load_rules(rules_path)
    assert "inbound" in rules
    assert "outbound" in rules

    # Test inbound abusive IP blocked
    pkt_blocked = {
        "id": "T01",
        "direction": "inbound",
        "protocol": "tcp",
        "port": 443,
        "address": "198.51.100.25"
    }
    action, rule = decide(rules, pkt_blocked)
    assert action == "deny"

    # Test inbound HTTPS allowed from internet
    pkt_allow_https = {
        "id": "T02",
        "direction": "inbound",
        "protocol": "tcp",
        "port": 443,
        "address": "203.0.113.10"
    }
    action, rule = decide(rules, pkt_allow_https)
    assert action == "allow"

    # Test SSH denied from public internet
    pkt_deny_ssh = {
        "id": "T03",
        "direction": "inbound",
        "protocol": "tcp",
        "port": 22,
        "address": "203.0.113.10"
    }
    action, rule = decide(rules, pkt_deny_ssh)
    assert action == "deny"

    # Test SSH allowed from management subnet 10.20.5.128/27
    pkt_allow_ssh = {
        "id": "T04",
        "direction": "inbound",
        "protocol": "tcp",
        "port": 22,
        "address": "10.20.5.130"
    }
    action, rule = decide(rules, pkt_allow_ssh)
    assert action == "allow"

    # Test outbound 8000 allowed to app subnet 10.20.0.0/22
    pkt_outbound_app = {
        "id": "T05",
        "direction": "outbound",
        "protocol": "tcp",
        "port": 8000,
        "address": "10.20.1.50"
    }
    action, rule = decide(rules, pkt_outbound_app)
    assert action == "allow"

