from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_claims(
    llm_path: Path,
    human_path: Path,
    *,
    llm_field: str = "original_text",
) -> tuple[list[str], list[str]]:
    llm_data = json.loads(Path(llm_path).read_text(encoding="utf-8"))
    human_data = json.loads(Path(human_path).read_text(encoding="utf-8"))
    llm_items = llm_data.get("result", llm_data.get("claims", []))
    llm_claims = [str(item[llm_field]).strip() for item in llm_items if item.get(llm_field)]
    human_claims = [str(item).strip() for item in human_data.get("claims", []) if str(item).strip()]
    return llm_claims, human_claims


def compute_semantic_matching(
    llm_claims: list[str],
    human_claims: list[str],
    *,
    threshold: float = 0.75,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    matching: str = "many_to_one",
    model: Any | None = None,
) -> dict[str, Any]:
    if matching not in {"one_to_one", "many_to_one"}:
        raise ValueError(f"Unknown matching strategy: {matching}")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between zero and one")
    if not llm_claims or not human_claims:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "num_llm_claims": len(llm_claims),
            "num_human_claims": len(human_claims),
            "num_matched": 0,
            "matching": matching,
        }
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Claim evaluation dependencies are missing; install requirements-paper-claims-eval.txt."
        ) from exc

    embedding_model = model or SentenceTransformer(model_name)
    llm_embeddings = embedding_model.encode(llm_claims, convert_to_numpy=True, normalize_embeddings=True)
    human_embeddings = embedding_model.encode(human_claims, convert_to_numpy=True, normalize_embeddings=True)
    similarities = np.dot(llm_embeddings, human_embeddings.T)

    if matching == "one_to_one":
        rows, columns = linear_sum_assignment(1 - similarities)
        true_positives = sum(1 for row, column in zip(rows, columns) if similarities[row, column] >= threshold)
        false_positives = len(llm_claims) - true_positives
        false_negatives = len(human_claims) - true_positives
    else:
        best_indices = np.argmax(similarities, axis=1)
        best_scores = similarities[np.arange(similarities.shape[0]), best_indices]
        matched_rows = np.where(best_scores >= threshold)[0]
        true_positives = int(len(matched_rows))
        false_positives = len(llm_claims) - true_positives
        covered_humans = {int(best_indices[row]) for row in matched_rows}
        false_negatives = len(human_claims) - len(covered_humans)

    precision = true_positives / (true_positives + false_positives) if llm_claims else 0.0
    recall = true_positives / (true_positives + false_negatives) if human_claims else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "num_llm_claims": len(llm_claims),
        "num_human_claims": len(human_claims),
        "num_matched": true_positives,
        "matching": matching,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate extracted claims against human annotations.")
    parser.add_argument("--llm", type=Path, required=True)
    parser.add_argument("--human", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation_result.json"))
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--model", default="paraphrase-multilingual-MiniLM-L12-v2")
    parser.add_argument("--llm-field", choices=["original_text", "claim"], default="original_text")
    parser.add_argument("--matching", choices=["one_to_one", "many_to_one"], default="many_to_one")
    args = parser.parse_args()
    llm_claims, human_claims = load_claims(args.llm, args.human, llm_field=args.llm_field)
    metrics = compute_semantic_matching(
        llm_claims,
        human_claims,
        threshold=args.threshold,
        model_name=args.model,
        matching=args.matching,
    )
    result = {
        "semantic_matching": metrics,
        "meta": {
            "model": args.model,
            "threshold": args.threshold,
            "llm_field": args.llm_field,
            "matching": args.matching,
            "llm_file": str(args.llm),
            "human_file": str(args.human),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
