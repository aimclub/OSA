import json
import os

import pandas as pd

from metrics import calculate_bert_score, calculate_concise, flesch_reading_ease


def find_json_files(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        if "docs_experiment.json" in filenames:
            yield os.path.join(dirpath, "docs_experiment.json")

def extract_docstring_pairs(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pairs = []
    if 'albumentations_repoagent' in json_path:
        orig_json_pth = "OSA/albumentations/docs_experiment.json" 
        pref = "albumentations"
        with open(orig_json_pth, 'r', encoding='utf-8') as f:
            orig_data = json.load(f)
    elif "simdjson_repoagent" in json_path:
        orig_json_pth = "OSA/simdjson/docs_experiment.json"
        pref = "simdjson"
        with open(orig_json_pth, 'r', encoding='utf-8') as f:
            orig_data = json.load(f)
    elif "flask_repoagent" in json_path:
        orig_json_pth = "OSA/flask/docs_experiment.json"
        pref = "flask"
        with open(orig_json_pth, 'r', encoding='utf-8') as f:
            orig_data = json.load(f)
    else:
        orig_data = None

    for repo_key, items in data.items():
        for item_id,entry in enumerate(items):
            if 'details' in entry:
                details = entry['details']
                if orig_data is not None:
                    if item_id >= len(orig_data[f"{pref}/{repo_key}"]):
                        original = ''
                    else:
                        original = orig_data[f"{pref}/{repo_key}"][item_id].get('docstring', '')
                else:
                    original = details.get('docstring', '')
                generated = details.get('second_doc') or details.get('first_doc') or ''
                if original and generated:
                    pairs.append((original, generated))
            if 'methods' in entry and isinstance(entry['methods'], list):
                for method in entry['methods']:
                    if orig_data is not None:
                        if item_id >= len(orig_data[f"{pref}/{repo_key}"]):
                            original = ''
                        else:
                            original = orig_data[f"{pref}/{repo_key}"][item_id].get('docstring', '')
                    else:
                        original = method.get('docstring', '')
                    generated = method.get('second_doc') or method.get('first_doc') or ''
                    if original and generated:
                        pairs.append((original, generated))
    return pairs

def main(root_dir):
    repo_results = []
    for json_file in find_json_files(root_dir):
        try:
            repo_name = os.path.basename(os.path.dirname(json_file))
            if "albumentations_repoagent" in json_file:
                repo_name = "albumentations_repoagent"
            elif "simdjson_repoagent" in json_file:
                repo_name = "simdjson_repoagent"
            elif "flask_repoagent" in json_file:
                repo_name = "flask_repoagent"
            print(f"Processing {repo_name} from {json_file}")

            pairs = extract_docstring_pairs(json_file)
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
        except Exception as e:
            print(f"Error processing {json_file}: {e}")

    df = pd.DataFrame(repo_results)
    csv_path = os.path.join(root_dir, "docstring_scores.csv")
    df.to_csv(csv_path, index=False)

    for r in repo_results:
        print(f"{r['repo']}: mean_flesch={r['mean_flesch']:.2f}, mean_bert={r['mean_bert']:.4f}, mean_concise={r['mean_concise']:.4f} (n={r['num_pairs']})")
    print(f"Total repos evaluated: {len(repo_results)}")
    print(f"Results saved to {csv_path}")


if __name__ == "__main__":
    main("OSA/")