"""
Enum classes that store information settings for the LLM
API service providers, badge styles, and image options.
"""

import enum


class BadgeStyleOptions(str, enum.Enum):
    """
    Badge icon styles for the project README.
    """

    DEFAULT = "default"


class HeaderStyleOptions(str, enum.Enum):
    """
    Enum of supported 'Header' template styles for the README file.
    """

    CLASSIC = "classic"


class ImageOptions(str, enum.Enum):
    """
    Default image options for the project logo.
    """

    ITMO_LOGO = "https://itmo.ru/file/pages/213/logo_na_plashke_russkiy_belyy.png"


class LLMService(str, enum.Enum):
    """
        LLM API service providers.
    """
    OLLAMA = "llama"
