import json
import os
import re

import requests
import tomli

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.header import HeaderBuilder
from osa_tool.readmegen.generator.installation import InstallationSectionBuilder
from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.readmegen.utils import clean_code_block_indents, find_in_repo_tree
from osa_tool.utils import osa_project_root


class MarkdownBuilderBase:
    """
    Base class for constructing Markdown README files from repository metadata and optional JSON sections.
    
    This class provides a framework for generating standard README sections such as Overview, Getting Started, Examples, Documentation, License, and Citation. It also handles template loading, URL validation, and deduplication of sections using an LLM.
    
    Class Methods
    -------------
    - __init__: Initializes the builder with configuration and optional JSON data.
    - load_template: Loads a TOML template file and returns its sections as a dictionary.
    - _check_url: Checks if a given URL is reachable and returns HTTP 200.
    - deduplicate_sections: Deduplicates Installation and Getting Started sections via LLM if both are present.
    - overview: Generates the README Overview section.
    - getting_started: Generates the README Getting Started section.
    - examples: Generates the README Examples section.
    - documentation: Generates the README Documentation section.
    - license: Generates the README License section.
    - citation: Generates the README Citation section.
    - table_of_contents: Generates an adaptive Table of Contents based on provided sections.
    
    Attributes
    ----------
    config_loader
        The :class:`ConfigLoader` instance passed to the constructor.
    config
        The configuration dictionary obtained from ``config_loader``.
    sourcerank
        Instance of :class:`SourceRank` initialized with the same ``config_loader``. Holds the repository tree and related information.
    repo_url
        Repository URL extracted from the configuration.
    metadata
        Repository metadata retrieved via :func:`load_data_metadata` using ``repo_url``. Provides information such as the default branch.
    url_path
        Base URL path for the repository on its hosting platform, constructed from ``config.git.host_domain`` and ``config.git.full_name``.
    branch_path
        Path to the default branch tree in the repository, formatted as ``tree/<default_branch>/``.
    _overview_json
        Stored overview JSON data passed to the constructor.
    _getting_started_json
        Stored getting‑started JSON data passed to the constructor.
    header
        Header section built by :class:`HeaderBuilder`.
    installation
        Installation section built by :class:`InstallationSectionBuilder`.
    template_path
        Filesystem path to the ``template.toml`` file located in the project's ``config/templates`` directory.
    _template
        Loaded template content returned by :meth:`load_template`.
    """
    def __init__(self, config_loader: ConfigLoader, overview=None, getting_started=None):
        """
        Initialize the object with configuration and optional JSON data.
        
        Parameters
        ----------
        config_loader
            Configuration loader instance that provides access to the repository
            configuration.
        overview
            Optional JSON data for the overview section.
        getting_started
            Optional JSON data for the getting‑started section.
        
        Attributes
        ----------
        config_loader
            The :class:`ConfigLoader` instance passed to the constructor.
        config
            The configuration dictionary obtained from ``config_loader``.
        sourcerank
            Instance of :class:`SourceRank` initialized with the same
            ``config_loader``.  It holds the repository tree and related
            information.
        repo_url
            Repository URL extracted from the configuration.
        metadata
            Repository metadata retrieved via :func:`load_data_metadata` using
            ``repo_url``.  Provides information such as the default branch.
        url_path
            Base URL path for the repository on its hosting platform,
            constructed from ``config.git.host_domain`` and
            ``config.git.full_name``.
        branch_path
            Path to the default branch tree in the repository,
            formatted as ``tree/<default_branch>/``.
        _overview_json
            Stored overview JSON data passed to the constructor.
        _getting_started_json
            Stored getting‑started JSON data passed to the constructor.
        header
            Header section built by :class:`HeaderBuilder`.
        installation
            Installation section built by :class:`InstallationSectionBuilder`.
        template_path
            Filesystem path to the ``template.toml`` file located in the
            project's ``config/templates`` directory.
        _template
            Loaded template content returned by :meth:`load_template`.
        
        Returns
        -------
        None
        """
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.sourcerank = SourceRank(self.config_loader)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.url_path = f"https://{self.config.git.host_domain}/{self.config.git.full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"

        self._overview_json = overview
        self._getting_started_json = getting_started

        self.header = HeaderBuilder(self.config_loader).build_header()
        self.installation = InstallationSectionBuilder(self.config_loader).build_installation()

        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self._template = self.load_template()

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @staticmethod
    def _check_url(url):
        """
        Check if a given URL is reachable and returns HTTP 200.
        
        Args:
            url: The URL to be checked.
        
        Returns:
            bool: True if the URL responds with status code 200, False otherwise.
        """
        response = requests.get(url)
        return response.status_code == 200

    def deduplicate_sections(self):
        """Deduplicates Installation and Getting Started sections via LLM if both are present."""
        if not self.installation or not self._getting_started_json:
            return

        getting_started_text = json.loads(self._getting_started_json)
        if not getting_started_text["getting_started"]:
            return

        llm_client = LLMClient(self.config_loader)
        response = llm_client.deduplicate_sections(self.installation, getting_started_text["getting_started"])
        response = json.loads(response)

        self.installation = clean_code_block_indents(response["installation"] or "")
        new_getting_started = clean_code_block_indents(response["getting_started"])
        if new_getting_started is not None:
            self._getting_started_json = json.dumps({"getting_started": new_getting_started})
        else:
            self._getting_started_json = json.dumps({"getting_started": None})

    @property
    def overview(self) -> str:
        """Generates the README Overview section"""
        if not self._overview_json:
            return ""
        overview_data = json.loads(self._overview_json)
        return self._template["overview"].format(overview_data["overview"])

    @property
    def getting_started(self) -> str:
        """Generates the README Getting Started section"""
        if not self._getting_started_json:
            return ""

        getting_started_text = json.loads(self._getting_started_json)
        if not getting_started_text["getting_started"]:
            return ""
        return self._template["getting_started"].format(getting_started_text["getting_started"])

    @property
    def examples(self) -> str:
        """Generates the README Examples section"""
        if not self.sourcerank.examples_presence():
            return ""

        pattern = r"\b(tutorials?|examples|notebooks?)\b"
        path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        return self._template["examples"].format(path=path)

    @property
    def documentation(self) -> str:
        """Generates the README Documentation section"""
        if not self.metadata.homepage_url:
            if self.sourcerank.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
            else:
                return ""
        else:
            path = self.metadata.homepage_url
        return self._template["documentation"].format(repo_name=self.metadata.name, path=path)

    @property
    def license(self) -> str:
        """Generates the README License section"""
        if not self.metadata.license_name:
            return ""

        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        help_var = find_in_repo_tree(self.sourcerank.tree, pattern)
        path = self.url_path + self.branch_path + help_var if help_var else self.metadata.license_url
        return self._template["license"].format(license_name=self.metadata.license_name, path=path)

    @property
    def citation(self) -> str:
        """Generates the README Citation section"""
        if self.sourcerank.citation_presence():
            pattern = r"\bCITATION(\.\w+)?\b"
            path = self.url_path + self.branch_path + find_in_repo_tree(self.sourcerank.tree, pattern)
            return self._template["citation"] + self._template["citation_v1"].format(path=path)

        return self._template["citation"] + self._template["citation_v2"].format(
            owner=self.metadata.owner,
            year=self.metadata.created_at.split("-")[0],
            repo_name=self.config.git.name,
            publisher=self.config.git.host_domain,
            repository_url=self.config.git.repository,
        )

    @staticmethod
    def table_of_contents(sections: dict) -> str:
        """Generates an adaptive Table of Contents based on provided sections."""
        toc = ["## Table of Contents\n"]

        for section_name, section_content in sections.items():
            if section_content:
                toc.append("- [{}]({})".format(section_name, "#" + re.sub(r"\s+", "-", section_name.lower())))

        toc.append("\n---")
        return "\n".join(toc)
