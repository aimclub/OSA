"""LaTeX-specific import analyzer for inclusions and references."""

import re
from pathlib import Path
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class LatexImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for LaTeX files: extracts \\input, \\include, \\usepackage, \\bibliography.

    Handles LaTeX, BibTeX, and related files, extracting and updating
    various types of LaTeX inclusions and references.
    """

    def __init__(self, base_path: str):
        """
        Initialize the LaTeX import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".tex", ".bib", ".sty", ".cls"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract all types of LaTeX inclusions and references.

        Handles \\input, \\include, \\usepackage, \\RequirePackage, and \\bibliography.

        Args:
            file_path: Path to the LaTeX file relative to base_path

        Returns:
            Set[str]: Set of referenced file/package names
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            input_pattern = r"\\input\{([^}]+)\}"
            for match in re.findall(input_pattern, content):
                imports.add(match.replace(".tex", ""))
            include_pattern = r"\\include\{([^}]+)\}"
            for match in re.findall(include_pattern, content):
                imports.add(match.replace(".tex", ""))
            bib_pattern = r"\\bibliography\{([^}]+)\}"
            for match in re.findall(bib_pattern, content):
                for bib in match.split(","):
                    imports.add(bib.strip().replace(".bib", ""))
            package_pattern = r"\\(?:usepackage|RequirePackage)(?:\[[^]]*\])?\{([^}]+)\}"
            for match in re.findall(package_pattern, content):
                for pkg in match.split(","):
                    pkg = pkg.strip()
                    if pkg:
                        imports.add(pkg)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a LaTeX-related file.

        Args:
            file_path: Path to the file relative to base_path

        Returns:
            str: Import key (path without extension)
        """
        path = Path(file_path)
        if path.suffix in (".tex", ".bib"):
            return str(path.with_suffix(""))
        elif path.suffix in (".sty", ".cls"):
            return str(path.with_suffix(""))
        else:
            return file_path

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update all types of LaTeX inclusions and references.

        Updates \\input, \\include, \\usepackage, \\RequirePackage, and \\bibliography.

        Args:
            file_path: Path to the LaTeX file relative to base_path
            old_import: Original reference to replace
            new_import: New reference to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            old_input = old_import.replace(".tex", "")
            new_input = new_import.replace(".tex", "")
            content = re.sub(rf"\\input\{{{re.escape(old_input)}(\.tex)?\}}", f"\\input{{{new_input}}}", content)
            content = re.sub(rf"\\include\{{{re.escape(old_input)}(\.tex)?\}}", f"\\include{{{new_input}}}", content)

            def replace_bib(match):
                """
                Replace bibliography references in a \\bibliography command.

                Args:
                    match: Regex match object containing the bibliography command

                Returns:
                    str: Updated bibliography command
                """
                files = match.group(1).split(",")
                updated = []
                for f in files:
                    f = f.strip()
                    if f.replace(".bib", "") == old_input:
                        updated.append(new_input + (".bib" if f.endswith(".bib") else ""))
                    else:
                        updated.append(f)
                return f'\\bibliography{{{",".join(updated)}}}'

            bib_pattern = r"\\bibliography\{([^}]+)\}"
            content = re.sub(bib_pattern, replace_bib, content)

            def replace_package(match):
                """
                Replace package names in \\usepackage or \\RequirePackage commands.

                Args:
                    match: Regex match object containing the package command

                Returns:
                    str: Updated package command or original if no replacement needed
                """
                full_cmd = match.group(0)
                options = match.group(1) or ""
                packages_body = match.group(2)
                packages = [p.strip() for p in packages_body.split(",")]
                changed = False
                new_packages = []
                for p in packages:
                    if p == old_import:
                        new_packages.append(new_import)
                        changed = True
                    else:
                        new_packages.append(p)
                if changed:
                    new_body = ",".join(new_packages)
                    if options:
                        return f"\\usepackage[{options}]{{{new_body}}}"
                    else:
                        return f"\\usepackage{{{new_body}}}"
                else:
                    return full_cmd

            package_pattern = r"\\(usepackage|RequirePackage)(?:\[([^]]*)\])?\{([^}]+)\}"
            content = re.sub(package_pattern, replace_package, content)
            return content
        except Exception:
            return None
