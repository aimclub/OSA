from enum import StrEnum
from typing import Optional
from iso639 import Language, LanguageNotFoundError
from pydantic import DirectoryPath, Field, HttpUrl, PositiveFloat, PositiveInt, SecretStr, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path


class LogLevel(StrEnum):
    """Enum representing the log levels for the application.

This enum is used to set the log level in the `ProjectSettings` class, which is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. The tool integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

Args:
    DEBUG (str): Log level for detailed debug information. Value is 'DEBUG'.
    INFO (str): Log level for general information. Value is 'INFO'.
    WARNING (str): Log level for warning messages. Value is 'WARNING'.
    ERROR (str): Log level for error messages. Value is 'ERROR'.
    CRITICAL (str): Log level for critical error messages. Value is 'CRITICAL'.

Note:
    This enum is essential for configuring the logging behavior of the tool, ensuring that relevant information is captured and displayed based on the set log level."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class ProjectSettings(BaseSettings):
    """ProjectSettings class for configuring project settings.

This class extends BaseSettings and provides configuration options for the project, including the target repository, hierarchy name, markdown documents name, ignore list, language, maximum thread count, log level, main idea, and whether to parse references.

Args:
    target_repo (DirectoryPath): The path to the target repository. Defaults to an empty string.
    hierarchy_name (str): The name of the hierarchy directory. Defaults to '.project_doc_record'.
    markdown_docs_name (str): The name of the markdown documents directory. Defaults to 'markdown_docs'.
    ignore_list (list[str]): A list of files or directories to ignore. Defaults to an empty list.
    language (str): The language to use. Defaults to 'English'.
    max_thread_count (PositiveInt): The maximum number of threads to use. Defaults to 4.
    log_level (LogLevel): The log level for the application. Defaults to LogLevel.INFO.
    main_idea (Optional[str]): The main idea of the project. Defaults to None.
    parse_references (bool): Whether to parse references. Defaults to True.

Raises:
    ValueError: If the language input is invalid. The input must be a valid ISO 639 code or language name.
    ValueError: If the log level input is invalid. The input must be one of the valid log levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.

Note:
    The `language` and `log_level` fields have custom validation methods to ensure they are set correctly.

    The project is a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories. The tool also includes a chat engine and a multi-task dispatch system to enhance user interaction and process management. Additionally, it provides utilities for handling .gitignore files and managing fake files for untracked and modified content. The primary purpose of this project is to streamline the documentation process for software repositories, ensuring that documentation is up-to-date, accurate, and reflects the current state of the codebase."""
    target_repo: DirectoryPath = ''
    hierarchy_name: str = '.project_doc_record'
    markdown_docs_name: str = 'markdown_docs'
    ignore_list: list[str] = []
    language: str = 'English'
    max_thread_count: PositiveInt = 4
    log_level: LogLevel = LogLevel.INFO
    main_idea: Optional[str] = None
    parse_references: bool = True
    secondary_docstring_generation: bool = True

    @field_validator('language')
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Validates a language code and returns the corresponding language name.

This method checks if the provided language code or name matches a valid ISO 639 code or language name. If a match is found, it returns the language name. If not, it raises a ValueError.

Args:
    v (str): The language code or name to validate.

Returns:
    str: The corresponding language name.

Raises:
    ValueError: If the input is not a valid ISO 639 code or language name.

Note:
    This method uses the `Language.match` method to find the language name."""
        try:
            language_name = Language.match(v).name
            return language_name
        except LanguageNotFoundError:
            raise ValueError('Invalid language input. Please enter a valid ISO 639 code or language name.')

    @field_validator('log_level', mode='before')
    @classmethod
    def set_log_level(cls, v: str) -> LogLevel:
        """Sets the log level for the project.

This method takes a string representing the log level, converts it to uppercase, and returns the corresponding LogLevel enum member. If the provided log level is not valid, it raises a ValueError. This functionality is crucial for configuring the verbosity of logs, which helps in debugging and monitoring the tool's operations.

Args:  
    v (str): The log level to set. This should be a string representing a valid log level.

Returns:  
    LogLevel: The LogLevel enum member corresponding to the provided log level.

Raises:  
    ValueError: If the provided log level is not a valid member of the LogLevel enum.

Note:  
    This method is part of the project settings management, ensuring that the tool's logging behavior can be easily adjusted to suit different development and operational needs."""
        if isinstance(v, str):
            v = v.upper()
        if v in LogLevel._value2member_map_:
            return LogLevel(v)
        raise ValueError(f'Invalid log level: {v}')


class ChatCompletionSettings(BaseSettings):
    """Settings for chat completion using the OpenAI API.

This class configures the settings required for generating chat completions using the OpenAI API. It is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, enhancing user interaction through a chat engine.

Args:
    model (str): The model to use for chat completion. Defaults to 'gpt-4o-mini'.
    temperature (PositiveFloat): The sampling temperature for the model. Defaults to 0.2.
    request_timeout (PositiveInt): The timeout for API requests in seconds. Defaults to 180.
    openai_base_url (str): The base URL for the OpenAI API. Defaults to 'https://api.openai.com/v1'.
    openai_api_key (SecretStr): The API key for OpenAI. This is a required field.

Returns:
    None

Raises:
    ValueError: If `openai_api_key` is not provided.

Note:
    The `openai_api_key` is excluded from the settings output for security reasons. The `openai_base_url` is converted to a string before validation."""
    model: str = 'gpt-4o-mini'
    temperature: PositiveFloat = 0.2
    request_timeout: PositiveInt = 180
    openai_base_url: str = 'https://api.openai.com/v1'
    openai_api_key: SecretStr = Field(..., exclude=True)

    @field_validator('openai_base_url', mode='before')
    @classmethod
    def convert_base_url_to_str(cls, openai_base_url: HttpUrl) -> str:
        """Converts an HTTP URL to a string.

This method takes an HTTP URL object and returns its string representation, which is useful for generating and managing documentation for a Git repository. It ensures that URLs used in the documentation are in a readable and usable format.

Args:
    openai_base_url (HttpUrl): The base URL to be converted to a string.

Returns:
    str: The string representation of the base URL.

Raises:
    None

Note:
    This method is part of the documentation generation and management tool, which automates the process of updating and maintaining high-quality documentation for software repositories."""
        return str(openai_base_url)


class Setting(BaseSettings):
    """Setting class for configuring project and chat completion settings.

This class extends BaseSettings and provides configuration options for the project and chat completion using the OpenAI API. It is designed to support the automation of documentation generation and management for a Git repository, integrating functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

Args:
    project (ProjectSettings): Configuration settings for the project. Defaults to an empty dictionary.
    chat_completion (ChatCompletionSettings): Configuration settings for chat completion. Defaults to an empty dictionary.

Note:
    The `project` and `chat_completion` fields are instances of `ProjectSettings` and `ChatCompletionSettings` respectively, which provide detailed configuration options for the project and chat completion settings. These settings are crucial for the tool's ability to automate documentation and enhance user interaction through a chat engine."""
    project: ProjectSettings = {}
    chat_completion: ChatCompletionSettings = {}


class SettingsManager:
    """SettingsManager class for managing and initializing project and chat completion settings.

This class provides methods to get and initialize settings for the project and chat completion using the OpenAI API. It is designed to streamline the documentation process for software repositories by automating the detection of changes, generation of summaries, and handling of file operations.

Args:
    _setting_instance (Optional[Setting]): The singleton instance of the Setting class. Defaults to None.

Returns:
    Setting: The singleton instance of the Setting class.

Raises:
    ValueError: If the provided parameters are invalid or incomplete.

Note:
    The `Setting` class extends `BaseSettings` and provides configuration options for the project and chat completion settings. The `ProjectSettings` and `ChatCompletionSettings` classes are used to configure detailed settings for the project and chat completion, respectively. This tool is particularly useful for large repositories where manual tracking and updating of documentation can be time-consuming and error-prone."""
    _setting_instance: Optional[Setting] = None

    @classmethod
    def get_setting(cls):
        """Retrieves the singleton instance of the `Setting` class.

This method ensures that only one instance of the `Setting` class is created and returned. If the instance does not exist, it is created and stored in the class variable `_setting_instance`.

Args:
    None

Returns:
    Setting: The singleton instance of the `Setting` class.

Raises:
    None

Note:
    The `Setting` class provides configuration options for the project, including settings for the chat completion using the OpenAI API and other project-specific configurations. This method is crucial for maintaining a consistent and centralized configuration management system within the project."""
        if cls._setting_instance is None:
            cls._setting_instance = Setting()
        return cls._setting_instance

    @classmethod
    def initialize_with_params(cls, target_repo: Path, markdown_docs_name: str, hierarchy_name: str,
                               ignore_list: list[str], language: str, max_thread_count: int, log_level: str, model: str,
                               temperature: float, request_timeout: int, openai_base_url: str,
                               parse_references: bool = True, secondary_docstring_generation: bool = True):
        """Initializes the settings with the provided parameters.

This method sets up the project and chat completion settings using the provided parameters. It creates instances of `ProjectSettings` and `ChatCompletionSettings` and assigns them to the `_setting_instance` class attribute.

Args:
    target_repo (Path): The path to the target repository.
    markdown_docs_name (str): The name of the markdown documents directory.
    hierarchy_name (str): The name of the hierarchy directory.
    ignore_list (list[str]): A list of files or directories to ignore.
    language (str): The language to use. Must be a valid ISO 639 code or language name.
    max_thread_count (int): The maximum number of threads to use.
    log_level (str): The log level for the application. Must be one of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
    model (str): The model to use for chat completion.
    temperature (float): The sampling temperature for the model.
    request_timeout (int): The timeout for API requests in seconds.
    openai_base_url (str): The base URL for the OpenAI API.
    parse_references (bool): Whether to parse references. Defaults to True.

Returns:
    None

Raises:
    ValueError: If the language input is invalid. The input must be a valid ISO 639 code or language name.
    ValueError: If the log level input is invalid. The input must be one of the valid log levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
    ValueError: If `openai_api_key` is not provided in `ChatCompletionSettings`.

Note:
    The `log_level` is converted to an instance of `LogLevel` before being used in `ProjectSettings`. The `openai_api_key` is a required field in `ChatCompletionSettings` and is excluded from the settings output for security reasons."""
        project_settings = ProjectSettings(target_repo=target_repo, hierarchy_name=hierarchy_name,
                                           markdown_docs_name=markdown_docs_name, ignore_list=ignore_list,
                                           language=language, max_thread_count=max_thread_count,
                                           log_level=LogLevel(log_level), parse_references=parse_references,
                                           secondary_docstring_generation=secondary_docstring_generation)
        chat_completion_settings = ChatCompletionSettings(model=model, temperature=temperature,
                                                          request_timeout=request_timeout,
                                                          openai_base_url=openai_base_url)
        cls._setting_instance = Setting(project=project_settings, chat_completion=chat_completion_settings)


if __name__ == '__main__':
    setting = SettingsManager.get_setting()
    print(setting.model_dump())
