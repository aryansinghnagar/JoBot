import asyncio
import logging
from typing import Dict, List, Optional
from jobot.models.domain import Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskGraphEngine:
    """
    Task Graph & Worker Claiming Engine (Layer B/C).
    Manages task dependency resolution, atomic worker claiming, and execution lifecycle.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task

    def get_executable_tasks(self) -> List[Task]:
        """Return tasks that are PENDING and have all dependencies COMPLETED."""
        executable = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                deps_satisfied = all(
                    dep_id in self.tasks and self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_satisfied:
                    executable.append(task)
        return executable

    def claim_task(self, task_id: str, worker_id: str) -> bool:
        """Atomically claim a task for a worker."""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.RUNNING
            task.assigned_worker = worker_id
            logger.info(f"Task {task_id} claimed by worker {worker_id}")
            return True
        return False

    def mark_completed(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED

    def mark_failed(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
