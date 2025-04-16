from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.readmegen.context.files_contents import FileContext
from osa_tool.utils import extract_readme_content, logger


def get_prompt_preanalysis(prompt: str, tree: str, base_path: str) -> str:
    """
    Builds a prompt by formatting the preanalysis template with the repository
    tree and README content.

    Args:
        prompt: The prompt template containing placeholders for formatting.
        tree: A string representation of the repository's file structure.
        base_path: The base local path to the cloned repository.

    Returns:
        str: The formatted prompt string to be sent to the model.
    """
    try:
        formatted_prompt = prompt.format(
            repository_tree=tree,
            reamde_content=extract_readme_content(base_path)
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build preanalysis prompt: {e}")
        raise


def get_prompt_core_features(
        prompt: str,
        metadata: RepositoryMetadata,
        base_path: str,
        key_files: list[FileContext]
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            metadata=metadata,
            readme_content=extract_readme_content(base_path),
            key_files_content=serialize_file_contexts(key_files)
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build core features prompt: {e}")
        raise


def get_prompt_overview(
        prompt: str,
        metadata: RepositoryMetadata,
        base_path: str,
        core_features: str
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            description=metadata.description,
            readme_content=extract_readme_content(base_path),
            core_features=core_features
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build overview prompt: {e}")
        raise


def get_getting_started_prompt(
        prompt: str,
        metadata: RepositoryMetadata,
        base_path: str,
        examples_files: list[FileContext]
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            readme_content=extract_readme_content(base_path),
            examples_files_content=serialize_file_contexts(examples_files)
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build getting started prompt: {e}")
        raise


def get_files_summary_prompt(
        prompt: str,
        files_content: list[FileContext]
) -> str:
    try:
        formatted_prompt = prompt.format(
            files_content=serialize_file_contexts(files_content)
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build files summary prompt: {e}")
        raise


def get_pdf_summary_prompt(
        prompt: str,
        pdf_content: str
) -> str:
    try:
        formatted_prompt = prompt.format(
            pdf_content=pdf_content
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build PDF summary prompt: {e}")
        raise


def get_prompt_overview_article(
        prompt: str,
        metadata: RepositoryMetadata,
        files_summary: str,
        pdf_summary: str
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            files_summary=files_summary,
            pdf_summary=pdf_summary
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build overview prompt: {e}")
        raise

def get_prompt_content_article(
        prompt: str,
        metadata: RepositoryMetadata,
        key_files: list[FileContext],
        pdf_summary: str
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            files_content=key_files,
            pdf_summary=pdf_summary
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build content prompt: {e}")
        raise


def get_prompt_algorithms_article(
        prompt: str,
        metadata: RepositoryMetadata,
        files_summary: str,
        pdf_summary: str
) -> str:
    try:
        formatted_prompt = prompt.format(
            project_name=metadata.name,
            file_summary=files_summary,
            pdf_summary=pdf_summary
        )
        return formatted_prompt
    except Exception as e:
        logger.error(f"Failed to build algorithms prompt: {e}")
        raise


def serialize_file_contexts(files: list[FileContext]) -> str:
    """
    Serializes a list of FileContext objects into a string.

    For each FileContext object, a Markdown section is created that includes
    the file's name, its path, and its content. All sections are separated by
    two newlines.

    Args:
        files (list[FileContext]): A list of FileContext objects representing files.

    Returns:
        str: A string representing the serialized file data in Markdown format.
            Each section includes the file's name, path, and content.
    """
    return "\n\n".join(
        f"### {f.name} ({f.path})\n{f.content}" for f in files
    )
