from abc import ABC, abstractmethod


class LanguageAdapter(ABC):

    EXTENSIONS = ()

    @abstractmethod
    def build_parser(self):
        pass

    @abstractmethod
    def is_class(self, node) -> bool:
        pass

    @abstractmethod
    def is_function(self, node) -> bool:
        pass

    @abstractmethod
    def get_name(self, node, source_view):
        pass

    @abstractmethod
    def get_docstring(self, node, source_view):
        pass

    @abstractmethod
    def get_decorators(self, node, source_view):
        pass

    @abstractmethod
    def get_attributes(self, node, source_view):
        pass

    @abstractmethod
    def get_parameters(self, node, source_view):
        pass

    @abstractmethod
    def extract_imports(self, root, source_view, cwd):
        pass

    @abstractmethod
    def resolve_method_calls(self, node, source_view):
        pass