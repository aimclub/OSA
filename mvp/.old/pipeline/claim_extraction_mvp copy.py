#!/usr/bin/env python3
"""MVP script: multi-turn paper experiment extraction with ProtoLLM message history."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory, ProtollmHandler
from osa_tool.utils.logger import logger
from osa_tool.utils.response_cleaner import JsonProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract experiment list from paper using multi-turn message history (ProtoLLM MVP)."
    )
    parser.add_argument("--repository", default="https://github.com/ai-chem/DiMag")
    parser.add_argument("--model", default="openai/gpt-oss-120b")  # deepseek/deepseek-v3.2 openai/gpt-oss-120b
    parser.add_argument("--attachment", required=True, help="Path or URL to .pdf or path to .docx")
    parser.add_argument("--config-file", default=None, help="Optional path to OSA config.toml")
    parser.add_argument("--output", default=None, help="Optional path to write resulting JSON")
    parser.add_argument("--max-retries", type=int, default=5, help="Retries for each chain step")
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


def _parse_list(raw: str, key: str | None = None) -> list[str]:
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
) -> tuple[str, list[str]]:
    logger.info("Starting step: %s", step_name)
    history.append(HumanMessage(content=user_prompt))
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        logger.info("Step '%s' attempt %s/%s", step_name, attempt, max_retries)
        last_raw = await _ainvoke_with_history(handler, history)
        history.append(AIMessage(content=last_raw))
        try:
            parsed = _parse_list(last_raw)
            logger.info("Step '%s' parse success on attempt %s/%s", step_name, attempt, max_retries)
            return last_raw, parsed
        except Exception as exc:
            logger.warning("Step '%s' parse failed on attempt %s/%s: %s", step_name, attempt, max_retries, exc)
            if attempt == max_retries:
                return last_raw, []

    raise RuntimeError("Unreachable parse loop state.")


async def run() -> dict[str, Any]:
    args = parse_args()
    configure_terminal_logging(args.log_level)
    logger.info("Running paper_chain_mvp with log level %s", args.log_level)
    config_manager = ConfigManager(args)
    model_settings = config_manager.get_model_settings("validation")
    handler = ModelHandlerFactory.build(model_settings)
    logger.info("Initialized model handler for model: %s", handler.model_settings.model)

    paper_content = json.loads(Path(args.attachment).read_text(encoding="utf-8"))

    system_prompt = (
        "You are an academic document structure filter. Your task is to process a list of extracted section headings from a research paper and return only the sections that should be retained for downstream technical claim extraction."
        "RULES:"
        "1. EXCLUDE standard meta-sections that typically do not contain novel technical claims or core methodology. Always remove: Related Work / Literature Review, Limitations, Conclusion, Introduction, Acknowledgments, References, Appendices, and Supplementary Material."
        "2. RETAIN all other sections, especially those covering methods, algorithms, system design, experiments, results, theoretical analysis, or applications."
        "3. If a section combines excluded and retained topics (e.g., 'Discussion & Limitations'), keep it. When in doubt, prefer retention over exclusion."
        "4. Preserve the original sequential order of the sections."
        "OUTPUT FORMAT:"
        "- Return ONLY a valid JSON array of strings. No markdown, no explanations, no extra text, no wrapper object."
        "- Example: ['Methodology', 'Experimental Setup', 'Results']"
        "- If no sections are retained, return an empty array: []"
    )

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step1_prompt = (
        "Below is the list of section headings extracted from the target paper:"
        f"{[section['name'] for section in paper_content]}"
        "Filter the list according to the rules and return ONLY a JSON array of strings containing the retained section names in their original order."
    )

    raw, step1_output = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_1",
        user_prompt=step1_prompt,
        max_retries=args.max_retries,
    )

    print(step1_output)

    list_of_claims = []

    system_prompt = (
        "You are an expert technical reviewer for academic papers. Your task is to extract atomic, verifiable factual claims from a given paper section."
        "DEFINITION:"
        "A 'verifiable claim' is a specific, self-contained technical fact that can be confirmed or refuted by examining the paper's methodology, experiments, or explicitly stated configurations."
        "RULES:"
        "1. GRANULARITY: Extract exactly ONE technical fact per claim. Split compound statements joined by 'and', 'while', or semicolons into separate claims."
        "2. INCLUDE: Architecture, pipelines, methods, datasets, models, training procedures, infrastructure, experimental setups, and specific numerical configurations."
        "3. EXCLUDE: Motivations, vague descriptions, references to prior work, subjective quality evaluations, and final performance outcomes (e.g., 'achieved 95% accuracy' or 'outperformed baseline by 2%')."
        "4. LANGUAGE: Preserve the original language of the paper for `claim` and `original_text`. Do not translate."
        "5. ATOMICITY: If a sentence contains multiple independent facts, output separate claim objects."
        "OUTPUT SCHEMA (each object must include exactly these fields):"
        "- 'claim': string, restated as a clear, self-contained sentence"
        "- 'original_text': string, the exact, complete sentence from the paper that contains the claim. Preserve it verbatim; do not truncate, summarize, or modify any part of the original text."
        "- 'category': string, EXACTLY one of: ['dataset', 'model_architecture', 'training_procedure', 'evaluation_metric', 'numerical_result', 'baseline_comparison', 'data_preprocessing', 'infrastructure']"
        "- 'value': string or null, specific parameter, name, or number if present (e.g., '0.001', 'BERT-base', 'ImageNet'), else null"
        "- 'verifiability': string, EXACTLY one of:"
        "    'high' = Exact values, configs, or explicit references stated in text"
        "    'medium' = Procedural description provided, but exact parameters omitted"
        "    'low' = High-level statement without reproducible details"
        "GOOD EXAMPLES:"
        "- claim: 'The model uses a pre-trained BERT-base-uncased encoder without fine-tuning.'"
        "  original_text: 'Используется компактная предварительно обученная модель BERT-base-uncased без дообучения'"
        "  category: 'model_architecture'"
        "  value: 'BERT-base-uncased'"
        "  verifiability: 'high'"
        "- claim: 'Clustering uses k-means with automatic k selection via silhouette score optimization.'"
        "  original_text: 'Применяется кластеризация методом k-means с автоматическим выбором k по silhouette score'"
        "  category: 'training_procedure'"
        "  value: 'k-means, silhouette score'"
        "  verifiability: 'medium'"
        "BAD EXAMPLES (DO NOT EXTRACT):"
        "- Vague: 'A deep learning model was used for feature extraction.'"
        "- Motivation: 'We chose this approach because it is computationally efficient.'"
        "- Prior work: 'Transformers were introduced by Vaswani et al. in 2017.'"
        "- Performance/Result: 'Our method achieved an F1-score of 0.88, outperforming the baseline by 1.67%.'"
        "OUTPUT FORMAT:"
        "- Return ONLY a valid JSON array of objects."
        "- DO NOT use markdown formatting, code blocks, explanations, or extra text."
        "- Start directly with `[` and end with `]`."
        "- If no claims match the criteria, return exactly: []"
    )

    for heading in step1_output:
        history: list[Any] = [SystemMessage(content=system_prompt)]
        matching_sections = [section.get("text", "") for section in paper_content if section.get("name") == heading]
        section_text = "\n\n".join(text for text in matching_sections if text)
        if not section_text:
            continue

        step2_prompt = (
            "Analyze the following paper section and extract all verifiable factual claims:\n"
            f"{section_text}\n"
            "Return ONLY the JSON array as specified in the system instructions."
        )

        raw, step2_output = await _step_with_repair(
            handler=handler,
            history=history,
            step_name="step_2",
            user_prompt=step2_prompt,
            max_retries=args.max_retries,
        )

        list_of_claims.append(raw)

    print(list_of_claims)

    system_prompt = (
        "You are a technical claim deduplication and conflict resolution engine. Your task is to process a list of extracted report claims, merge duplicates, and flag factual contradictions."
        "CORE RULES:"
        "1. MERGE DUPLICATES: If multiple claims refer to the exact same technical fact, consolidate them into a single entry. Keep the most specific, detailed, or precise version. Discard redundant or vaguer duplicates."
        "2. FLAG CONTRADICTIONS: If claims disagree on a specific factual attribute (e.g., different learning rates, conflicting dataset splits, mismatched metric scores), DO NOT merge them. Retain both separate claims and set 'contradiction': true for each conflicting entry."
        "3. PRESERVE PLAUSIBILITY: Do not filter out claims simply because they seem incorrect, implausible, or poorly phrased. Accuracy verification occurs in a later step."
        "4. STRICT SCHEMA COMPLIANCE: Every output object must contain exactly these fields:"
        "- 'claim': string, restated as a clear, self-contained sentence"
        "- 'original_text': string, the exact, complete sentence from the paper that contains the claim. Preserve it verbatim; do not truncate, summarize, or modify any part of the original text."
        "- 'category': string, EXACTLY one of: ['dataset', 'model_architecture', 'training_procedure', 'evaluation_metric', 'numerical_result', 'baseline_comparison', 'data_preprocessing', 'infrastructure']"
        "- 'value': string or null, specific parameter, name, or number if present (e.g., '0.001', 'BERT-base', 'ImageNet'), else null"
        "- 'verifiability': string, EXACTLY one of:"
        "    'high' = Exact values, configs, or explicit references stated in text"
        "    'medium' = Procedural description provided, but exact parameters omitted"
        "    'low' = High-level statement without reproducible details"
        " - 'contradiction': boolean (true if conflicting with another retained claim; false or omitted otherwise)"
        "OUTPUT FORMAT:"
        "- Return ONLY a valid JSON array of objects matching the schema above."
        "- No markdown wrappers, no explanations, no preamble."
        "- If the input is empty or fully deduplicated to zero claims, return []."
    )

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step3_prompt = (
        "Below is the JSON array of claims extracted from the report sections. Apply the deduplication and contradiction rules."
        f"{list_of_claims}"
        "Return ONLY the final processed JSON array."
    )

    final_raw, step3_output = await _step_with_repair(
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
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved result to %s", output_path)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    logger.debug("Final raw response:\n%s", final_raw)
    return result


if __name__ == "__main__":
    asyncio.run(run())

# CLAIM
