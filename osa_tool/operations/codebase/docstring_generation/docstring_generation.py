import asyncio
import multiprocessing

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.core.models.task import TaskStatus
from osa_tool.operations.codebase.docstring_generation.docgen import DocGen
from osa_tool.operations.codebase.docstring_generation.core.osa_parser import OSA_TreeSitter
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import resolve_repo_path


class DocstringsGenerator:
    def __init__(
        self,
        config_manager: ConfigManager,
        ignore_list: list[str],
        incremental: bool = False,
        target_files: list[str] = None,
    ) -> None:
        self.config_manager = config_manager
        self.ignore_list = ignore_list
        self.incremental = incremental
        self.target_files = target_files

        self.sem = asyncio.Semaphore(100)
        self.workers = multiprocessing.cpu_count()

        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = str(resolve_repo_path(self.repo_url))

        self.dg = DocGen(self.config_manager)
        self.ts = OSA_TreeSitter(
            self.repo_path,
            self.ignore_list,
            target_files=self.target_files,
        )
        self.events = self.dg.events

    def run(self) -> dict:
        """
        Sync entrypoint without explicit loop.
        Safe for both sync and async callers.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._run_async(), loop)
            return future.result()
        else:
            return asyncio.run(self._run_async())

    async def _run_async(self) -> dict:
        try:
            res = self.ts.analyze_directory(self.ts.cwd)
            self._emit(EventKind.ANALYZED, target="codebase_analysis")
            if not any(file.get("structure") for file in res.values()):
                return self._outcome()
            rate_limit = self.config_manager.get_model_settings("docstring").rate_limit
            await self.dg.classify_model_size()

            # getting the project source code and start generating docstrings
            source_code = await self.dg._get_project_source_code(res, self.sem)

            # first stage
            # generate for functions and methods first
            fn_generated = await self.dg._generate_docstrings_for_items(
                res,
                docstring_type=("functions", "methods"),
                rate_limit=rate_limit,
            )
            if not await self._persist(res, source_code, fn_generated):
                return self._outcome()

            # re-analyze project after docstrings writing
            res = self.ts.analyze_directory(self.ts.cwd)
            source_code = await self.dg._get_project_source_code(res, self.sem)

            # then generate description for classes based on filled methods docstrings
            cl_generated = await self.dg._generate_docstrings_for_items(
                res,
                docstring_type="classes",
                rate_limit=rate_limit,
            )
            if not await self._persist(res, source_code, cl_generated):
                return self._outcome()

            if self.incremental:
                logger.info("Incremental mode active. Skipping main idea generation and full codebase update.")
                return self._outcome("Docstrings successfully generated (incremental)")

            if any(event.kind == EventKind.FAILED for event in self.events) and not self._has_written_docstrings():
                return self._outcome()

            # generate the main idea
            await self.dg.generate_the_main_idea(res)
            self._emit(EventKind.SET, target="main_idea", data={"purpose": "improve_docstrings"})

            # re-analyze project and read augmented source code
            res = self.ts.analyze_directory(self.ts.cwd)
            source_code = await self.dg._get_project_source_code(res, self.sem)

            # update docstrings for project based on generated main idea
            generated_after_idea = await self.dg._generate_docstrings_for_items(
                res,
                docstring_type=("functions", "methods", "classes"),
                rate_limit=rate_limit,
            )
            if not await self._persist(res, source_code, generated_after_idea):
                return self._outcome()

            modules_summaries = await self.dg.summarize_submodules(res, rate_limit)
            self.dg.generate_documentation_mkdocs(
                self.repo_path,
                res,
                modules_summaries,
            )
            self._emit(EventKind.SET, target="mkdocs")
            self.dg.create_mkdocs_git_workflow(
                self.repo_url,
                self.repo_path,
            )
            self._emit(EventKind.SET, target="mkdocs_workflow")
            return self._outcome("Docstrings successfully generated")
        except Exception as e:
            logger.error(
                "Error while generating codebase documentation: %s",
                repr(e),
                exc_info=True,
            )
            self._emit(EventKind.FAILED, target="docstrings", data={"error": repr(e)})
            try:
                self.dg._purge_temp_files(self.repo_path)
            except Exception as cleanup_error:
                self._emit(EventKind.FAILED, target="docstrings cleanup", data={"error": str(cleanup_error)})
            return self._outcome()

    async def _persist(self, structure: dict, source_code: dict, generated: dict) -> bool:
        if not any(any(items.values()) for items in generated.values()):
            return True

        augmented = self.dg._run_in_executor(structure, source_code, generated, self.workers)
        writes = await self.dg._write_augmented_code(structure, augmented, self.sem, source_code=source_code)
        for file, error in writes:
            if error is None:
                self._emit(EventKind.WRITTEN, target=file)
            else:
                self._emit(EventKind.FAILED, target=file, data={"error": str(error)})
        return all(error is None for _, error in writes)

    def _has_written_docstrings(self) -> bool:
        return any(event.kind == EventKind.WRITTEN for event in self.events)

    def _outcome(self, success_message: str | None = None) -> dict:
        has_output = self._has_written_docstrings() or any(
            event.kind == EventKind.SET and event.target == "mkdocs" for event in self.events
        )
        failures = [event for event in self.events if event.kind == EventKind.FAILED]
        if failures:
            status = TaskStatus.PARTIAL if has_output else TaskStatus.FAILED
            result = "Some docstring outputs were saved" if has_output else {"error": failures[0].data["error"]}
        elif has_output:
            status = TaskStatus.COMPLETED
            result = success_message
        else:
            status = TaskStatus.SKIPPED
            self._emit(EventKind.SKIPPED, target="docstrings", data={"reason": "no_changes_required"})
            result = None
        return {"status": status, "result": result, "events": self.events}

    def _emit(self, kind: EventKind, target: str, data: dict = None):
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
