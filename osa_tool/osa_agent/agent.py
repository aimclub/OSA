from langchain_core.output_parsers import PydanticOutputParser
from langgraph.constants import END
from langgraph.graph import StateGraph

from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.operations.registry import OperationRegistry
from osa_tool.osa_agent.config import OSAConfig
from osa_tool.osa_agent.models import IntentDecision, PlannerDecision
from osa_tool.osa_agent.state import OSAState, AgentStatus
from osa_tool.tools.repository_analysis.repo_analyzer import RepositoryAnalyzer
from osa_tool.ui.input_for_chat import clarify_user_input
from osa_tool.utils.prompts_builder import PromptBuilder


class OSAAgent:
    def __init__(self, agent_config: OSAConfig):
        self.agent_config = agent_config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.agent_config.config_loader.config)
        self.git_agent = self.agent_config.git_agent
        self.workflow_manager = self.agent_config.workflow_manager
        self.prompts = self.agent_config.config_loader.config.prompts
        self.create_fork = self.agent_config.create_fork
        self.create_pull_request = self.agent_config.create_pull_request

    def intent_router(self, state: OSAState) -> OSAState:
        """
        Determine user's intent and task scope.
        Does NOT analyze repository.
        """
        if state.status == AgentStatus.WAITING_FOR_USER:
            update_state_from_clarification(state)

        parser = PydanticOutputParser(pydantic_object=IntentDecision)
        system_message = PromptBuilder.render(self.prompts.get("system_messages.intent_router"), safe=True)
        prompt = PromptBuilder.render(
            self.prompts.get("osa_agent.intent_router"),
            user_request=state.user_request,
            attachment=state.attachment,
        )

        decision: IntentDecision = self.model_handler.run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

        # Update state
        state.intent = decision.intent
        state.task_scope = decision.task_scope
        state.intent_confidence = decision.confidence

        state.session_memory.append(
            {
                "agent": "IntentRouter",
                "request": prompt,
                "decision": decision.model_dump(),
            }
        )

        # Low confidence → wait for user clarification
        if decision.confidence < 0.5 or decision.intent == "unknown":
            state.status = AgentStatus.WAITING_FOR_USER
        else:
            state.status = AgentStatus.ANALYZING

        state.active_agent = "IntentRouter"
        return state

    def repo_analysis(self, state: OSAState) -> OSAState:
        """Docstring"""
        # Prepare repository to analysis
        if not state.repo_prepared:
            if self.create_fork:
                self.git_agent.star_repository()
                self.git_agent.create_fork()

            self.git_agent.clone_repository()

            if self.create_fork:
                self.git_agent.create_and_checkout_branch()

            state.repo_path = self.git_agent.clone_dir
            state.repo_prepared = True

        # Analyze repository
        analyzer = RepositoryAnalyzer(state.repo_path, self.workflow_manager.existing_jobs)
        repo_data = analyzer.analyze()

        # Update state
        state.repo_data = repo_data
        state.repo_metadata = self.git_agent.metadata
        state.status = AgentStatus.ANALYZING
        state.active_agent = "RepoAnalysis"

        return state

    def planner(self, state: OSAState) -> OSAState:
        """Docstring"""
        available_ops = OperationRegistry.applicable(state)

        parser = PydanticOutputParser(pydantic_object=PlannerDecision)
        system_message = PromptBuilder.render(self.prompts.get("system_messages.planner"), safe=True)
        prompt = PromptBuilder.render(
            self.prompts.get("osa_agent.planner"),
            user_request=state.user_request,
            intent=state.intent,
            task_scope=state.task_scope,
            repo_data=state.repo_data,
            available_operations="\n".join(f"- {op.name}: {op.description}" for op in available_ops),
        )

        decision: PlannerDecision = self.model_handler.run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

        selected_ops = [OperationRegistry.get(name) for name in decision.operations if OperationRegistry.get(name)]

        # Sort ONLY by developer-defined priority
        selected_ops.sort(key=lambda op: op.priority)

        state.plan = [task for op in selected_ops for task in op.plan_tasks()]

        state.current_step_index = 0
        state.status = AgentStatus.GENERATING
        state.active_agent = "Planner"

        state.session_memory.append(
            {
                "agent": "Planner",
                "prompts": prompt,
                "decision": decision.model_dump(),
                "plan": [t.model_dump() for t in state.plan],
            }
        )

        return state

    @classmethod
    def build_graph(cls, agent_config: OSAConfig):
        osa_agent = cls(agent_config)

        graph = StateGraph(OSAState)
        graph.add_node("intent_router", osa_agent.intent_router)
        graph.add_node("repo_analysis", osa_agent.repo_analysis)
        graph.add_node("planner", osa_agent.planner)

        graph.set_entry_point("intent_router")

        graph.add_conditional_edges(
            "intent_router",
            lambda state: ("intent_router" if state.status == AgentStatus.WAITING_FOR_USER else "repo_analysis"),
        )

        graph.add_edge("repo_analysis", "planner")
        graph.add_edge("planner", END)

        return graph.compile()


def update_state_from_clarification(state: OSAState):
    clarification = clarify_user_input()
    state.user_request = clarification.user_request
    if clarification.attachment:
        state.attachment = clarification.attachment

    state.status = AgentStatus.ANALYZING
    return state
