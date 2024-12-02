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
    SKILLS = "skills"


class HeaderStyleOptions(str, enum.Enum):
    """
    Enum of supported 'Header' template styles for the README file.
    """

    CLASSIC = "classic"


class ImageOptions(str, enum.Enum):
    """
    Default image options for the project logo.
    """

    ITMO_LOGO = ""


class TocStyleOptions(str, enum.Enum):
    """
        Enum of supported 'Table of Contents' templates for the README file.
        """

    BULLET = "bullet"


class LLMService(str, enum.Enum):
    """
        LLM API service providers.
    """
    OLLAMA = "llama"
