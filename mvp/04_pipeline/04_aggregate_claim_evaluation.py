#!/usr/bin/env python3
import glob
import json
import os

import pandas as pd

base_dir = "/home/ilya/OSA/mvp/05_results/v2-fix"
os.chdir(base_dir)

pattern = "**/fix_evaluation*.json"  # "**/**/evaluation*.json"
eval_files = glob.glob(pattern)

print(f"Found {len(eval_files)} evaluation files:\n")

metrics_list = []
for fpath in sorted(eval_files):
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        paper_name = os.path.basename(os.path.dirname(fpath))

        metrics = data.get("semantic_matching", data)
        metrics_list.append({"paper": paper_name, **metrics})

    except Exception as e:
        print(f"Failed to load {fpath}: {e}")

if not metrics_list:
    print("No valid metrics found. Check paths or JSON structure.")
else:
    df = pd.DataFrame(metrics_list)

    df = df.sort_values("paper").reset_index(drop=True)

    print("Aggregated Metrics:")
    print(df.to_string(index=False))

    print("\nSummary Statistics:")
    print(df.describe().round(3))

    df.to_csv("aggregated_claims_metrics.csv", index=False)
    print("\nSaved to aggregated_claims_metrics.csv")
