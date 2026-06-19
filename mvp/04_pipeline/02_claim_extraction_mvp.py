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


def _parse_string_list(raw: str, key: str | None = None) -> list[str]:
    data = JsonProcessor.parse(raw, expected_key=key, expected_type=list)
    cleaned: list[str] = []
    for item in data:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                cleaned.append(stripped)
    return cleaned


def _parse_object_list(raw: str, key: str | None = None) -> list[dict[str, Any]]:
    data = JsonProcessor.parse(raw, expected_key=key, expected_type=list)
    cleaned: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            cleaned.append(item)
    return cleaned


def _extract_selected_section_ids(items: list[dict[str, Any]]) -> list[str]:
    selected_ids: list[str] = []
    for item in items:
        section_id = item.get("section_id")
        if isinstance(section_id, str):
            sid = section_id.strip()
            if sid:
                selected_ids.append(sid)
    return selected_ids


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
    parser: str = "string_list",
) -> tuple[str, list[Any]]:
    logger.info("Starting step: %s", step_name)
    history.append(HumanMessage(content=user_prompt))
    last_raw = ""

    for attempt in range(1, max_retries + 1):
        logger.info("Step '%s' attempt %s/%s", step_name, attempt, max_retries)
        last_raw = await _ainvoke_with_history(handler, history)
        history.append(AIMessage(content=last_raw))
        try:
            if parser == "string_list":
                parsed = _parse_string_list(last_raw)
            elif parser == "object_list":
                parsed = _parse_object_list(last_raw)
            else:
                raise ValueError(f"Unknown parser mode: {parser}")
            logger.info("Step '%s' parse success on attempt %s/%s", step_name, attempt, max_retries)
            return last_raw, parsed
        except Exception as exc:
            logger.warning("Step '%s' parse failed on attempt %s/%s: %s", step_name, attempt, max_retries, exc)
            logger.debug(last_raw)
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

    section_options: list[dict[str, Any]] = []
    for idx, section in enumerate(paper_content, start=1):
        section_options.append(
            {
                "section_id": f"s{idx:03d}",
                "name": section.get("name", ""),
                "heading_meta": section.get("heading_meta", {}),
            }
        )

    logger.debug(section_options)

    system_prompt = (
        "You are an academic document structure filter. Your task is to process a list of extracted section headings from a research paper and return only the sections that should be retained for downstream technical claim extraction."
        "RULES:"
        "1. EXCLUDE standard meta-sections that typically do not contain novel technical claims. Always remove: Abstract, Keywords, Table of Content, Domain Overview, Related Work / Literature Review, Limitations, Conclusion, Introduction, Acknowledgments, References, Appendices, and Supplementary Material."
        "2. HIERARCHICAL EXCLUSION: Exclusion propagates downward. If a parent heading is excluded, ALL of its descendants (sub-sections, sub-sub-sections, etc.) must also be excluded, regardless of their individual titles. Identify parent-child relationships using the 'numbering' field or by parsing numeric prefixes from the 'raw' text (e.g., headings starting with '2.1' or '2.2' are children of '2.'). Exclude the entire subtree."
        "3. RETAIN all other sections, especially those covering methods, algorithms, system design, experiments, results, theoretical analysis, or applications."
        "4. MIXED TOPICS: If a section combines excluded and retained topics (e.g., 'Discussion & Limitations'), keep it. When in doubt, prefer retention over exclusion."
        "5. PRESERVE ORDER: Maintain the original sequential order of the retained sections."
        "OUTPUT FORMAT:"
        "- Return ONLY a valid JSON array of objects. No markdown, no explanations, no extra text."
        "- Each object MUST contain exactly one field: 'section_id'."
        '- Example: [{"section_id":"s003"},{"section_id":"s004"}]'
        "- Use only section_id values from the provided input list."
        "- If no sections are retained, return an empty array: []"
    )

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step1_prompt = (
        "Below is the list of extracted sections. Each item includes section_id, cleaned heading name, and heading_meta.\n"
        f"{json.dumps(section_options, ensure_ascii=False)}\n"
        "Filter the list according to the rules and return ONLY a JSON array of objects with section_id in original order."
    )

    raw, step1_output = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_1",
        user_prompt=step1_prompt,
        max_retries=args.max_retries,
        parser="object_list",
    )

    selected_section_ids = _extract_selected_section_ids(step1_output)
    section_id_to_name: dict[str, str] = {}
    for option in section_options:
        section_id_to_name[str(option["section_id"])] = str(option.get("name", ""))

    selected_section_names = [
        f"{sid} - {section_id_to_name[sid]}" for sid in selected_section_ids if sid in section_id_to_name
    ]
    print(selected_section_names)

    section_id_to_text: dict[str, str] = {}
    section_id_to_heading_name: dict[str, str] = {}
    section_id_to_heading_raw: dict[str, str | None] = {}
    for option, section in zip(section_options, paper_content):
        sid = str(option["section_id"])
        section_id_to_text[sid] = str(section.get("text", ""))
        section_id_to_heading_name[sid] = str(option.get("name", ""))
        heading_meta = option.get("heading_meta", {})
        if isinstance(heading_meta, dict):
            raw_heading = heading_meta.get("raw")
            section_id_to_heading_raw[sid] = str(raw_heading) if raw_heading is not None else None
        else:
            section_id_to_heading_raw[sid] = None

    extracted_claims: list[dict[str, Any]] = []

    system_prompt = (
        "You are an expert technical reviewer for academic papers. Your task is to extract atomic, verifiable factual claims from a given paper section."
        "DEFINITION:"
        "A 'verifiable claim' is a specific, self-contained technical fact that can be confirmed or refuted by examining the paper's methodology, experiments, or explicitly stated configurations."
        "RULES:"
        "1. GRANULARITY: Extract exactly ONE technical fact per claim. Split compound statements joined by 'and', 'while', or semicolons into separate claims."
        "2. INCLUDE: Architecture, pipelines, methods, datasets, models, training procedures, infrastructure, experimental setups, and specific numerical configurations."
        "3. EXCLUDE: Motivations, vague descriptions, figure or table description, references to prior work, subjective quality evaluations, and final performance outcomes (e.g., 'achieved 95% accuracy' or 'outperformed baseline by 2%')."
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
        "- claim: 'Используется BERT-base-uncased без дообучения'"
        "  original_text: 'Используется компактная предварительно обученная модель BERT-base-uncased без дообучения'"
        "  category: 'model_architecture'"
        "  value: 'BERT-base-uncased'"
        "  verifiability: 'high'"
        "- claim: 'Clustering uses k-means with automatic k selection via silhouette score optimization'"
        "  original_text: 'Clustering uses k-means with automatic k selection via silhouette score optimization'"
        "  category: 'training_procedure'"
        "  value: 'k-means, silhouette score'"
        "  verifiability: 'medium'"
        "BAD EXAMPLES (DO NOT EXTRACT):"
        "- Vague: 'A deep learning model was used for feature extraction.'"
        "- Motivation: 'We chose this approach because it is computationally efficient.'"
        "- Prior work: 'Transformers were introduced by Vaswani et al. in 2017.'"
        "- Performance/Result: 'Our method achieved an F1-score of 0.88, outperforming the baseline by 1.67%.'"
        "OUTPUT FORMAT:"
        "- Keep the original language for claim and original_text, do not translate."
        "- Return ONLY a valid JSON array of objects."
        "- DO NOT use markdown formatting, code blocks, explanations, or extra text."
        "- Start directly with `[` and end with `]`."
        "- If no claims match the criteria, return exactly: []"
    )

    for section_id in selected_section_ids:
        history: list[Any] = [SystemMessage(content=system_prompt)]
        section_text = section_id_to_text.get(section_id, "")
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
            parser="object_list",
        )

        section_name = section_id_to_heading_name.get(section_id, "")
        section_heading_raw = section_id_to_heading_raw.get(section_id)
        for claim_obj in step2_output:
            enriched_claim = dict(claim_obj)
            enriched_claim["section_name"] = section_name
            enriched_claim["section_heading_raw"] = section_heading_raw
            extracted_claims.append(enriched_claim)

    print(extracted_claims)

    claims_with_ids: list[dict[str, Any]] = []
    for idx, claim in enumerate(extracted_claims, start=1):
        claim_id = f"c{idx:04d}"
        claim_copy = dict(claim)
        claim_copy["claim_id"] = claim_id
        claims_with_ids.append(claim_copy)

    step3_input_claims: list[dict[str, Any]] = []
    for claim_obj in claims_with_ids:
        claim_text = claim_obj.get("claim")
        if isinstance(claim_text, str) and claim_text.strip():
            step3_input_claims.append({"claim_id": claim_obj["claim_id"], "claim": claim_text.strip()})

    system_prompt = (
        "You are a technical claim deduplication and conflict resolution engine. Your task is to process a list of extracted report claims, merge duplicates, and flag factual contradictions."
        "CORE RULES:"
        "1. INPUT FORMAT: Each item includes only 'claim_id' and 'claim'."
        "2. MERGE DUPLICATES: If multiple claims refer to the exact same technical fact, keep only one item in output, selecting the most specific wording."
        "3. FLAG CONTRADICTIONS: If claims disagree on a specific factual attribute (e.g., different learning rates, conflicting dataset splits, mismatched metric scores), DO NOT merge them. Retain both separate claims and set 'contradiction': true for each conflicting entry."
        "3. PRESERVE PLAUSIBILITY: Do not filter out claims simply because they seem incorrect, implausible, or poorly phrased. Accuracy verification occurs in a later step."
        "4. STRICT SCHEMA COMPLIANCE: Every output object must contain exactly these fields:"
        "- 'claim_id': string, copied from input"
        "- 'claim': string"
        "- 'contradiction': boolean"
        "OUTPUT FORMAT:"
        "- Return ONLY a valid JSON array of objects matching the schema above."
        "- No markdown wrappers, no explanations, no preamble."
        "- If the input is empty or fully deduplicated to zero claims, return []."
    )

    history: list[Any] = [SystemMessage(content=system_prompt)]

    step3_prompt = (
        "Below is the JSON array of claims extracted from the report sections. Apply the deduplication and contradiction rules.\n"
        f"{json.dumps(step3_input_claims, ensure_ascii=False)}\n"
        "Return ONLY the final processed JSON array."
    )

    final_raw, step3_output = await _step_with_repair(
        handler=handler,
        history=history,
        step_name="step_3",
        user_prompt=step3_prompt,
        max_retries=args.max_retries,
        parser="object_list",
    )
    logger.info("Completed all steps.")
    logger.info(final_raw)

    step3_kept_ids: set[str] = set()
    contradiction_by_id: dict[str, bool] = {}
    for item in step3_output:
        claim_id = item.get("claim_id")
        if isinstance(claim_id, str) and claim_id:
            step3_kept_ids.add(claim_id)
            contradiction_by_id[claim_id] = bool(item.get("contradiction", False))

    filtered_claims: list[dict[str, Any]] = []
    for claim in claims_with_ids:
        claim_id = claim.get("claim_id")
        if claim_id in step3_kept_ids:
            enriched_claim = dict(claim)
            enriched_claim["contradiction"] = contradiction_by_id.get(claim_id, False)
            filtered_claims.append(enriched_claim)

    step3_input_count = len(step3_input_claims)
    step3_output_count = len(step3_output)

    result = {
        "result": filtered_claims,
        "step3_selection": step3_output,
        "meta": {
            "source": args.attachment,
            "steps": 3,
            "history_messages": len(history),
            "model": handler.model_settings.model,
            "filtered_claims": len(filtered_claims),
            "step3_input_count": step3_input_count,
            "step3_output_count": step3_output_count,
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
