"""
Claim Extraction Evaluator: LLM vs Human Expert
Uses multilingual embeddings + Hungarian algorithm for optimal semantic matching.
"""

"""
python evaluate_claims.py --llm /home/ilya/OSA/marker_output/paper_7/final_result_7.json --human /home/ilya/OSA/marker_output/paper_7/claims_7.json

#   --output evaluation_result.json \
#   --threshold 0.75
"""

import argparse
import json

import numpy as np
from scipy.optimize import linear_sum_assignment
from sentence_transformers import SentenceTransformer


def load_claims_with_field(llm_path: str, human_path: str, llm_field: str = "original_text"):
    with open(llm_path, "r", encoding="utf-8") as f:
        llm_data = json.load(f)
    with open(human_path, "r", encoding="utf-8") as f:
        human_data = json.load(f)

    llm_claims = [item[llm_field].strip() for item in llm_data.get("result", []) if item.get(llm_field)]
    human_claims = [c.strip() for c in human_data.get("claims", []) if c.strip()]
    return llm_claims, human_claims


def compute_semantic_matching(
    llm_claims: list,
    human_claims: list,
    threshold: float = 0.75,
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    matching: str = "one_to_one",
):
    if not llm_claims or not human_claims:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "num_llm_claims": len(llm_claims),
            "num_human_claims": len(human_claims),
            "num_matched": 0,
        }

    print(f"Loading embedding model: {model_name} ...")
    model = SentenceTransformer(model_name)

    # Encode & normalize for fast cosine similarity via dot product
    llm_embs = model.encode(llm_claims, convert_to_numpy=True, normalize_embeddings=True)
    human_embs = model.encode(human_claims, convert_to_numpy=True, normalize_embeddings=True)

    # Cosine similarity matrix
    sim_matrix = np.dot(llm_embs, human_embs.T)

    if matching == "one_to_one":
        # Hungarian algorithm finds optimal 1:1 pairing (minimizes cost = 1 - similarity)
        cost_matrix = 1 - sim_matrix
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        valid_matches = [(r, c, sim_matrix[r, c]) for r, c in zip(row_ind, col_ind) if sim_matrix[r, c] >= threshold]
        TP = len(valid_matches)
        FP = len(llm_claims) - TP
        FN = len(human_claims) - TP
    elif matching == "many_to_one":
        # Each LLM claim can match its best human claim independently.
        # This is useful when one human sentence contains multiple atomic claims.
        best_human_idx = np.argmax(sim_matrix, axis=1)
        best_scores = sim_matrix[np.arange(sim_matrix.shape[0]), best_human_idx]
        matched_rows = np.where(best_scores >= threshold)[0]

        TP = int(len(matched_rows))
        FP = len(llm_claims) - TP

        # For recall, count how many unique human claims are covered.
        covered_humans = set(int(best_human_idx[r]) for r in matched_rows)
        FN = len(human_claims) - len(covered_humans)
    else:
        raise ValueError(f"Unknown matching strategy: {matching}")

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "num_llm_claims": len(llm_claims),
        "num_human_claims": len(human_claims),
        "num_matched": TP,
        "matching": matching,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM claim extraction against human expert annotations.")
    parser.add_argument("--llm", required=True, help="Path to LLM output JSON")
    parser.add_argument("--human", required=True, help="Path to human expert JSON")
    parser.add_argument("--output", default="evaluation_result.json", help="Path to save evaluation results JSON")
    parser.add_argument(
        "--threshold", type=float, default=0.75, help="Cosine similarity threshold for matching (default: 0.75)"
    )
    parser.add_argument(
        "--model", default="paraphrase-multilingual-MiniLM-L12-v2", help="Sentence transformer model name"
    )
    parser.add_argument(
        "--llm-field",
        default="original_text",
        choices=["original_text", "claim"],
        help="Which LLM field to evaluate against human claims",
    )
    parser.add_argument(
        "--matching",
        default="many_to_one",
        choices=["one_to_one", "many_to_one"],
        help="Matching strategy: one_to_one (Hungarian) or many_to_one (best human per LLM claim)",
    )
    args = parser.parse_args()

    print("Loading claims...")
    llm_claims, human_claims = load_claims_with_field(args.llm, args.human, llm_field=args.llm_field)
    print(f"  LLM claims: {len(llm_claims)}")
    print(f"  Human claims: {len(human_claims)}")
    print(f"  LLM field: {args.llm_field}")
    print(f"  Matching: {args.matching}")

    print("Computing semantic matching metrics...")
    metrics = compute_semantic_matching(
        llm_claims,
        human_claims,
        threshold=args.threshold,
        model_name=args.model,
        matching=args.matching,
    )

    # Wrap in requested structure
    result = {
        "semantic_matching": metrics,
        "meta": {
            "model": args.model,
            "threshold": args.threshold,
            "llm_field": args.llm_field,
            "matching": args.matching,
            "llm_file": args.llm,
            "human_file": args.human,
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Evaluation saved to {args.output}")
    print(f"   Precision: {metrics['precision']:.4f} | Recall: {metrics['recall']:.4f} | F1: {metrics['f1']:.4f}")
    print(
        f"   Matched: {metrics['num_matched']}/{min(metrics['num_llm_claims'], metrics['num_human_claims'])} possible pairs"
    )


if __name__ == "__main__":
    main()
