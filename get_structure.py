import os
import pandas as pd
import requests
import time
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# df = pd.read_csv("final_readme_eval_with_users.csv")
os.makedirs("data", exist_ok=True)

# for _, row in df.iterrows():
# user = row["user"]
# repo = row["repo_name"]
# commit = row["repo_commit"]
# url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{commit}?recursive=1"
url = "https://api.github.com/repos/reflex-dev/reflex/git/trees/642233b141b8e03131fac8588a3776ef3a14ecce?recursive=1"
filename = "reflex.json"

headers = {
    "Accept": "application/vnd.github.v3+json"
}
if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

try:
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        with open(f"data/{filename}", "w", encoding="utf-8") as f:
            f.write(r.text)
            print(f'{filename} saved successfully')
    else:
        print(f"[{r.status_code}] Error for {url}")
except Exception as e:
    print(f"Request failed for {url}: {e}")
