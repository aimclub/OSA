from osa_tool.core.models.agent import AgentStatus
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.tools.repository_analysis.repo_analyzer import RepositoryAnalyzer
from osa_tool.utils.utils import rich_section


class RepoAnalysisAgent(BaseAgent):
    name = "RepoAnalysis"

    def run(self, state: OSAState) -> OSAState:
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

    def _prepare_repo(self, state: OSAState):
        if self.context.create_fork:
            self.context.git_agent.star_repository()
            self.context.git_agent.create_fork()

        self.context.git_agent.clone_repository()

        if self.context.create_fork:
            self.context.git_agent.create_and_checkout_branch()

        state.repo_path = self.context.git_agent.clone_dir
        state.repo_prepared = True
