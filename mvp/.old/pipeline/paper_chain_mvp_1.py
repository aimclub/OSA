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
    max_retries: int,
) -> str:
    logger.info("Starting step: %s", step_name)
    history.append(HumanMessage(content=user_prompt))
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        logger.info("Step '%s' attempt %s/%s", step_name, attempt, max_retries)
        last_raw = await _ainvoke_with_history(handler, history)
        history.append(AIMessage(content=last_raw))
        try:
            logger.info("Step '%s' parse success on attempt %s/%s", step_name, attempt, max_retries)
            return last_raw
        except Exception as exc:
            logger.warning("Step '%s' parse failed on attempt %s/%s: %s", step_name, attempt, max_retries, exc)
            if attempt == max_retries:
                raise

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

    system_prompt = "You are an expert in analyzing machine learning research reports."

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step1_prompt = (
        "Your task is to identify and extract specific sections from a student "
        "ML report, regardless of how those sections are titled."
        "Return a JSON object with these keys:"
        "- 'problem_statement': text describing the task/problem being solved"
        "- 'dataset': text describing data used (source, size, splits, preprocessing)"
        "- 'methodology': text describing model architecture and design choices"
        "- 'training': text describing training procedure, hyperparameters, augmentation"
        "- 'evaluation': text describing metrics and evaluation protocol"
        "- 'results': text describing numerical outcomes and comparisons"
        "- 'baseline': text describing baseline models or related work comparisons"
        "If a section is not present, set its value to null."
        "Do not summarize — extract the original text verbatim."
        "Return only valid JSON, no preamble."
        f"REPORT:\n{paper_content}"
    )
    raw = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_1",
        user_prompt=step1_prompt,
        max_retries=args.max_retries,
    )

    step2_prompt = (
        "Your task is to extract verifiable factual claims from a section "
        "of a student ML report."
        "A 'verifiable claim' is a specific, concrete statement that can "
        "be confirmed or refuted by inspecting the code repository. "
        "Good examples of verifiable claims:"
        "- 'ResNet-50 was used as the backbone'"
        "- 'The dataset was split 80/10/10 for train/val/test'"
        "- 'Adam optimizer with lr=0.001 was used'"
        "- 'Data augmentation includes random horizontal flips'"
        "- 'F1-macro score on the test set is 0.847'"
        "- 'The model was trained for 50 epochs'"
        "- 'batch size of 32 was used'"
        "Bad examples (do NOT extract these):"
        "- Vague statements: 'a deep learning model was used'"
        "- Motivations: 'we chose this approach because it is efficient'"
        "- References to prior work: 'ResNet was proposed by He et al.'"
        "- Evaluation of quality: 'the results are satisfactory'"
        "For each claim, return:"
        "- 'claim': the claim restated as a clear, self-contained sentence"
        "- 'original_text': the verbatim fragment from the report (max 30 words)"
        "- 'category': one of [dataset, model_architecture, training_procedure, "
        "evaluation_metric, numerical_result, baseline_comparison, "
        "data_preprocessing, infrastructure]"
        "- 'value': the specific value if present (number, ratio, name), else null"
        "- 'verifiability': 'high' if directly visible in code (import, function call, "
        "constant), 'medium' if inferable (e.g. from output logs), "
        "'low' if only in comments or not executable"
        "Return a JSON array. Return only valid JSON, no preamble."
        "If no verifiable claims are found, return an empty array []."
    )
    raw = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_2",
        user_prompt=step2_prompt,
        max_retries=args.max_retries,
    )

    system_prompt = (
        "You are reviewing a list of claims extracted from different sections "
        "of an ML report. Some claims may be duplicates or near-duplicates."
    )

    history.append(SystemMessage(content=system_prompt))

    step3_prompt = (
        "Your task:"
        "1. Merge claims that refer to the same fact. Keep the more specific version."
        "2. Resolve contradictions: if two claims disagree on the same fact"
        "(e.g. 'lr=0.001' and 'lr=0.0001'), keep both and add"
        "'contradiction': true to both."
        "3. Do not remove claims just because they seem unlikely or wrong —"
        "that is for the verification step."
        "Return the deduplicated list as a JSON array with the same schema,"
        "plus an optional 'contradiction' boolean field."
        "Return only valid JSON, no preamble."
    )
    final_raw = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_3",
        user_prompt=step3_prompt,
        max_retries=args.max_retries,
    )
    logger.info("Completed all steps.")
    logger.info(final_raw)

    result = {
        "result": JsonProcessor.parse(final_raw),
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
