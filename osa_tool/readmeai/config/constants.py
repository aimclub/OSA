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

    ITMO_LOGO = (
        "https://raw.githubusercontent.com/aimclub/open-source-ops/7de1e1321389ec177f236d0a5f41f876811a912a/badges/ITMO_badge.svg"
    )


class LLMService(str, enum.Enum):
    """
    LLM API service providers.
    """

    OLLAMA = "llama"
    OPENAI = "openai"


class ServiceAuthKeys(str, enum.Enum):
    """
    Environment variable names associated with a LLM API key.
    """

    OPENAI_API_KEY = "OPENAI_API_KEY"
    VSE_GPT_KEY = "VSE_GPT_KEY"
