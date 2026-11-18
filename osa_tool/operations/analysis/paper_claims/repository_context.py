"""Retrieve bounded implementation evidence from the analyzed Git revision."""
import heapq
import re
import subprocess
from pathlib import Path


_WORDS = re.compile(r"[a-z][a-z0-9]{2,}")
_COMMON = set("the and with for from that this are uses using used paper model models method data dataset training implementation results same their each".split())
_SOURCES = ("*.py", "*.r", "*.R", "*.jl", "*.cpp", "*.cu", "*.rs", "*.java", "*.yaml", "*.yml", "*.toml", "*.sh")


def repository_lookup(root: Path):
    git = ["git", "-C", str(root)]
    commit = subprocess.check_output([*git, "rev-parse", "--verify", "HEAD^{commit}"], text=True).strip()

    def retrieve(query: str):
        terms = set(_WORDS.findall(query.lower())) - _COMMON
        if not terms:
            return []
        command = [*git, "grep", "-n", "-z", "-I", "-i", "-E", "-e", "|".join(sorted(terms)), commit, "--", *_SOURCES]
        def matches(stream):
            for line in stream:
                fields = line.rstrip(b"\r\n").split(b"\0", 2)
                if len(fields) != 3 or not fields[1].isdigit() or len(fields[2]) > 1200:
                    continue
                path = fields[0].decode("utf8", errors="replace").removeprefix(commit + ":")
                snippet = fields[2].decode("utf8", errors="replace")
                score = len(set(_WORDS.findall(snippet.lower())) & terms)
                if score:
                    yield (score, path, int(fields[1]), snippet)
        with subprocess.Popen(command, stdout=subprocess.PIPE) as proc:
            best = heapq.nlargest(4, matches(proc.stdout))
            if proc.wait() not in (0, 1):
                raise RuntimeError(f"Cannot read source evidence at {commit}")
        return [dict(evidence_id=f"{commit}:{path}:{line}", commit=commit, path=path,
                     line_start=line, line_end=line, snippet=snippet) for _, path, line, snippet in best]
    return retrieve
