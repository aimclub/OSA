from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from osa_tool.operations.docs.readme_generation.generator.builder_article import MarkdownBuilderArticle
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def _collect_generated_sections(state: ReadmeState) -> str:
    """Collect all non-None generated sections into a labeled string for the merge prompt."""
    parts = []
    if state.generated_sections:
        for name, value in state.generated_sections.items():
            if value:
                parts.append(f"### {name}\n{value}")
        if parts:
            return "\n\n".join(parts)

    section_map = {
        "overview": state.overview,
        "core_features": str(state.core_features) if state.core_features else None,
        "getting_started": state.getting_started,
        "content": state.content,
        "algorithms": state.algorithms,
        "file_summary": state.file_summary,
        "pdf_summary": state.pdf_summary,
    }
    for name, value in section_map.items():
        if value:
            parts.append(f"### {name}\n{value}")
    return "\n\n".join(parts)


def section_assembler_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Assemble sections into readme_draft (full_regen: build, targeted: LLM merge)."""
    logger.info("[SectionAssembler] Assembling README draft (mode=%s)...", state.generation_mode)

    if state.generation_mode == "targeted":
        new_sections = _collect_generated_sections(state)
        if new_sections:
            merge_targets = state.resolved_target_sections or state.target_sections
            readme_draft = context.model_handler.send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get("readme_agent.section_merge"),
                    existing_readme=state.existing_readme,
                    new_sections=new_sections,
                    target_sections=", ".join(merge_targets),
                    generation_plan=state.generation_plan or "",
                ),
                parser=LlmTextOutput,
            ).text
            readme_draft = readme_draft if readme_draft is not None else state.existing_readme
        else:
            readme_draft = state.existing_readme
    elif state.readme_mode == "article":
        builder = MarkdownBuilderArticle(
            context.config_manager,
            context.metadata,
            overview=state.overview,
            content=state.content,
            algorithms=state.algorithms,
            getting_started=state.getting_started,
        )
        readme_draft = builder.build()
    else:
        builder = MarkdownBuilder(
            context.config_manager,
            context.metadata,
            overview=state.overview,
            core_features=state.core_features,
            getting_started=state.getting_started,
        )
        readme_draft = builder.build()

    logger.info("[SectionAssembler] Draft assembled.")
    return {"readme_draft": readme_draft}
