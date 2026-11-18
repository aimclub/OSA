"""Conservative, document-local retrieval links from explicit source syntax.

Aliases and part-of links are distinct. Neither is evidence of a contradiction.
Only one part-of hop is allowed; shared ancestors do not make siblings equivalent.
"""
import re


def component_links(claims):
    links, seen = [], set()
    for claim in claims:
        text = claim.original_text
        # Pseudocode declarations, e.g. "Input: encoder E, decoder D".
        for declaration in re.finditer(r"\bInput\s*:\s*([^\n]+)", text):
            for m in re.finditer(r"\b([a-z]{3,})\s+([A-Z])\b", declaration.group(1)):
                row = ("alias", m[1], m[2], m[0])
                if row[:3] not in seen:
                    seen.add(row[:3])
                    links.append(dict(kind=row[0], child=row[1], parent=row[2],
                                      quote=row[3], evidence_id=f"{claim.claim_id}#source0"))
        # Explicit caption scope, e.g. "Figure 2: Input block in Decoder."
        for m in re.finditer(
            r"\bFigure\s+\d+\s*:\s*([A-Za-z]+(?:[ \t]+[A-Za-z]+){0,3})"
            r"[ \t]+in[ \t]+([A-Za-z]+(?:[ \t]+[A-Za-z]+){0,2})[.]", text
        ):
            row = ("part_of", m[1].strip(), m[2].strip(), m[0])
            if row[:3] not in seen:
                seen.add(row[:3])
                links.append(dict(kind=row[0], child=row[1], parent=row[2],
                                  quote=row[3], evidence_id=f"{claim.claim_id}#source0"))
    # Ambiguous symbols are not expanded across unrelated definitions.
    definitions = {}
    for link in links:
        if link["kind"] == "alias":
            definitions.setdefault(link["parent"], set()).add(link["child"].lower())
    return [link for link in links if link["kind"] != "alias"
            or len(definitions[link["parent"]]) == 1]


def mentions(text, entity):
    # Single-letter function symbols are case-sensitive and must be calls.
    if len(entity) == 1:
        return bool(re.search(rf"(?<!\w){re.escape(entity)}\s*\(", text))
    return bool(re.search(rf"(?<!\w){re.escape(entity)}(?!\w)", text, re.I))


def linked_interface_pairs(claims):
    links = component_links(claims)
    aliases = [x for x in links if x["kind"] == "alias"]
    parts = [x for x in links if x["kind"] == "part_of"]
    matches = {}
    for i, left in enumerate(claims):
        # Compare explicit input descriptions with function argument lists.
        if not re.search(r"\b(?:inputs|arguments|receives|takes)\b", left.claim, re.I):
            continue
        for part in parts:
            if not mentions(left.claim, part["child"]):
                continue
            for alias in aliases:
                if alias["child"].lower() != part["parent"].lower():
                    continue
                for j, right in enumerate(claims):
                    if i == j or not mentions(right.claim, alias["parent"]):
                        continue
                    key = tuple(sorted((i, j)))
                    matches.setdefault(key, []).extend([part, alias])
    return matches, links
