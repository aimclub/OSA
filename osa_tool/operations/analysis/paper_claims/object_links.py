"""Bounded retrieval by explicitly named document objects, without a model."""
import re
from collections import defaultdict
from itertools import combinations, zip_longest

REF = re.compile(r"\b(figure|fig\.?|table|algorithm|alg\.?)\s*(\d+[a-z]?)(?:\(([a-z])\))?", re.I)
DESCRIPTION = re.compile(r"\b(caption|depicts?|shows?|illustrates?|describes?|plots?|contains?|summari[sz]es?|showcases?)\b", re.I)


def references(text):
    result = set()
    for m in REF.finditer(text):
        kind = m[1].lower().rstrip(".")
        kind = {"fig": "figure", "alg": "algorithm"}.get(kind, kind)
        # Panels remain distinct; whole-object assertions can link to a panel.
        result.add((kind, m[2].lower(), (m[3] or "").lower()))
    return result


def object_pairs(claims):
    groups = defaultdict(list)
    refs = [references(c.claim) for c in claims]
    for i, values in enumerate(refs):
        for kind, number, panel in values:
            groups[kind, number].append(i)
    streams = []
    for key, indices in sorted(groups.items()):
        rows = []
        for i, j in combinations(sorted(set(indices)), 2):
            a = {p for k, n, p in refs[i] if (k, n) == key}
            b = {p for k, n, p in refs[j] if (k, n) == key}
            if "" not in a | b and not a & b:
                continue
            score = sum(bool(DESCRIPTION.search(claims[x].claim)) for x in (i, j))
            separate_source = claims[i].original_text != claims[j].original_text
            rows.append((i, j, key, score, separate_source))
        streams.append(sorted(rows, key=lambda r: (-r[3], -r[4], r[0], r[1])))
    # Round-robin prevents a large table from taking every reserved slot.
    ordered, seen = [], set()
    for batch in zip_longest(*streams):
        for row in batch:
            if row is not None and row[:2] not in seen:
                seen.add(row[:2])
                ordered.append(row)
    return ordered
