import re
from osa_tool.operations.codebase.docstring_generation.insert.base_augmentor import BaseAugmentor

class TSJSAugmentor(BaseAugmentor):

    DOC_START = "/**"
    DOC_END = " */"

    def augment(self, file: str, source_code: str, docstrings: dict) -> dict[str, str]:

        if not docstrings:
            return {file: source_code}

        lines = source_code.splitlines(True)

        lines = self._inject_classes(lines, docstrings.get("classes", []))
        lines = self._inject_functions(lines, docstrings.get("functions", []))
        lines = self._inject_methods(lines, docstrings.get("methods", []))

        return {file: "".join(lines)}

    def _inject_classes(self, lines, classes):
        for doc, class_name in classes:
            for i, line in enumerate(lines):
                if re.search(rf"\bexport\s+class\s+{class_name}\b", line):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))
                    break

        return lines

    def _inject_functions(self, lines, functions):
        for doc, meta in functions:
            name = meta["method_name"]

            for i, line in enumerate(lines):
                if re.search(rf"\bexport\s+function\s+{name}\b", line):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))
                    break

        return lines

    def _inject_methods(self, lines, methods):
        for doc, meta in methods:
            name = meta["method_name"]

            for i, line in enumerate(lines):
                # async + normal
                if re.search(rf"\basync\s+{name}\b|\b{name}\s*\(", line):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))
                    break

        return lines

 
    # detect existing doc
    def _has_doc(self, lines, i):
        # look backwards for /**
        for j in range(i, max(i - 5, 0), -1):
            if "/**" in lines[j]:
                return True
        return False

    def _replace_doc(self, lines, i, doc):
        # remove old block
        start = i
        while start > 0 and "/**" not in lines[start]:
            start -= 1

        end = start
        while end < len(lines) and "*/" not in lines[end]:
            end += 1

        new_block = self._format(doc, lines[i])

        return lines[:start] + [new_block + "\n"] + lines[end+1:]

    def _format(self, text: str, line: str) -> str:
        indent = re.match(r"\s*", line).group(0)

        clean = text.strip().replace("*/", "* /")

        body = "\n".join(
            indent + " * " + l if l.strip() else indent + " *"
            for l in clean.split("\n")
        )

        return f"{indent}/**\n{body}\n{indent} */\n"