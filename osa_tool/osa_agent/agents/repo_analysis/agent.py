from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.tools.repository_analysis.repo_analyzer import RepositoryAnalyzer
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section


class RepoAnalysisAgent(BaseAgent):
    """
    Agent responsible for preparing and analyzing the repository for automated documentation generation, structural improvements, and content validation.
    
        The RepoAnalysisAgent:
        - clones and optionally forks the repository
        - prepares a working branch if required
        - performs static repository analysis
        - stores repository metadata and analysis results in the state
    """


    name = "RepoAnalysis"

    def run(self, state: OSAState) -> OSAState:
        """
        Prepare the repository and extract structural information.
        
        This method orchestrates the repository analysis phase of the workflow. It ensures a local copy of the repository is ready, performs a comprehensive structural and semantic analysis, and updates the workflow state with the results.
        
        The method:
        1. Ensures the repository is cloned and ready for analysis. If not already prepared, it clones the repository (optionally creating a fork first, depending on the agent's context).
        2. Runs repository analysis to collect structural and semantic data, including testing setup, file structure, and dependency information.
        3. Updates the workflow state with the repository information and analysis results.
        
        Args:
            state: Current workflow state. The method updates this object in place and returns it.
        
        Returns:
            Updated state containing repository analysis results. The state includes `repo_data` (the analysis output), `repo_metadata` (Git metadata from the cloning process), and updated status fields.
        """
        rich_section("Repository Analysis Agent")
        logger.info("Repo analysis started")

        state.active_agent = self.name
        state.status = AgentStatus.ANALYZING

        # Prepare repository if not already prepared
        if not state.repo_prepared:
            logger.debug("Repository not prepared; cloning and preparing")
            self._prepare_repo(state)
        else:
            logger.debug("Repository already prepared at %s", state.repo_path)

        # Analyze repository
        analyzer = RepositoryAnalyzer(state.repo_path, self.context.workflow_manager.existing_jobs)
        repo_data = analyzer.analyze()
        logger.debug("Repository analysis data collected")

        # Update state with repository data
        state.repo_data = repo_data
        state.repo_metadata = self.context.git_agent.metadata
        logger.info("Repository analysis completed")
        return state

    def _prepare_repo(self, state: OSAState) -> None:
        """
        Clone and initialize the repository workspace.
        
        This method orchestrates the local and remote Git operations required to prepare a working copy of the repository for analysis or modification. Its behavior is conditional based on the `create_fork` flag in the agent's context.
        
        If `create_fork` is True, the method will:
        - Star the repository on Gitverse (to support the forking workflow).
        - Create a fork of the repository on Gitverse for the authenticated user.
        - Clone the forked repository locally.
        - Create and checkout a new working branch (typically for isolated changes).
        
        If `create_fork` is False, the method will:
        - Clone the original repository locally without forking or starring.
        
        After cloning, the method updates the analysis state with the local repository path and marks the repository as prepared.
        
        Args:
            state: The current analysis state object. Its `repo_path` attribute will be set to the local clone directory, and `repo_prepared` will be set to True.
        
        Side effects:
            - Filesystem writes (local repository clone).
            - Remote Git operations (starring, forking, cloning).
            - Modifies the provided `state` object in place.
        """
        if self.context.create_fork:
            self.context.git_agent.star_repository()
            self.context.git_agent.create_fork()

        self.context.git_agent.clone_repository()

        if self.context.create_fork:
            self.context.git_agent.create_and_checkout_branch()

        state.repo_path = self.context.git_agent.clone_dir
        state.repo_prepared = True
        logger.info("Repository prepared: %s", state.repo_path)
