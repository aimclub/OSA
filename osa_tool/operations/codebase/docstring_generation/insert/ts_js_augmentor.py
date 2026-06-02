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

            class_pattern = re.compile(rf"^\s*(export\s+)?(abstract\s+)?class\s+{re.escape(class_name)}\b")

            for i, line in enumerate(lines):
                if class_pattern.search(line):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))
                    break

        return lines

    def _inject_functions(self, lines, functions):
        for doc, meta in functions:
            name = meta["method_name"]
            patterns = [
                re.compile(rf"^\s*export\s+(async\s+)?function\s+{re.escape(name)}\s*\("),
                re.compile(rf"^\s*(async\s+)?function\s+{re.escape(name)}\s*\("),
                re.compile(rf"^\s*export\s+const\s+{re.escape(name)}\s*=\s*(async\s*)?\("),
                re.compile(rf"^\s*const\s+{re.escape(name)}\s*=\s*(async\s*)?\("),
                re.compile(rf"^\s*export\s+const\s+{re.escape(name)}\s*=\s*(async\s*)?.*=>"),
                re.compile(rf"^\s*const\s+{re.escape(name)}\s*=\s*(async\s*)?.*=>"),
            ]

            for i, line in enumerate(lines):
                if any(p.search(line) for p in patterns):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))

                    break

        return lines

    def _inject_methods(self, lines, methods):
        for doc, meta in methods:
            name = meta["method_name"]
            patterns = [
                # public/private/protected async static method<T>(
                re.compile(
                    rf"""^\s*
                    (?:
                        public|private|protected|static|readonly|async|get|set
                    |\s)+
                    \s*
                    {re.escape(name)}
                    \s*
                    (?:<[^>]*>)?
                    \s*
                    \(
                    """,
                    re.VERBOSE,
                ),
                # async method<T>(
                re.compile(
                    rf"""^\s*
                    async\s+
                    {re.escape(name)}
                    \s*
                    (?:<[^>]*>)?
                    \s*
                    \(
                    """,
                    re.VERBOSE,
                ),
                # method<T>(
                re.compile(
                    rf"""^\s*
                    {re.escape(name)}
                    \s*
                    (?:<[^>]*>)?
                    \s*
                    \(
                    """,
                    re.VERBOSE,
                ),
                # getter/setter
                re.compile(
                    rf"""^\s*
                    (?:public|private|protected|static\s+)*?
                    (?:get|set)\s+
                    {re.escape(name)}
                    \b
                    """,
                    re.VERBOSE,
                ),
            ]

            for i, line in enumerate(lines):
                stripped = line.strip()
                # skip obvious calls/usages
                if (
                    stripped.startswith("return ")
                    or stripped.startswith("if ")
                    or stripped.startswith("while ")
                    or stripped.startswith("for ")
                    or stripped.startswith("switch ")
                    or stripped.startswith("catch ")
                    or stripped.startswith("new ")
                    or re.search(rf"\.\s*{re.escape(name)}\s*\(", stripped)
                    or "=" in stripped
                ):
                    continue

                if any(p.search(line) for p in patterns):
                    if self._has_doc(lines, i):
                        lines = self._replace_doc(lines, i, doc)
                    else:
                        lines.insert(i, self._format(doc, line))
                    break

        return lines

    def _has_doc(self, lines, i):
        j = i - 1
        while j >= 0:
            current = lines[j].strip()
            # skip empty lines
            if not current:
                j -= 1
                continue

            # direct jsdoc above declaration
            if current.endswith("*/"):
                k = j
                while k >= 0:
                    if "/**" in lines[k]:
                        return True
                    # stop if another code construct encountered
                    if lines[k].strip() and not lines[k].strip().startswith("*"):
                        break
                    k -= 1
            return False

        return False

    def _replace_doc(self, lines, i, doc):
        start = i - 1
        while start >= 0:
            if "/**" in lines[start]:
                break
            start -= 1

        if start < 0:
            return lines

        end = start

        while end < len(lines):
            if "*/" in lines[end]:
                break
            end += 1

        new_block = self._format(doc, lines[i])

        return lines[:start] + [new_block] + lines[end + 1 :]

    def _format(self, text: str, line: str) -> str:
        indent = re.match(r"\s*", line).group(0)
        clean = text.strip()

        # remove existing jsdoc wrappers if already present
        clean = re.sub(r"^\s*/\*\*", "", clean)
        clean = re.sub(r"\*/\s*$", "", clean)

        # remove leading *
        clean_lines = []

        for l in clean.splitlines():
            l = re.sub(r"^\s*\*\s?", "", l.rstrip())
            clean_lines.append(l)

        clean = "\n".join(clean_lines)
        clean = clean.replace("*/", "* /")

        body = "\n".join(indent + " * " + l if l.strip() else indent + " *" for l in clean.split("\n"))

        return f"{indent}/**\n" f"{body}\n" f"{indent} */\n"