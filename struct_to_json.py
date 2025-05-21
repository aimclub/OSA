import json
import os


# Построение иерархической структуры
def build_tree(paths):
    tree = {}
    for path in paths:
        parts = path.split('/')
        current = tree
        for part in parts:
            current = current.setdefault(part, {})
    return tree

# Преобразование в формат с выводом как список файлов/директорий
def tree_to_dict(tree):
    result = []
    for name, subtree in sorted(tree.items()):
        if subtree:
            result.append({"name": name, "type": "dir", "children": tree_to_dict(subtree)})
        else:
            result.append({"name": name, "type": "file"})
    return result

# for file in os.listdir('data'):
#     with open(f'data/{file}', 'r', encoding='utf-8') as f:
#         data = json.load(f)

# # Извлечение путей
#     stop_words = ['assets', 'results', 'sources', 'packages', 'images', 'data']
#     paths = [
#         entry['path']
#         for entry in data.get('tree', [])
#         if not any(f"/{stop}/" in f"/{entry['path']}/" or entry['path'].startswith(f"{stop}/") for stop in stop_words)
#     ]
#     # Построение финальной структуры
#     tree = build_tree(paths)
#     structured = tree_to_dict(tree)

# Сохранение результата
    # with open(f'data/struct_{file}', 'w', encoding='utf-8') as f:
    #     json.dump(structured, f, indent=2, ensure_ascii=False)

# Пример вывода:
# [
#   {
#     "name": ".github",
#     "type": "dir",
#     "children": [
#       {"name": "ISSUE_TEMPLATE.md", "type": "file"},
#       {
#         "name": "workflows",
#         "type": "dir",
#         "children": [{"name": "main.yml", "type": "file"}]
#       }
#     ]
#   },
#   ...
# ]
