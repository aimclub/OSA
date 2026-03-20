import asyncio
import multiprocessing

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.codebase.docstring_generation.docgen import DocGen
from osa_tool.operations.codebase.docstring_generation.osa_treesitter import OSA_TreeSitter
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class DocstringsGenerator:
    """
    Generates docstrings for Python codebases using AI and manages the documentation workflow.
    
        This class orchestrates the process of analyzing a codebase, generating docstrings for functions, methods, and classes, and setting up the final MkDocs documentation. It handles asynchronous operations, event tracking, and configuration management.
    
        Attributes:
            config_manager: Manages configuration settings for the application.
            ignore_list: List of file or directory patterns to ignore during processing.
            sem: Semaphore for limiting concurrent asynchronous operations.
            workers: Number of worker processes, typically set to the system's CPU count.
            repo_url: URL of the Git repository, obtained from configuration.
            repo_path: Parsed folder name derived from the repository URL.
            dg: Instance for generating documentation.
            ts: Instance for parsing the repository code structure.
            events: List to store operation events.
    
        Methods:
            __init__: Initializes the generator with configuration, an ignore list, and sets up internal components like the documentation generator and code parser.
            run: Synchronous entry point that safely orchestrates the documentation workflow for both synchronous and asynchronous callers.
            _run_async: Asynchronously executes the core multi-stage workflow: analyzing the project, generating docstrings for functions/methods and then classes, updating them with a project-wide main idea, creating module summaries, and configuring MkDocs with a deployment workflow. Returns a result dictionary and a list of events.
            _emit: Records an operation event (like a progress update or error) by appending it to the internal events list for tracking.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        ignore_list: list[str],
    ) -> None:
        """
        Initializes the DocGenManager instance with configuration and settings.
        
        Args:
            config_manager: Manages configuration settings for the application.
            ignore_list: List of file or directory patterns to ignore during processing.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Manages configuration settings for the application.
            ignore_list (list[str]): List of file or directory patterns to ignore during processing.
            sem (asyncio.Semaphore): Semaphore for limiting concurrent asynchronous operations. The limit is fixed at 100 to control resource usage during async tasks.
            workers (int): Number of worker processes, set to the system's CPU count to maximize parallel processing.
            repo_url (str): URL of the Git repository, obtained from the configuration's git settings.
            repo_path (str): Parsed folder name derived from the repository URL, used as a safe directory name for cloning.
            dg (DocGen): Instance for generating documentation, initialized with the config manager.
            ts (OSA_TreeSitter): Instance for parsing the repository code structure, set up with the repo path and ignore list.
            events (list[OperationEvent]): List to store operation events, initialized as empty.
        """
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
        
        This method provides a unified synchronous interface to run the asynchronous docstring generation workflow. It automatically detects the current execution context and chooses the appropriate strategy to run the underlying async operation (`_run_async`). This allows the method to be called safely from both synchronous code and from within an already running asyncio event loop.
        
        Why:
            The method handles two scenarios to avoid runtime errors:
            1. If called from within a running event loop (e.g., from async code), it schedules the coroutine in a thread-safe manner and waits for the result.
            2. If no loop is running, it creates and runs a new event loop. This dual approach ensures compatibility without requiring the caller to manage loop lifecycle.
        
        Args:
            None.
        
        Returns:
            dict: A dictionary containing the operation result and a list of emitted events. On success, the 'result' key contains a success message and 'events' contains all emitted events. On failure, the 'result' key is None and 'events' contains events up to the point of failure.
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
        """
        Asynchronously orchestrates the entire docstring generation and documentation workflow for a codebase.
                
                This method performs a multi-stage process: it first analyzes the project structure, then generates and writes docstrings for functions and methods. After re-analyzing the project, it generates docstrings for classes. It then generates a main idea for the project and uses it to update all docstrings. Finally, it creates module summaries and sets up MkDocs documentation with a deployment workflow. Events are emitted throughout the process to track progress.
                
                Why:
                    The workflow is staged because generating docstrings for classes benefits from having method docstrings already in place, providing better context. The main idea is generated after class docstrings to incorporate a holistic view of the project, which is then used to refine all docstrings for consistency. Re-analysis after each writing step ensures the parsed structure reflects the updated code.
                
                Args:
                    None.
                
                Returns:
                    dict: A dictionary containing the operation result and a list of emitted events. On success, the 'result' key contains a success message and 'events' contains all emitted events. On failure, the 'result' key is None and 'events' contains events up to the point of failure.
                
                Raises:
                    Exception: Any exception raised during the workflow will be caught, logged, and result in a failure response. Temporary files are purged on failure.
        """
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
        """
        Appends an operation event to the internal events list for tracking and logging purposes.
        
        Args:
            kind: The type of the event (e.g., success, error, info).
            target: The target of the event, typically a file, operation, or component name.
            data: Optional dictionary containing additional event-specific details.
        
        Returns:
            None
        """
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
