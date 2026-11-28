"""Carry extracted subject/metric/conditions as hints, never as truth labels."""

import json


def review_packet(claim):
    packet = {"claim_id": claim.claim_id, "claim": claim.claim}
    scopes = {}
    for source in claim.sources:
        raw = source.metadata.get("assertion_scope")
        if not isinstance(raw, dict):
            continue
        scope = {k: raw[k] for k in ("subject", "attribute", "conditions") if k in raw}
        if scope:
            scopes[json.dumps(scope, sort_keys=True, ensure_ascii=False)] = scope
    if scopes:
        field = "historical_scope_hints" if claim.claim_id.startswith("corrected:") else "extracted_scope_hints"
        packet[field] = [scopes[k] for k in sorted(scopes)]
    return packet
