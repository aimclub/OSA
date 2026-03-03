"""Factory for creating language-specific analyzers."""

from typing import Dict, List, Optional, Set, Type

from osa_tool.organization.core.analyzers.base import BaseAnalyzer
from osa_tool.organization.core.analyzers.python import PythonImportAnalyzer
from osa_tool.organization.core.analyzers.java import JavaImportAnalyzer
from osa_tool.organization.core.analyzers.javascript import JavaScriptImportAnalyzer
from osa_tool.organization.core.analyzers.cpp import CppImportAnalyzer
from osa_tool.organization.core.analyzers.go import GoPackagesAnalyzer
from osa_tool.organization.core.analyzers.rust import RustImportAnalyzer
from osa_tool.organization.core.analyzers.latex import LatexImportAnalyzer
from osa_tool.organization.core.analyzers.csharp import CSharpImportAnalyzer
from osa_tool.organization.core.analyzers.swift import SwiftImportAnalyzer
from osa_tool.organization.core.analyzers.ruby import RubyImportAnalyzer
from osa_tool.organization.core.analyzers.kotlin import KotlinImportAnalyzer
from osa_tool.organization.core.analyzers.generic import GenericReferenceAnalyzer


class AnalyzerFactory:
    """
    Factory to create language‑specific analyzers and the generic reference analyzer.

    Provides a centralized registry and creation mechanism for all analyzer types.
    Supports dynamic registration of new analyzers.
    """

    _analyzers: Dict[str, Type[BaseAnalyzer]] = {
        "python": PythonImportAnalyzer,
        "java": JavaImportAnalyzer,
        "javascript": JavaScriptImportAnalyzer,
        "cpp": CppImportAnalyzer,
        "go": GoPackagesAnalyzer,
        "rust": RustImportAnalyzer,
        "latex": LatexImportAnalyzer,
        "csharp": CSharpImportAnalyzer,
        "swift": SwiftImportAnalyzer,
        "ruby": RubyImportAnalyzer,
        "kotlin": KotlinImportAnalyzer,
    }

    @classmethod
    def create_analyzer(cls, language: str, base_path: str) -> Optional[BaseAnalyzer]:
        """
        Instantiate an analyzer for the given language.

        Args:
            language: Language identifier (e.g., 'python', 'java')
            base_path: Root directory path for analysis

        Returns:
            Optional[BaseAnalyzer]: Analyzer instance or None if language not supported
        """
        analyzer_class = cls._analyzers.get(language.lower())
        if analyzer_class:
            return analyzer_class(base_path)
        return None

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """
        Get list of supported programming languages.

        Returns:
            List[str]: List of language identifiers
        """
        return list(cls._analyzers.keys())

    @classmethod
    def register_analyzer(cls, language: str, analyzer_class: Type[BaseAnalyzer]) -> None:
        """
        Register a new analyzer for a language.

        Args:
            language: Language identifier
            analyzer_class: Analyzer class to register
        """
        cls._analyzers[language.lower()] = analyzer_class

    @classmethod
    def create_generic_analyzer(cls, base_path: str, excluded_extensions: Set[str]) -> GenericReferenceAnalyzer:
        """
        Create a generic reference analyzer.

        Args:
            base_path: Root directory path for analysis
            excluded_extensions: Set of file extensions to exclude

        Returns:
            GenericReferenceAnalyzer: Generic analyzer instance
        """
        return GenericReferenceAnalyzer(base_path, excluded_extensions)
