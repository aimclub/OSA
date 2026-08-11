from osa_tool.operations.codebase.docstring_generation.insert.ts_js_augmentor import TSJSAugmentor


def _augment_function(doc, source):
    aug = TSJSAugmentor()
    meta = {"method_name": "multiply"}
    result = aug.augment("f.ts", source, {"functions": [(doc, meta)]})
    return result["f.ts"]


def test_format_strips_model_wrapper_and_trailing_fence():
    """Model wraps its JSDoc in /** */ and tacks a trailing markdown fence.

    The augmentor must keep only the inner content: no stray ' * /' (mangled
    close) and no ' * ``` ' fence line should leak into the emitted comment.
    """
    dirty = (
        "/**\n"
        " * Multiplies two numbers.\n"
        " *\n"
        " * @param {number} a The first number.\n"
        " * @param {number} b The second number.\n"
        " * @returns {number} The product.\n"
        " */\n"
        "```"
    )
    source = "export function multiply(a: number, b: number): number {\n  return a * b;\n}\n"

    out = _augment_function(dirty, source)

    assert "@param {number} a The first number." in out
    assert "@returns {number} The product." in out
    # no mangled close and no leaked fence
    assert "* /" not in out
    assert "```" not in out
    # exactly one opening and one closing JSDoc delimiter
    assert out.count("/**") == 1
    assert out.count("*/") == 1


def test_format_strips_full_markdown_fence():
    """Model wraps the whole answer in a ```javascript ... ``` fence."""
    dirty = (
        "```javascript\n"
        "/**\n"
        " * Multiplies two numbers.\n"
        " * @param {number} a first\n"
        " * @param {number} b second\n"
        " * @returns {number} product\n"
        " */\n"
        "```"
    )
    source = "export function multiply(a, b) {\n  return a * b;\n}\n"

    out = _augment_function(dirty, source)

    assert "@returns {number} product" in out
    assert "```" not in out
    assert "* /" not in out
    assert out.count("/**") == 1
    assert out.count("*/") == 1


def test_wrapper_body_containing_star_slash_is_preserved_not_truncated():
    """A /** ... */ wrapper whose body literally contains '*/' must not be cut short.

    The close is taken as the LAST '*/', so the '@returns' after an in-body '*/'
    survives, and the stray in-body '*/' is escaped so it cannot close early.
    """
    dirty = (
        "/**\n"
        " * Handles the */ token in a comment.\n"
        " * @param {string} s input\n"
        " * @returns {string} cleaned output\n"
        " */"
    )
    source = "export function multiply(s) {\n  return s;\n}\n"

    out = _augment_function(dirty, source)

    # content after the in-body '*/' is preserved (no truncation)
    assert "@returns {string} cleaned output" in out
    assert "Handles the" in out
    # still a single well-formed block; the in-body '*/' was escaped, not left to close early
    assert out.count("/**") == 1
    assert out.count("*/") == 1


def test_star_slash_in_plain_body_is_escaped():
    """A plain (unwrapped) body containing '*/' must be escaped to '* /'."""
    doc = "Documents the */ terminator.\n@returns {void} nothing"
    source = "export function multiply() {}\n"

    out = _augment_function(doc, source)

    assert "@returns {void} nothing" in out
    # exactly one real closing delimiter (the block's own); the body '*/' is escaped
    assert out.count("*/") == 1
    assert "* /" in out


def test_format_plain_text_unchanged_behaviour():
    """A clean, unwrapped docstring is still emitted as a valid JSDoc block."""
    doc = "Multiplies two numbers.\n@param {number} a first\n@returns {number} product"
    source = "export function multiply(a, b) {\n  return a * b;\n}\n"

    out = _augment_function(doc, source)

    assert out.startswith("/**")
    assert "@param {number} a first" in out
    assert "@returns {number} product" in out
    assert "```" not in out
    assert out.count("/**") == 1
    assert out.count("*/") == 1


# --- robustness fixes: class/method injection edge cases ---------------------


def _line_above(out, decl_substring):
    """Return the stripped line directly above the first line containing decl_substring."""
    lines = out.splitlines()
    for i, l in enumerate(lines):
        if decl_substring in l:
            return lines[i - 1].strip() if i > 0 else ""
    return None


def test_inject_export_default_class():
    """`export default class X` must receive a class-level JSDoc (regex #1)."""
    aug = TSJSAugmentor()
    src = "export default class Queue {\n\tclear() {}\n}\n"
    out = aug.augment("f.ts", src, {"classes": [("A FIFO queue.", "Queue")]})["f.ts"]

    assert "A FIFO queue." in out
    assert _line_above(out, "export default class Queue") == "*/"


def test_inject_generator_method():
    """Generator methods (`* gen()`) must be matched and documented (#4)."""
    aug = TSJSAugmentor()
    src = "class Q {\n\t* drain() {\n\t\tyield 1;\n\t}\n}\n"
    out = aug.augment("f.ts", src, {"methods": [("Drains the queue.", {"method_name": "drain"})]})["f.ts"]

    assert "Drains the queue." in out
    assert _line_above(out, "* drain()") == "*/"


def test_inject_two_same_named_methods_both_documented():
    """Two methods with the same name must each get their own doc, in order (#2)."""
    aug = TSJSAugmentor()
    src = (
        "class Node {\n\tconstructor(value) {\n\t\tthis.value = value;\n\t}\n}\n"
        "class Queue {\n\tconstructor() {\n\t\tthis.clear();\n\t}\n}\n"
    )
    docs = {
        "methods": [
            ("Node constructor.", {"method_name": "constructor"}),
            ("Queue constructor.", {"method_name": "constructor"}),
        ]
    }
    out = aug.augment("f.ts", src, docs)["f.ts"]

    assert out.count("constructor(") == 2
    assert "Node constructor." in out
    assert "Queue constructor." in out
    # both declarations carry a doc block directly above them
    lines = out.splitlines()
    ctor_idxs = [i for i, l in enumerate(lines) if "constructor(" in l]
    assert len(ctor_idxs) == 2
    for idx in ctor_idxs:
        assert lines[idx - 1].strip() == "*/"
    # order preserved: first constructor -> first doc
    assert out.index("Node constructor.") < out.index("Queue constructor.")


def test_inject_method_with_default_param_value():
    """A method whose signature line contains `=` (default value) must be documented (#3)."""
    aug = TSJSAugmentor()
    src = "class C {\n\tscale(x, factor = 2) {\n\t\treturn x * factor;\n\t}\n}\n"
    out = aug.augment("f.ts", src, {"methods": [("Scales a value.", {"method_name": "scale"})]})["f.ts"]

    assert "Scales a value." in out
    assert _line_above(out, "scale(x, factor = 2)") == "*/"


def test_assignment_is_not_mistaken_for_method():
    """A local assignment must NOT be documented as a method (guard still holds)."""
    aug = TSJSAugmentor()
    src = "class C {\n\trun() {\n\t\tconst compute = helper(1);\n\t\treturn compute;\n\t}\n}\n"
    out = aug.augment("f.ts", src, {"methods": [("Computes.", {"method_name": "compute"})]})["f.ts"]

    assert "Computes." not in out


def test_inject_class_field_arrow_method():
    """A class-field arrow (`name = (...) => ...`) must be documented (#5, injection)."""
    aug = TSJSAugmentor()
    src = "class C {\n\tgreet = (name) => 'hi ' + name;\n}\n"
    out = aug.augment("f.ts", src, {"methods": [("Greets by name.", {"method_name": "greet"})]})["f.ts"]

    assert "Greets by name." in out
    assert _line_above(out, "greet = (name) =>") == "*/"


def test_bare_call_with_operator_not_documented():
    """A bare call statement whose args contain `===`/`>=`/etc must NOT be mistaken
    for a method declaration; the real same-named method gets the doc instead (#3 guard)."""
    aug = TSJSAugmentor()
    src = (
        "class S {\n"
        "\tboot() {\n"
        "\t\tassert(ready === true);\n"
        "\t}\n"
        "\tassert(cond) {\n"
        "\t\treturn cond;\n"
        "\t}\n"
        "}\n"
    )
    docs = {
        "methods": [
            ("Boots the service.", {"method_name": "boot"}),
            ("Asserts a condition.", {"method_name": "assert"}),
        ]
    }
    out = aug.augment("f.ts", src, docs)["f.ts"]
    lines = out.splitlines()

    # the call statement must NOT receive a doc
    call_idx = next(i for i, l in enumerate(lines) if "assert(ready === true)" in l)
    assert lines[call_idx - 1].strip() != "*/"
    # the real declaration does
    decl_idx = next(i for i, l in enumerate(lines) if "assert(cond)" in l)
    assert lines[decl_idx - 1].strip() == "*/"
    assert "Asserts a condition." in out


def test_same_named_methods_mapped_by_source_order():
    """When entries arrive out of source order (dependency order), each doc must land
    on the method at its own start_line, not get swapped (regression for the swap bug)."""
    aug = TSJSAugmentor()
    src = (
        "class A {\n\tadd(item, priority = 0) {\n\t\treturn item;\n\t}\n}\n"
        "class B {\n\tadd(key, value) {\n\t\treturn key;\n\t}\n}\n"
    )
    # entries deliberately reversed (B.add first) to mimic dependency-order output
    docs = {
        "methods": [
            ("Doc for B add.", {"method_name": "add", "start_line": 7}),
            ("Doc for A add.", {"method_name": "add", "start_line": 2}),
        ]
    }
    out = aug.augment("f.ts", src, docs)["f.ts"]
    lines = out.splitlines()

    a_idx = next(i for i, l in enumerate(lines) if "add(item, priority = 0)" in l)
    b_idx = next(i for i, l in enumerate(lines) if "add(key, value)" in l)
    a_block = "\n".join(lines[max(0, a_idx - 4) : a_idx])
    b_block = "\n".join(lines[max(0, b_idx - 4) : b_idx])

    assert "Doc for A add." in a_block
    assert "Doc for B add." in b_block


def test_comment_body_not_matched_as_declaration():
    """A JSDoc body line like ` * save(entity) ...` must not be matched as the method
    declaration (the generator `*` pattern must not hit comment lines and corrupt the
    file). Regenerating updates the real method's doc instead."""
    aug = TSJSAugmentor()
    src = (
        "class Repo {\n"
        "\t/**\n"
        "\t * save(entity) persists the record.\n"
        "\t */\n"
        "\tsave(entity) {\n"
        "\t\treturn entity;\n"
        "\t}\n"
        "}\n"
    )
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Persists the entity.", {"method_name": "save", "start_line": 5})]},
    )["f.ts"]

    assert "Persists the entity." in out
    # exactly one JSDoc block (the method's, replaced) -> no nested/corrupted /**
    assert out.count("/**") == 1
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "save(entity) {" in l)
    assert lines[decl - 1].strip() == "*/"


def test_block_comment_line_not_matched_as_declaration():
    """A plain block-comment line starting with a method name must not be matched."""
    aug = TSJSAugmentor()
    src = (
        "class Repo {\n"
        "\t/*\n"
        "\tload(id) is deprecated, use fetch instead.\n"
        "\t*/\n"
        "\tload(id) {\n"
        "\t\treturn id;\n"
        "\t}\n"
        "}\n"
    )
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Loads by id.", {"method_name": "load", "start_line": 5})]},
    )["f.ts"]

    assert "Loads by id." in out
    # the doc must land above the real declaration, not inside the block comment
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "load(id) {" in l)
    assert lines[decl - 1].strip() == "*/"
    # the deprecated block-comment text is untouched (still present, not wrapped in /**)
    assert "load(id) is deprecated" in out


def test_method_with_inline_block_comment_still_documented():
    """A method whose declaration line has an inline `/* */` comment must still be
    documented (single-line block comments are not treated as comment lines)."""
    aug = TSJSAugmentor()
    src = "class C {\n\tparse(url) /* TODO */ {\n\t\treturn url;\n\t}\n}\n"
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Parses a URL.", {"method_name": "parse", "start_line": 2})]},
    )["f.ts"]

    assert "Parses a URL." in out
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "parse(url)" in l)
    assert lines[decl - 1].strip() == "*/"


def test_string_literal_slash_star_does_not_suppress_methods():
    """A `/*` inside a string literal must NOT open a phantom comment block that
    suppresses documentation of later methods (literal-aware comment scan)."""
    aug = TSJSAugmentor()
    src = "class Repo {\n" '\tglob = "src/*";\n' "\tsave(entity) {\n\t\treturn entity;\n\t}\n" "}\n"
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Saves the entity.", {"method_name": "save", "start_line": 3})]},
    )["f.ts"]

    assert "Saves the entity." in out
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "save(entity) {" in l)
    assert lines[decl - 1].strip() == "*/"


def test_declaration_opening_trailing_block_comment_still_documented():
    """A declaration line that also opens a multi-line comment after the code must still
    be documented (the code part is a real declaration)."""
    aug = TSJSAugmentor()
    src = "class I {\n" "\tsave(entity) { /* note:\n" "\t   multi-line */\n" "\t\treturn entity;\n" "\t}\n" "}\n"
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Saves it.", {"method_name": "save", "start_line": 2})]},
    )["f.ts"]

    assert "Saves it." in out
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "save(entity)" in l and "*" != l.strip()[:1])
    assert lines[decl - 1].strip() == "*/"


def test_multiline_template_literal_does_not_suppress_methods():
    """A multi-line template literal containing '/*' must not open a phantom comment
    block (quote state is threaded across lines), so later methods stay documented."""
    aug = TSJSAugmentor()
    src = (
        "class Q {\n"
        "\tsql = `\n"
        "\t\tSELECT /* unclosed marker\n"
        "\t`;\n"
        "\tsave(entity) {\n\t\treturn entity;\n\t}\n"
        "}\n"
    )
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Saves it.", {"method_name": "save", "start_line": 5})]},
    )["f.ts"]

    assert "Saves it." in out
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "save(entity) {" in l)
    assert lines[decl - 1].strip() == "*/"


def test_regex_with_apostrophe_does_not_suppress_methods():
    """A regex literal containing a lone quote char (e.g. /O'Brien/) must not leave a
    dangling string state that suppresses documentation of later methods."""
    aug = TSJSAugmentor()
    src = "class M {\n" "\tre = /O'Brien/;\n" "\tsave(entity) {\n\t\treturn entity;\n\t}\n" "}\n"
    out = aug.augment(
        "f.ts",
        src,
        {"methods": [("Saves it.", {"method_name": "save", "start_line": 3})]},
    )["f.ts"]

    assert "Saves it." in out
    lines = out.splitlines()
    decl = next(i for i, l in enumerate(lines) if "save(entity) {" in l)
    assert lines[decl - 1].strip() == "*/"
