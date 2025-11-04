import os

import tomli

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.logger import logger
from osa_tool.utils import osa_project_root


def compile_license_file(sourcerank: SourceRank, ensure_license, metadata: RepositoryMetadata):
    """
    Compiles a license file for a software project using a specified template.

    This method takes a SourceRank object as input, extracts necessary information such as creation year and author
    to compile a license file based on a predefined template. The compiled license file is then saved in the repository
    directory of the SourceRank object.

    Parameters:
        - sourcerank: SourceRank object containing metadata about the software project.
        - ensure_license: License type provided by user.
        - metadata: Git repository metadata.

    Returns:
        None. The compiled license file is saved in the repository directory of the SourceRank object.
    """
    try:
        if sourcerank.license_presence():
            logger.info("LICENSE file already exists.")
        else:
            logger.info("LICENSE was not resolved, compiling started...")
            metadata = metadata
            license_template_path = os.path.join(osa_project_root(), "docs", "templates", "licenses.toml")
            with open(license_template_path, "rb") as f:
                license_template = tomli.load(f)
            license_type = ensure_license
            year = metadata.created_at[:4]
            author = metadata.owner
            try:
                license_text = license_template[license_type]["template"].format(year=year, author=author)
                license_output_path = os.path.join(sourcerank.repo_path, "LICENSE")
                with open(license_output_path, "w") as f:
                    f.write(license_text)
                logger.info(
                    f"LICENSE has been successfully compiled at {os.path.join(sourcerank.repo_path, 'LICENSE')}."
                )
            except KeyError:
                logger.error(
                    f"Couldn't resolve {license_type} license type, try to look up available licenses at documentation."
                )
    except Exception as e:
        logger.error("Error while compiling LICENSE: %s", e, exc_info=True)
