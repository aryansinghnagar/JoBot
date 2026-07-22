import pytest
from jobaut.models.domain import Task, TaskStatus
from jobaut.task_graph import TaskGraphEngine


def test_task_graph_engine_dependency_resolution():
    engine = TaskGraphEngine()

    t1 = Task(task_id="t1", goal_id="g1", title="Parse Job Posting")
    t2 = Task(task_id="t2", goal_id="g1", title="Fill Form", dependencies=["t1"])

    engine.add_task(t1)
    engine.add_task(t2)

    # Initially only t1 is executable
    exec_tasks = engine.get_executable_tasks()
    assert len(exec_tasks) == 1
    assert exec_tasks[0].task_id == "t1"

    # Claim & complete t1
    claimed = engine.claim_task("t1", "worker_1")
    assert claimed is True
    engine.mark_completed("t1")

    # Now t2 becomes executable
    exec_tasks_after = engine.get_executable_tasks()
    assert len(exec_tasks_after) == 1
    assert exec_tasks_after[0].task_id == "t2"
