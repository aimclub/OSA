from importlib import metadata
import click
from pydantic import ValidationError

from osa_tool.docs_generator.repoagent.runner import Runner
from osa_tool.docs_generator.repoagent.settings import SettingsManager
from osa_tool.utils import logger

try:
    version_number = metadata.version('repoagent')
except metadata.PackageNotFoundError:
    version_number = '0.0.0'


def handle_setting_error(e: ValidationError):
    """Handles and displays configuration errors from a ValidationError.

This method iterates over the errors in a ValidationError, formats them into user-friendly messages, and prints them to the console. If any required field is missing, it instructs the user to set the corresponding environment variable. After displaying all errors, it raises a ClickException to terminate the program.

Args:
    e (ValidationError): The ValidationError object containing the configuration errors.

Returns:
    None: This method does not return any value.

Raises:
    click.ClickException: If there are configuration errors, this exception is raised to terminate the program.

Note:
    This method is used to handle and display errors during the initialization of settings in the `run`, `run_outside_cli`, and `diff` methods. It ensures that the user is informed about any missing or incorrect configuration settings, helping to maintain the integrity and functionality of the documentation generation process."""
    for error in e.errors():
        field = error['loc'][-1]
        if error['type'] == 'missing':
            message = click.style(f'Missing required field `{field}`. Please set the `{field}` environment variable.',
                                  fg='yellow')
        else:
            message = click.style(error['msg'], fg='yellow')
        click.echo(message, err=True, color=True)
    raise click.ClickException(click.style('Program terminated due to configuration errors.', fg='red', bold=True))


def run_outside_cli(model, temperature, request_timeout, base_url, target_repo_path, hierarchy_path, markdown_docs_path,
                    ignore_list, language, max_thread_count, log_level, print_hierarchy,
                    parse_references=True,
                    secondary_docstring_generation=True):
    """Runs the documentation generation process outside of the command-line interface (CLI).

This method initializes the project settings, sets the logger level, and runs the documentation generation process. If the `print_hierarchy` flag is set, it prints the hierarchical structure of the documentation items.

Args:
    model (str): The OpenAI model to use for chat completion.
    temperature (float): The sampling temperature for the model.
    request_timeout (int): The timeout for API requests in seconds.
    base_url (str): The base URL for the OpenAI API.
    target_repo_path (Path): The path to the target repository.
    hierarchy_path (str): The name of the hierarchy directory.
    markdown_docs_path (str): The name of the markdown documents directory.
    ignore_list (str): A comma-separated list of files or directories to ignore.
    language (str): The language to use. Must be a valid ISO 639 code or language name.
    max_thread_count (int): The maximum number of threads to use.
    log_level (str): The log level for the application. Must be one of 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
    print_hierarchy (bool): Whether to print the hierarchical structure of the documentation items.

Returns:
    None

Raises:
    ValidationError: If the provided settings are invalid.
    ValueError: If the log level input is invalid. The input must be one of the valid log levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
    ValueError: If the language input is invalid. The input must be a valid ISO 639 code or language name.

Note:
    - The method uses the `SettingsManager` to initialize project settings.
    - It uses the `set_logger_level_from_config` function to set the logger level.
    - It uses the `Runner` class to manage and generate the documentation.
    - If `print_hierarchy` is set, it prints the hierarchical structure of the documentation items using the `print_recursive` method."""
    try:
        setting = SettingsManager.initialize_with_params(target_repo=target_repo_path, hierarchy_name=hierarchy_path,
                                                         markdown_docs_name=markdown_docs_path,
                                                         ignore_list=[item.strip() for item in ignore_list.split(',') if
                                                                      item], language=language, log_level=log_level,
                                                         model=model, temperature=temperature,
                                                         request_timeout=request_timeout, openai_base_url=base_url,
                                                         max_thread_count=max_thread_count,
                                                         parse_references=parse_references,
                                                         secondary_docstring_generation=secondary_docstring_generation)
    except ValidationError as e:
        handle_setting_error(e)
        return
    runner = Runner()
    runner.run()
    logger.info('Documentation task completed.')
    if print_hierarchy:
        runner.meta_info.target_repo_hierarchical_tree.print_recursive()
        logger.info('Hierarchy printed.')
