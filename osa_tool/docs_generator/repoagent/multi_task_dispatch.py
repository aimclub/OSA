from __future__ import annotations
import random
import threading
import time
from typing import Any, Callable, Dict, List
from colorama import Fore, Style

class Task:
    """Task class represents a task with a unique identifier, dependencies, and additional information.

This class is a core component of the multi-task dispatch system, which is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates with the TaskManager class to manage and dispatch tasks efficiently.

Args:
    task_id (int): The unique identifier for the task.
    dependencies (List[Task]): A list of tasks that this task depends on.
    extra_info (Any, optional): Additional information associated with the task. Defaults to None.

Returns:
    None

Raises:
    None

Note:
    This class is used in conjunction with the TaskManager class to manage and dispatch tasks. It helps in organizing and tracking the dependencies and additional information required for each task in the documentation generation process."""

    def __init__(self, task_id: int, dependencies: List[Task], extra_info: Any=None):
        """Initializes a Task object.

This method sets up a new Task instance with a unique identifier, a list of dependent tasks, and optional extra information. The Task object is part of a multi-task dispatch system designed to automate the generation and management of documentation for a Git repository.

Args:
    task_id (int): The unique identifier for the task.
    dependencies (List[Task]): A list of Task objects that this task depends on.
    extra_info (Any, optional): Additional information associated with the task. Defaults to None.

Returns:
    None

Raises:
    None

Note:
    The status attribute is initialized to 0, indicating the task is in a default state. This status can be updated as the task progresses through the dispatch system."""
        self.task_id = task_id
        self.extra_info = extra_info
        self.dependencies = dependencies
        self.status = 0

class TaskManager:
    """TaskManager manages a collection of tasks with dependencies and provides methods to add, retrieve, and mark tasks as completed. It ensures thread safety using a lock and is designed to handle tasks in a multi-threaded environment.

Args:
    None

Returns:
    None

Raises:
    None

Note:
    This class is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates with other functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

---

add_task(dependency_task_id: List[int], extra=None) -> int

Adds a new task with the specified dependencies and extra information.

Args:
    dependency_task_id (List[int]): List of task IDs that the new task depends on.
    extra: Additional information for the task. Defaults to None.

Returns:
    int: The ID of the newly added task.

Raises:
    None

Note:
    This method is thread-safe.

---

get_next_task(process_id: int)

Retrieves the next available task for a given process ID.

Args:
    process_id (int): The ID of the process requesting the next task.

Returns:
    Tuple[Task, int]: A tuple containing the next task and its ID, or (None, -1) if no tasks are available.

Raises:
    None

Note:
    This method is thread-safe and prints a message indicating the task retrieval and remaining tasks.

---

mark_completed(task_id: int)

Marks a task as completed and updates the dependencies of other tasks.

Args:
    task_id (int): The ID of the task to mark as completed.

Returns:
    None

Raises:
    None

Note:
    This method is thread-safe and removes the completed task from the task dictionary."""

    def __init__(self):
        """Initializes the TaskManager.

This method sets up the initial state of the TaskManager, including an empty dictionary to store tasks, a threading lock for synchronization, and counters for task and query IDs. The TaskManager is a crucial component of the multi-task dispatch system, which automates the generation and management of documentation for a Git repository.

Args:
    None

Returns:
    None

Raises:
    None

Note:
    This method is called automatically when a TaskManager instance is created. The TaskManager is part of a larger tool designed to streamline the documentation process for software repositories by automating the detection of changes, generation of summaries, and handling of file operations."""
        self.task_dict: Dict[int, Task] = {}
        self.task_lock = threading.Lock()
        self.now_id = 0
        self.query_id = 0

    @property
    def all_success(self) -> bool:
        """Checks if all tasks in the task manager are completed successfully.

This method returns True if the task dictionary is empty, indicating that all tasks have been successfully completed. Otherwise, it returns False.

Returns:
    bool: True if all tasks are completed, False otherwise.

Note:
    This method is part of the multi-task dispatch system, which is designed to enhance user interaction and process management in the documentation generation and management tool."""
        return len(self.task_dict) == 0

    def add_task(self, dependency_task_id: List[int], extra=None) -> int:
        """Adds a new task to the task manager with specified dependencies and extra information.

This method acquires a lock to ensure thread safety, creates a new `Task` object with a unique identifier, and adds it to the task dictionary. The unique identifier is incremented after the task is added.

Args:
    dependency_task_id (List[int]): A list of task IDs that the new task depends on.
    extra (Any, optional): Additional information associated with the task. Defaults to None.

Returns:
    int: The unique identifier of the newly added task.

Raises:
    None

Note:
    This method is used in conjunction with the `Task` class to manage and dispatch tasks in the multi-task dispatch system, which is part of a comprehensive tool for automating the generation and management of documentation for a Git repository."""
        with self.task_lock:
            depend_tasks = [self.task_dict[task_id] for task_id in dependency_task_id if task_id in self.task_dict]
            self.task_dict[self.now_id] = Task(task_id=self.now_id, dependencies=depend_tasks, extra_info=extra)
            self.now_id += 1
            return self.now_id - 1

    def get_next_task(self, process_id: int):
        """Retrieves the next available task for a given process ID.

This method locks the task dictionary, increments the query ID, and checks for tasks that have no dependencies and are in the ready state. If such a task is found, it updates the task's status and returns the task along with its ID. If no such task is found, it returns a tuple containing `None` and `-1`.

Args:
    process_id (int): The ID of the process requesting the next task.

Returns:
    tuple: A tuple containing the next task and its ID if available, otherwise `(None, -1)`.

Raises:
    None

Note:
    This method is thread-safe due to the use of a lock. It is part of a multi-task dispatch system designed to automate the generation and management of documentation for a Git repository, ensuring efficient and accurate task handling."""
        with self.task_lock:
            self.query_id += 1
            for task_id in self.task_dict.keys():
                ready = len(self.task_dict[task_id].dependencies) == 0 and self.task_dict[task_id].status == 0
                if ready:
                    self.task_dict[task_id].status = 1
                    print(f'{Fore.RED}[process {process_id}]{Style.RESET_ALL}: get task({task_id}), remain({len(self.task_dict)})')
                    return (self.task_dict[task_id], task_id)
            return (None, -1)

    def mark_completed(self, task_id: int):
        """Marks a task as completed and updates dependencies.

This method removes the specified task from the task dictionary and updates the dependencies of other tasks that depend on it. It is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate.

Args:
    task_id (int): The ID of the task to mark as completed.

Raises:
    KeyError: If the task_id does not exist in the task dictionary.

Note:
    This method is thread-safe due to the use of a lock."""
        with self.task_lock:
            target_task = self.task_dict[task_id]
            for task in self.task_dict.values():
                if target_task in task.dependencies:
                    task.dependencies.remove(target_task)
            self.task_dict.pop(task_id)

def worker(task_manager, process_id: int, handler: Callable):
    """Continuously processes tasks from the task manager until all tasks are marked as successful.

This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories. The tool also includes a chat engine and a multi-task dispatch system to enhance user interaction and process management.

Args:
    task_manager (TaskManager): The task manager object that provides tasks and manages their completion status.
    process_id (int): The unique identifier for the worker process.
    handler (Callable): The function to be called to handle each task. It takes a single argument, `extra_info`, which is additional information associated with the task.

Returns:
    None: This method does not return any value.

Raises:
    None: This method does not raise any exceptions, but it may log errors if they occur.

Note:
    The worker method runs in an infinite loop, checking for new tasks from the task manager and processing them using the provided handler function. It sleeps for 0.5 seconds if no tasks are available. The loop exits when all tasks in the task manager are marked as successful."""
    while True:
        if task_manager.all_success:
            return
        task, task_id = task_manager.get_next_task(process_id)
        if task is None:
            time.sleep(0.5)
            continue
        handler(task.extra_info)
        task_manager.mark_completed(task.task_id)