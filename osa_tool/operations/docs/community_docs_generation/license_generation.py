import os
from typing import Literal

import tomli
from pydantic import BaseModel

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


def compile_license_file(config_loader: ConfigLoader, metadata: RepositoryMetadata, ensure_license):
    """
    Compiles a license file for a software project using a specified template.

    This method takes a SourceRank object as input, extracts necessary information such as creation year and author
    to compile a license file based on a predefined template. The compiled license file is then saved in the repository
    directory of the SourceRank object.

    Parameters:
        - config_loader: Loader containing configuration settings.
        - metadata: Git repository metadata.
        - ensure_license: License type provided by user.

    Returns:
        None. The compiled license file is saved in the repository directory of the SourceRank object.
    """
    sourcerank = SourceRank(config_loader)

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


class EnsureLicenseArgs(BaseModel):
    ensure_license: Literal["bsd-3", "mit", "ap2"] = "bsd-3"


class EnsureLicenseOperation(Operation):
    name = "ensure_license"
    description = "Ensure LICENSE file exists"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 60

    args_schema = EnsureLicenseArgs
    args_policy = "auto"
    prompt_for_args = (
        "For operation 'ensure_license' provide a license type. "
        "Expected key: 'ensure_license'."
        "Allowed values: 'bsd-3', 'mit', 'ap2'."
        "If not specified, use 'bsd-3'."
    )

    executor = staticmethod(compile_license_file)
    executor_method = None
    executor_dependencies = ["config_loader", "metadata"]


OperationRegistry.register(EnsureLicenseOperation())
