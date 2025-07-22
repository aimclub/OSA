#!/usr/bin/env python3
"""
convert_docs.py – преобразует project_hierarchy.json → docs_experiment.json

Использование:
    python convert_docs.py project_hierarchy.json docs_experiment.json
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from textwrap import dedent

def normalize_doc(md_block) -> str:
    """
    md_block в project_hierarchy.json – это список строк (абзацев).
    Склеиваем в один многострочный docstring. Если его нет – возвращаем ''.
    """
    if not md_block:
        return ""
    # Если там уже есть перевод‑строк, оставляем как есть
    return "\n".join(md_block).strip("\n")

def strip_indent(code: str) -> str:
    """
    В code_content методы идут с базовым отступом (как в исходном классе).
    Избавляемся от минимального общего отступа, чтобы получить «чистое» тело.
    """
    return dedent(code).rstrip()

def convert_one_file(nodes: list[dict]) -> list[dict]:
    """
    Превращает список узлов из project_hierarchy в список сущностей для docs_experiment.
    """
    result: list[dict] = []

    current_class: dict | None = None
    current_class_indent: int | None = None

    for node in nodes:
        ntype = node.get("type")

        if ntype == "ClassDef":
            # Закрываем предыдущий класс (если был)
            if current_class:
                result.append(current_class)
            current_class = {
                "type": "class",
                "name": node.get("name"),
                "methods": []
            }
            # Сохраняем базовый отступ имени класса
            current_class_indent = node.get("name_column", 0)

        elif ntype == "FunctionDef":
            # Определяем, является ли функция методом текущего класса
            if current_class and node.get("name_column", 0) > current_class_indent:
                method = {
                    "method_name": node["name"],
                    "source_code": strip_indent(node.get("code_content", "")),
                    "first_doc": normalize_doc(node.get("md_content", [])),
                }
                current_class["methods"].append(method)
            else:
                # Module‑level function – можно игнорировать или сохранить отдельно.
                # Условие задачи требует добавлять ТОЛЬКО методы, поэтому пропускаем.
                continue

    # Не забываем добавить последний класс (если был)
    if current_class:
        result.append(current_class)

    return result

def main(src: str, dst: str) -> None:
    with open(src, "r", encoding="utf‑8") as f:
        project = json.load(f)

    docs_experiment: dict = {}

    for filepath, nodes in project.items():
        docs_experiment[filepath] = convert_one_file(nodes)

    with open(dst, "w", encoding="utf‑8") as f:
        json.dump(docs_experiment, f, ensure_ascii=False, indent=4)

    print(f"Готово! Итог сохранён в {dst}")

if __name__ == "__main__":

    src = '/home/andrey/PycharmProjects/RepoAgent/code2flow/.project_doc_record/project_hierarchy.json'
    dst = 'RESULTS/experiment_code2flow.json'
    main(src, dst)


