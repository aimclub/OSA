import json
import os

import pandas as pd

from metrics import calculate_bert_score, calculate_concise, flesch_reading_ease


def find_json_files(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        if "docs_experiment.json" in filenames:
            yield os.path.join(dirpath, "docs_experiment.json")

def extract_repoagent_pairs(repoagent_json_path, reference_json_path, pref):
    with open(repoagent_json_path, 'r', encoding='utf-8') as f:
        repoagent_data = json.load(f)
    with open(reference_json_path, 'r', encoding='utf-8') as f:
        reference_data = json.load(f)
    pairs = []
    for repo_key, items in repoagent_data.items():
        ref_items = reference_data.get(f"{pref}/{repo_key}", [])
        for item_id, entry in enumerate(items):
            if 'details' in entry:
                details = entry['details']
                original = ''
                if item_id < len(ref_items):
                    original = ref_items[item_id].get('docstring', '')
                generated = details.get('second_doc') or details.get('first_doc') or ''
                if original and generated:
                    pairs.append((original, generated))
            if 'methods' in entry and isinstance(entry['methods'], list):
                for method_id, method in enumerate(entry['methods']):
                    original = ''
                    if item_id < len(ref_items) and 'methods' in ref_items[item_id]:
                        ref_methods = ref_items[item_id]['methods']
                        if method_id < len(ref_methods):
                            original = ref_methods[method_id].get('docstring', '')
                    generated = method.get('second_doc') or method.get('first_doc') or ''
                    if original and generated:
                        pairs.append((original, generated))
    return pairs

def main(root_dir):
    repo_results = []
    for json_file in find_json_files(root_dir):
        repo_name = os.path.basename(os.path.dirname(json_file))
        if "repoagent" in repo_name:
            # Determine reference path and prefix
            if "albumentations_repoagent" in repo_name:
                reference_json = os.path.join(root_dir, "albumentations/docs_experiment.json")
                pref = "albumentations"
            elif "simdjson_repoagent" in repo_name:
                reference_json = os.path.join(root_dir, "simdjson/docs_experiment.json")
                pref = "simdjson"
            elif "flask_repoagent" in repo_name:
                reference_json = os.path.join(root_dir, "flask/docs_experiment.json")
                pref = "flask"
            elif "greenlet_repoagent" in repo_name:
                reference_json = os.path.join(root_dir, "greenlet/docs_experiment.json")
                pref = "greenlet"
            elif "code2flow_repoagent" in repo_name:
                reference_json = os.path.join(root_dir, "code2flow/docs_experiment.json")
                pref = "code2flow"
            else:
                continue
            print(f"Processing {repo_name} from {json_file}")
            pairs = extract_repoagent_pairs(json_file, reference_json, pref)
            flesch_scores = []
            bert_scores = []
            concise_scores = []
            for original, generated in pairs:
                flesch = flesch_reading_ease(generated)
                bert = calculate_bert_score(original, generated)
                concise = calculate_concise(original, generated)
                flesch_scores.append(flesch)
                bert_scores.append(bert)
                concise_scores.append(concise)
            mean_flesch = sum(flesch_scores) / len(flesch_scores) if flesch_scores else 0.0
            mean_bert = sum(bert_scores) / len(bert_scores) if bert_scores else 0.0
            mean_concise = sum(concise_scores) / len(concise_scores) if concise_scores else 0.0
            repo_results.append({
                'repo': repo_name,
                'json_file': json_file,
                'mean_flesch': mean_flesch,
                'mean_bert': mean_bert,
                'mean_concise': mean_concise,
                'num_pairs': len(pairs)
            })
    df = pd.DataFrame(repo_results)
    csv_path = os.path.join(root_dir, "repoagent_docstring_scores.csv")
    df.to_csv(csv_path, index=False)
    for r in repo_results:
        print(f"{r['repo']}: mean_flesch={r['mean_flesch']:.2f}, mean_bert={r['mean_bert']:.4f}, mean_concise={r['mean_concise']:.4f} (n={r['num_pairs']})")
    print(f"Total repoagents evaluated: {len(repo_results)}")
    print(f"Results saved to {csv_path}")

if __name__ == "__main__":
    main("/root/work/itmo/OSA/")