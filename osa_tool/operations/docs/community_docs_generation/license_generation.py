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


class LicenseCompiler:
    """
    Compiles and ensures the presence of a LICENSE file in a repository.

    This class is responsible for generating a LICENSE file based on a predefined
    license template and repository metadata. It resolves the target repository
    using SourceRank, checks whether a LICENSE file already exists, and, if not,
    renders and writes the license text to the repository root.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        metadata: RepositoryMetadata,
        license_type: str,
    ):
        self.sourcerank = SourceRank(config_loader)
        self.metadata = metadata
        self.license_type = license_type
        self.license_template_path = os.path.join(osa_project_root(), "docs", "templates", "licenses.toml")

    def run(self) -> None:
        """
        Executes the license compilation process.
        """
        try:
            if self.sourcerank.license_presence():
                logger.info("LICENSE file already exists.")
                return

            logger.info("LICENSE was not resolved, compiling started...")

            with open(self.license_template_path, "rb") as f:
                license_template = tomli.load(f)

            try:
                license_text = license_template[self.license_type]["template"].format(
                    year=self.metadata.created_at[:4],
                    author=self.metadata.owner,
                )
                license_output_path = os.path.join(self.sourcerank.repo_path, "LICENSE")

                with open(license_output_path, "w", encoding="utf-8") as f:
                    f.write(license_text)

                logger.info(f"LICENSE has been successfully compiled at {license_output_path}.")

            except KeyError:
                logger.error(
                    f"Couldn't resolve {self.license_type} license type, "
                    "try to look up available licenses at documentation."
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
        "Expected key: 'license_type'."
        "Allowed values: 'bsd-3', 'mit', 'ap2'."
        "If not specified, use 'bsd-3'."
    )

    executor = LicenseCompiler
    executor_method = "run"
    executor_dependencies = ["config_loader", "metadata"]


OperationRegistry.register(EnsureLicenseOperation())
