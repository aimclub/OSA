from abc import ABC, abstractmethod


class BaseAugmentor(ABC):

    @abstractmethod
    def augment(self, file: str, source_code: str, docstrings: dict) -> dict[str, str]:
        pass