from osa_tool.core.models.task import TaskStatus
from osa_tool.scheduler.plan import EXCLUDED_TASK, Plan


def test_plan_initializes_tasks_from_truthy_flags():
    # Arrange
    generated = {"readme": True, "docstring": False, "organize": True}

    # Act
    plan = Plan(generated)

    # Assert
    assert set(plan.tasks.keys()) == {"readme", "organize"}
    assert all(s == TaskStatus.PENDING for s in plan.tasks.values())


def test_record_result_normalizes_dict():
    # Arrange
    plan = Plan({"readme": True})

    # Act
    plan.record_result("readme", {"result": {"file": "x"}, "events": [{"k": 1}]})

    # Assert
    assert "Readme" in plan.results
    assert plan.results["Readme"]["result"] == {"file": "x"}
    assert plan.results["Readme"]["events"] == [{"k": 1}]


def test_mark_done_updates_status():
    # Arrange
    plan = Plan({"readme": True})

    # Act
    plan.mark_done("readme")

    # Assert
    assert plan.tasks["readme"] == TaskStatus.COMPLETED


def test_list_for_report_skips_excluded_keys():
    # Arrange
    plan = Plan({"readme": True, "attachment": True})
    plan.mark_done("readme")
    plan.mark_failed("attachment")

    # Act
    rows = plan.list_for_report

    # Assert
    assert "attachment" in EXCLUDED_TASK
    names = [r[0] for r in rows]
    assert "Readme" in names
    assert not any("Attachment" == n for n in names)
