import asyncio
import multiprocessing

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.codebase.docstring_generation.docgen import DocGen
from osa_tool.operations.codebase.docstring_generation.osa_treesitter import OSA_TreeSitter
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class DocstringsGenerator:
    def __init__(
        self,
        config_manager: ConfigManager,
        ignore_list: list[str],
    ) -> None:
        self.config_manager = config_manager
        self.ignore_list = ignore_list

        self.sem = asyncio.Semaphore(100)
        self.workers = multiprocessing.cpu_count()

        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = parse_folder_name(self.repo_url)

        self.dg = DocGen(self.config_manager)
        self.ts = OSA_TreeSitter(self.repo_path, self.ignore_list)

        self.events: list[OperationEvent] = []

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
            rate_limit = self.config_manager.get_model_settings("docstrings").rate_limit

            res = self.ts.analyze_directory(self.ts.cwd)
            self._emit(EventKind.ANALYZED, target="codebase_analysis")

            # getting the project source code and start generating docstrings
            source_code = await self.dg._get_project_source_code(res, self.sem)

            # first stage
            # generate for functions and methods first
            fn_generated = await self.dg._generate_docstrings_for_items(
                res,
                docstring_type=("functions", "methods"),
                rate_limit=rate_limit,
            )
            self._emit(EventKind.GENERATED, target="functions", data={"type": "docstrings"})
            self._emit(EventKind.GENERATED, target="methods", data={"type": "docstrings"})

            fn_augmented = self.dg._run_in_executor(
                res,
                source_code,
                generated_docstrings=fn_generated,
                n_workers=self.workers,
            )

            await self.dg._write_augmented_code(res, fn_augmented, self.sem)
            self._emit(EventKind.WRITTEN, target="functions_methods_docstrings")

            # re-analyze project after docstrings writing
            res = self.ts.analyze_directory(self.ts.cwd)
            source_code = await self.dg._get_project_source_code(res, self.sem)

            # then generate description for classes based on filled methods docstrings
            cl_generated = await self.dg._generate_docstrings_for_items(
                res,
                docstring_type="classes",
                rate_limit=rate_limit,
            )
            self._emit(EventKind.GENERATED, target="classes", data={"type": "docstrings"})

            cl_augmented = self.dg._run_in_executor(
                res,
                source_code,
                generated_docstrings=cl_generated,
                n_workers=self.workers,
            )

            await self.dg._write_augmented_code(res, cl_augmented, self.sem)
            self._emit(EventKind.WRITTEN, target="classes_docstrings")

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
            self._emit(EventKind.UPDATED, target="all_docstrings", data={"source": "main_idea"})

            # augment the source code and persist it
            augmented_after_idea = self.dg._run_in_executor(
                res,
                source_code,
                generated_after_idea,
                self.workers,
            )

            await self.dg._write_augmented_code(
                res,
                augmented_after_idea,
                self.sem,
            )
            self._emit(EventKind.WRITTEN, target="all_docstrings_after_main_idea")

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
            return {
                "result": "Docstrings successfully generated",
                "events": self.events,
            }
        except Exception as e:
            self.dg._purge_temp_files(self.repo_path)
            logger.error(
                "Error while generating codebase documentation: %s",
                repr(e),
                exc_info=True,
            )
            self._emit(EventKind.FAILED, target="docstrings", data={"error": repr(e)})

            return {
                "result": None,
                "events": self.events,
            }

    def _emit(self, kind: EventKind, target: str, data: dict = None):
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
