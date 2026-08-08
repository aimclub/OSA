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
