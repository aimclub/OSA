#!/usr/bin/env python3
"""MVP script: multi-turn paper experiment extraction with ProtoLLM message history."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import docx2txt
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory, ProtollmHandler
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.response_cleaner import JsonProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract experiment list from paper using multi-turn message history (ProtoLLM MVP)."
    )
    parser.add_argument("--repository", default="https://github.com/ai-chem/DiMag")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--attachment", required=True, help="Path or URL to .pdf or path to .docx")
    parser.add_argument("--config-file", default=None, help="Optional path to OSA config.toml")
    parser.add_argument("--output", default=None, help="Optional path to write resulting JSON")
    parser.add_argument("--max-retries", type=int, default=3, help="Retries for each chain step")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Terminal log level. Use DEBUG to print request/response messages.",
    )
    return parser.parse_args()


def configure_terminal_logging(level: str) -> None:
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False


def parse_document(document_path: str) -> str:
    if document_path.endswith(".docx"):
        logger.info("Processing DOCX...")
        return docx2txt.process(document_path)

    if document_path.endswith(".pdf"):
        path_to_pdf = get_pdf_path(document_path)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Processing PDF...")
        return PdfParser(path_to_pdf).data_extractor()

    raise ValueError(f"Unprocessable file format: {document_path}")


def _extract_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


async def _ainvoke_with_history(
    handler: ProtollmHandler,
    messages: list[Any],
    retry_delay: float = 1.0,
) -> str:
    last_error = None

    for _ in handler._iter_configured_models():
        try:
            logger.debug("Request messages payload:\n%s", _format_messages(messages))
            response = await handler.client.ainvoke(messages)
            content = _extract_content(response)
            logger.debug("Raw response content:\n%s", content)
            return content
        except Exception as exc:
            last_error = exc
            logger.debug(repr(exc))
            await asyncio.sleep(retry_delay)

    logger.error(f"All models failed. Last error: {last_error}")
    raise last_error


def _parse_list(raw: str, key: str) -> list[str]:
    data = JsonProcessor.parse(raw, expected_key=key, expected_type=list)
    cleaned: list[str] = []
    for item in data:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                cleaned.append(stripped)
    return cleaned


def _format_messages(messages: list[Any]) -> str:
    rendered: list[str] = []
    for idx, msg in enumerate(messages, start=1):
        role = getattr(msg, "type", None) or getattr(msg, "role", None) or msg.__class__.__name__
        content = getattr(msg, "content", msg)
        rendered.append(f"[{idx}] role={role}\n{content}")
    return "\n\n".join(rendered)


async def _step_with_repair(
    *,
    handler: ProtollmHandler,
    history: list[Any],
    step_name: str,
    user_prompt: str,
    parse_key: str,
    max_retries: int,
) -> tuple[str, list[str]]:
    logger.info("Starting step: %s", step_name)
    history.append(HumanMessage(content=user_prompt))
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        logger.info("Step '%s' attempt %s/%s", step_name, attempt, max_retries)
        last_raw = await _ainvoke_with_history(handler, history)
        history.append(AIMessage(content=last_raw))

        try:
            parsed = _parse_list(last_raw, parse_key)
            logger.info("Step '%s' parse success on attempt %s/%s", step_name, attempt, max_retries)
            logger.debug("Step '%s' parsed %s items under key '%s'", step_name, len(parsed), parse_key)
            return last_raw, parsed
        except Exception as exc:
            logger.warning("Step '%s' parse failed on attempt %s/%s: %s", step_name, attempt, max_retries, exc)
            if attempt == max_retries:
                raise
            history.append(
                HumanMessage(
                    content=(
                        f"Your previous answer was not valid JSON with key '{parse_key}'. "
                        "Return ONLY valid JSON and nothing else.\n"
                        f"Previous answer:\n{last_raw}"
                    )
                )
            )

    raise RuntimeError("Unreachable parse loop state.")


async def run() -> dict[str, Any]:
    args = parse_args()
    configure_terminal_logging(args.log_level)
    logger.info("Running paper_chain_mvp with log level %s", args.log_level)
    config_manager = ConfigManager(args)
    model_settings = config_manager.get_model_settings("validation")
    handler = ModelHandlerFactory.build(model_settings)
    logger.info("Initialized model handler for model: %s", handler.model_settings.model)

    paper_content = await asyncio.to_thread(parse_document, args.attachment)
    logger.info("Document parsed. Character count: %s", len(paper_content))

    system_prompt = (
        "You are an assistant that extracts reproducible experiment descriptions from scientific papers. "
        "Keep intermediate reasoning private and return only requested JSON."
    )

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step1_prompt = (
        "Task: Find candidate experiment descriptions in this paper text. "
        'Return only JSON: {"candidate_experiments": ["..."]}. '
        "Keep each item close to source wording and in original order.\n\n"
        f"PAPER:\n{paper_content}"
    )
    _, candidate_experiments = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="candidate_experiments",
        user_prompt=step1_prompt,
        parse_key="candidate_experiments",
        max_retries=args.max_retries,
    )

    step2_prompt = (
        "Refine the candidate list: remove duplicates and non-experiments, keep only items that can be checked "
        "against code reproducibility. Preserve source wording as much as possible.\n"
        'Return only JSON: {"refined_experiments": ["..."]}.\n\n'
        f"CANDIDATES:\n{json.dumps(candidate_experiments, ensure_ascii=True)}"
    )
    _, refined_experiments = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="refined_experiments",
        user_prompt=step2_prompt,
        parse_key="refined_experiments",
        max_retries=args.max_retries,
    )

    step3_prompt = (
        "Produce the final output for downstream validator.\n"
        "Rules:\n"
        "- Return ONLY JSON.\n"
        "- Use key 'experiment_list'.\n"
        "- Keep list order stable.\n"
        "- Replace non-ASCII characters with ASCII variants when possible.\n\n"
        'Return exactly: {"experiment_list": ["..."]}.\n\n'
        f"REFINED:\n{json.dumps(refined_experiments, ensure_ascii=True)}"
    )
    final_raw, experiment_list = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="final_experiment_list",
        user_prompt=step3_prompt,
        parse_key="experiment_list",
        max_retries=args.max_retries,
    )
    logger.info("Completed all steps. Final experiment count: %s", len(experiment_list))

    result = {
        "experiment_list": experiment_list,
        "meta": {
            "source": args.attachment,
            "steps": 3,
            "history_messages": len(history),
            "model": handler.model_settings.model,
        },
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("Saved result to %s", output_path)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=True))

    logger.debug("Final raw response:\n%s", final_raw)
    return result


if __name__ == "__main__":
    asyncio.run(run())

# CLAIM
