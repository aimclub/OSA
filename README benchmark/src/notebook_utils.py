import os
import subprocess
import json
import requests
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel
from deepeval.models.base_model import DeepEvalBaseLLM


def parse_folder_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1]

def osa_project_root() -> Path:
    return Path(__file__).parent.parent


# Построение иерархической структуры
def build_tree(paths):
    tree = {}
    for path in paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            current = current.setdefault(part, {})
    return tree

def tree_to_dict(tree):
    result = []
    for name, subtree in sorted(tree.items()):
        if subtree:
            result.append({"name": name, "type": "dir", "children": tree_to_dict(subtree)})
        else:
            result.append({"name": name, "type": "file"})
    return result


class GithubAgent:
    def __init__(self, repo_url: str, branch_name: str = "osa_tool"):
        self.repo_url = repo_url
        self.clone_dir = parse_folder_name(repo_url)
        self.branch_name = branch_name
        self.token = os.getenv("GIT_TOKEN", "")

    def clone_repository(self, depth: Optional[int] = None) -> None:
        if Path(self.clone_dir).exists():
            return
        cmd = ["git", "clone", self.repo_url, self.clone_dir]
        if depth is not None:
            cmd = ["git", "clone", "--depth", str(depth), self.repo_url, self.clone_dir]
        try:
            subprocess.run(cmd, check=True)
        except Exception:
            return


class FileHandler:
    @staticmethod
    def read_text(file_path: str | Path) -> str:
        with open(file_path, encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def read_json(file_path: str | Path) -> dict[str, Any]:
        with open(file_path, encoding="utf-8") as fh:
            return json.load(fh)

    def read(self, file_path: str | Path) -> Any:
        p = Path(file_path)
        if p.suffix == ".json":
            return self.read_json(p)
        return self.read_text(p)


def get_resource_path(file_path: str, module: str = "", submodule: str = "") -> Path:
    p = Path(file_path)
    if p.exists():
        return p
    candidate = Path(submodule) / file_path if submodule else Path(file_path)
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Resource not found: {file_path}")


class GitSettings(BaseModel):
    repository: str
    name: str = ""


class ConfigLoader:
    """Config loader for notebook."""

    def __init__(self, config_dir: str | Path) -> None:
        self.config_dir = Path(config_dir)
        self.config: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)


class CustomLLM(DeepEvalBaseLLM):
    """LLM wrapper for API calls."""

    def __init__(self, api: str = "", model: str = "", url: str = "", prompt: str = "", **kwargs):
        self.api = api
        self.model_name = model
        self.url = url
        self._system_prompt = prompt

    def load_model(self):
        return self

    def generate(self, prompt: str) -> str:
        key = self._get_api_key()
        if not key:
            return ""
        headers = {
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': self.model_name,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        try:
            response = requests.post(f"{self.url}/chat/completions", headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return ""
        except Exception:
            return ""

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt)

    def _get_api_key(self) -> str:
        if self.api == 'openai':
            return os.getenv('OPENAI_API_KEY', '')
        elif self.api == 'openrouter':
            return os.getenv('OPENROUTER_API_KEY', '')
        elif self.api == 'hf':
            return os.getenv('HF_TOKEN', '')
        return ''

    def get_model_name(self) -> str:
        return self.model_name
