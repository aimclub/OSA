from osa_tool.operations.codebase.docstring_generation.insert.python_augmentor import PythonAugmentor
from osa_tool.operations.codebase.docstring_generation.insert.ts_js_augmentor import TSJSAugmentor


class AugmentorFactory:

    @staticmethod
    def create(file_path: str):
        if file_path.endswith(".py"):
            return PythonAugmentor()

        if file_path.endswith((".ts", ".js")):
            return TSJSAugmentor()

        raise ValueError(f"Unsupported file type: {file_path}")
