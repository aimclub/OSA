from osa_tool.core.models.agent import AgentStatus
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.tools.repository_analysis.repo_analyzer import RepositoryAnalyzer
from osa_tool.utils.utils import rich_section


class RepoAnalysisAgent(BaseAgent):
    """
    Agent responsible for preparing and analyzing the repository.

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

        This method:
        1. Ensures the repository is cloned and ready for analysis
        2. Runs repository analysis to collect structural and semantic data
        3. Updates the workflow state with repository information

        Args:
            state (OSAState): Current workflow state.

        Returns:
            OSAState: Updated state containing repository analysis results.
        """
        rich_section("Repository Analysis Agent")

        # Prepare repository if not already prepared
        if not state.repo_prepared:
            self._prepare_repo(state)

        # Analyze repository
        analyzer = RepositoryAnalyzer(state.repo_path, self.context.workflow_manager.existing_jobs)
        repo_data = analyzer.analyze()

        # Update state with repository data
        state.repo_data = repo_data
        state.repo_metadata = self.context.git_agent.metadata
        state.status = AgentStatus.ANALYZING
        state.active_agent = self.name

        return state

    def _prepare_repo(self, state: OSAState) -> None:
        """
        Clone and initialize the repository workspace.

        This method may:
        - star the repository
        - create a fork
        - clone the repository locally
        - create and checkout a working branch

        Side effects:
            - filesystem writes
            - remote Git operations
        """
        if self.context.create_fork:
            self.context.git_agent.star_repository()
            self.context.git_agent.create_fork()

        self.context.git_agent.clone_repository()

        if self.context.create_fork:
            self.context.git_agent.create_and_checkout_branch()

        state.repo_path = self.context.git_agent.clone_dir
        state.repo_prepared = True
