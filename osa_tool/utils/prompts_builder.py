import os

import tomli

from osa_tool.utils.utils import osa_project_root


class PromptBuilderError(Exception):
    """
    Base exception for PromptBuilder errors.
    """



class PromptLoadError(PromptBuilderError):
    """
    Raised when loading prompts from a file fails.
    """



class PromptFormatError(PromptBuilderError):
    """
    Raised when formatting the prompt with arguments fails.
    """



class PromptBuilder:
    """
    A class for building and rendering prompt templates.
    
        Methods:
        - render: Renders the template using Python's format() method, with optional safe mode.
    
        Attributes:
        - template: The string template used for rendering prompts.
        - safe: A boolean flag indicating whether to use safe rendering mode.
    """

    @staticmethod
    def render(template: str, safe: bool = False, **kwargs) -> str:
        """
        Render a template string using Python's format(), unless safe=True.
        
        If safe is True, the template is returned unchanged without formatting.
        Otherwise, the template is formatted with the provided keyword arguments.
        This is useful for bypassing formatting when the template contains curly braces
        that should not be interpreted as placeholders.
        
        Args:
            template: The string template containing placeholders in curly braces.
            safe: If True, skip formatting and return the template as-is.
            **kwargs: Keyword arguments to substitute into the template placeholders.
        
        Returns:
            The formatted string, or the original template if safe=True.
        
        Raises:
            PromptBuilderError: If a placeholder key is missing from kwargs, or if any
                other error occurs during formatting.
        """
        try:
            if safe:
                return template
            return template.format(**kwargs)
        except KeyError as e:
            missing = e.args[0]
            raise PromptBuilderError(f"Missing argument for prompt rendering: '{missing}'")
        except Exception as e:
            raise PromptBuilderError(f"Failed to render prompt: {e}")


class PromptLoader:
    """
    Loads and manages all prompt configuration files from the designated prompts directory.
    
        Allows accessing prompts using keys like:
            "readme.preanalysis"
            "readme_article.file_summary"
    """


    def __init__(self):
        """
        Initializes the PromptLoader instance.
        
        This constructor sets up the prompt loader by determining the prompts directory,
        initializing an empty cache for prompt data, and loading all TOML prompt files
        into memory. Loading all prompts at startup avoids repeated disk I/O during operation,
        improving performance and ensuring prompt definitions are readily available.
        
        Class Fields:
            prompts_dir (str): The absolute path to the directory containing TOML prompt
                files, derived from the osa_tool project root.
            cache (dict[str, dict[str, str]]): A dictionary cache for storing loaded
                prompt data, where keys are prompt identifiers (filenames without the .toml extension)
                and values are the corresponding prompt configurations from the `[prompts]` section.
        
        Raises:
            PromptLoadError: If the prompts directory is not found, a TOML file cannot be parsed,
                             or a file does not contain a required `[prompts]` section.
        """
        self.prompts_dir = os.path.join(osa_project_root(), "config", "prompts")
        self.cache: dict[str, dict[str, str]] = {}
        self._load_all()

    def _load_all(self):
        """
        Load all TOML prompt files from the prompts directory into an in-memory cache.
        
        This method scans the configured prompts directory for files with a `.toml` extension.
        Each file's content is parsed, and the data under the `[prompts]` section is stored
        in the internal cache, keyed by the filename without the extension. If the directory
        does not exist or any file fails to parse or lacks the required section, a PromptLoadError
        is raised.
        
        Why: Prompt files are loaded once at initialization to avoid repeated disk I/O during
        operation, improving performance and ensuring prompt definitions are readily available.
        
        Args:
            self: The PromptLoader instance.
        
        Raises:
            PromptLoadError: If the prompts directory is not found, a TOML file cannot be parsed,
                             or a file does not contain a `[prompts]` section.
        """
        if not os.path.exists(self.prompts_dir):
            raise PromptLoadError(f"Prompts directory not found: {self.prompts_dir}")

        for filename in os.listdir(self.prompts_dir):
            if not filename.endswith(".toml"):
                continue

            path = os.path.join(self.prompts_dir, filename)
            section_name = filename[:-5]  # strip ".toml"

            try:
                with open(path, "rb") as f:
                    data = tomli.load(f)
            except Exception as e:
                raise PromptLoadError(f"Failed to parse {filename}: {e}") from e

            if "prompts" not in data:
                raise PromptLoadError(f"No [prompts] section in {filename}")

            self.cache[section_name] = data["prompts"]

    def get(self, key: str) -> str:
        """
        Get a prompt by global key: "section.prompt_name".
        
        The key must follow a dot-separated format where the first part is the section name and the second part is the prompt name within that section. This structure organizes prompts into logical groups for easier management and retrieval.
        
        Args:
            key: The dot-separated identifier for the prompt (e.g., "readme.preanalysis").
        
        Returns:
            The prompt string associated with the given key.
        
        Raises:
            PromptLoadError: If the key format is invalid (missing a dot), or if the specified section or prompt name does not exist in the loaded prompts.
        
        Example:
            get("readme.preanalysis")
            get("article.main_prompt")
        """
        if "." not in key:
            raise PromptLoadError(
                f"Invalid prompt key '{key}'. Expected format: section.name (e.g. 'readme.preanalysis')"
            )

        section, name = key.split(".", 1)

        try:
            return self.cache[section][name]
        except KeyError:
            raise PromptLoadError(f"Prompt '{key}' not found in loaded prompts")
