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

            class_pattern = re.compile(rf"^\s*(export\s+)?(default\s+)?(abstract\s+)?class\s+{re.escape(class_name)}\b")

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
        # Decide targets first (pure scan, no mutation) so `used` line indices stay
        # stable, then apply bottom-up so earlier indices remain valid while we edit.
        used = set()
        actions = []

        # lines inside an existing comment must never be matched as a declaration
        # (e.g. a JSDoc body line ` * save(entity) ...` would otherwise look like a
        # generator method `* save(`), which would corrupt the file on regeneration.
        comment_idx = self._comment_lines(lines)

        # methods may arrive out of source order (they are generated in dependency
        # order). Map them to declarations by ascending source position so two methods
        # sharing a name each get their OWN doc instead of a swapped one.
        ordered = sorted(methods, key=lambda dm: dm[1].get("start_line", 0))

        for doc, meta in ordered:
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
                # generator method: * method<T>(  /  async * method(  /  static * method(
                re.compile(
                    rf"""^\s*
                    (?:public|private|protected|static|readonly|async|\s)*
                    \*\s*
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
            # class field arrow: name = (...) =>  /  name = async (...) =>  /  name = x =>
            field_arrow = re.compile(
                rf"^\s*(?:(?:public|private|protected|static|readonly)\s+)*"
                rf"{re.escape(name)}\s*=\s*(?:async\s+)?"
                rf"(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*(?::\s*[^=]+?)?\s*=>"
            )

            for i, line in enumerate(lines):
                if i in used or i in comment_idx:
                    continue

                stripped = line.strip()
                is_field_arrow = bool(field_arrow.search(line))

                # skip obvious calls / control-flow / usages
                if (
                    stripped.startswith("return ")
                    or stripped.startswith("if ")
                    or stripped.startswith("while ")
                    or stripped.startswith("for ")
                    or stripped.startswith("switch ")
                    or stripped.startswith("catch ")
                    or stripped.startswith("new ")
                    or re.search(rf"\.\s*{re.escape(name)}\s*\(", stripped)
                ):
                    continue

                # a statement (ends with ';') or an assignment ('=' before the call
                # parens) is a call/usage, not a declaration -- skip it. A legitimate
                # class-field arrow is allowed through (it also ends with ';').
                if not is_field_arrow:
                    if stripped.endswith(";"):
                        continue
                    paren = stripped.find("(")
                    before_paren = stripped if paren == -1 else stripped[:paren]
                    if "=" in before_paren:
                        continue

                if is_field_arrow or any(p.search(line) for p in patterns):
                    used.add(i)
                    actions.append((i, doc))
                    break

        for i, doc in sorted(actions, key=lambda a: a[0], reverse=True):
            if self._has_doc(lines, i):
                lines = self._replace_doc(lines, i, doc)
            else:
                lines.insert(i, self._format(doc, lines[i]))

        return lines

    @staticmethod
    def _scan_comment_state(line, in_block, quote):
        """Advance the (in_block, quote) lexer state across one line.
        Honours block comments `/* */`, `//` line comments, and string/template literals
        (with backslash escapes). `quote` is threaded so a multi-line template literal
        keeps its state and a `/*` inside it never opens a comment."""
        i, n = 0, len(line)
        while i < n:
            pair = line[i : i + 2]
            if in_block:
                if pair == "*/":
                    in_block = False
                    i += 2
                    continue
                i += 1
                continue
            if quote:
                if line[i] == "\\":
                    i += 2
                    continue
                if line[i] == quote:
                    quote = None
                i += 1
                continue
            if line[i] in "\"'`":
                quote = line[i]
                i += 1
                continue
            if pair == "//":
                break
            if pair == "/*":
                in_block = True
                i += 2
                continue
            i += 1

        # only a template literal (backtick) may legally span lines; a dangling ' or "
        # at end of line is a mis-lexed regex/division, not a real multi-line string, so
        # drop it instead of leaking the quote state onto the next line.
        if quote is not None and quote != "`":
            quote = None
        return in_block, quote

    @staticmethod
    def _comment_lines(lines):
        """Indices of lines whose start sits inside a block comment or a (multi-line)
        string/template literal, or that are whole-line `//` comments, so declaration
        patterns are never matched against comment or string text. A line that merely
        opens a comment/string after real code is NOT marked (its code may be a
        declaration); only lines that begin inside one are skipped."""
        marked = set()
        in_block = False
        quote = None
        for i, line in enumerate(lines):
            if in_block or quote is not None:
                marked.add(i)
            elif line.strip().startswith("//"):
                marked.add(i)
            in_block, quote = TSJSAugmentor._scan_comment_state(line, in_block, quote)

        return marked

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

        # strip a Markdown code fence if the model wrapped its answer in one
        fence = re.search(r"```[a-zA-Z]*\n([\s\S]+?)\n```", clean)
        if fence:
            clean = fence.group(1).strip()

        # if the model emitted a full /** ... */ block, keep only what's inside it
        # (drop anything before "/**" and after the closing "*/", e.g. a trailing fence).
        # Use the LAST "*/" as the close: a trailing fence contains none, while any "*/"
        # the model wrote inside the body stays in the slice and is escaped below.
        start = clean.find("/**")
        if start != -1:
            end = clean.rfind("*/")
            clean = (clean[start + 3 : end] if end > start + 2 else clean[start + 3 :]).strip()

        # drop any residual line that is nothing but a code fence (``` or ```lang)
        clean = "\n".join(l for l in clean.splitlines() if not re.match(r"^```[a-zA-Z]*$", l.strip()))

        # remove leading *
        clean_lines = []

        for l in clean.splitlines():
            l = re.sub(r"^\s*\*\s?", "", l.rstrip())
            clean_lines.append(l)

        clean = "\n".join(clean_lines)
        clean = clean.replace("*/", "* /")

        body = "\n".join(indent + " * " + l if l.strip() else indent + " *" for l in clean.split("\n"))

        return f"{indent}/**\n" f"{body}\n" f"{indent} */\n"
