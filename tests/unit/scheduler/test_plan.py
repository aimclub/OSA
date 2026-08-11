from osa_tool.core.models.task import TaskStatus
from osa_tool.scheduler.plan import EXCLUDED_TASK, Plan


def test_plan_initializes_tasks_from_truthy_flags():
    generated = {"readme": True, "docstring": False, "organize": True}

    plan = Plan(generated)

    assert set(plan.tasks.keys()) == {"readme", "organize"}
    assert all(status == TaskStatus.PENDING for status in plan.tasks.values())


def test_record_result_normalizes_dict():
    plan = Plan({"readme": True})

    plan.record_result("readme", {"result": {"file": "x"}, "events": [{"k": 1}]})

    assert "Readme" in plan.results
    assert plan.results["Readme"]["result"] == {"file": "x"}
    assert plan.results["Readme"]["events"] == [{"k": 1}]


def test_mark_done_updates_status():
    plan = Plan({"readme": True})

    plan.mark_done("readme")

    assert plan.tasks["readme"] == TaskStatus.COMPLETED


def test_list_for_report_skips_excluded_keys():
    plan = Plan({"readme": True, "attachment": True})
    plan.mark_done("readme")
    plan.mark_failed("attachment")

    rows = plan.list_for_report

    assert "attachment" in EXCLUDED_TASK
    names = [row[0] for row in rows]
    assert "Readme" in names
    assert "Attachment" not in names


def test_empty_notebook_report_is_tracked_as_repository_wide_task():
    plan = Plan({"notebook_report": [], "convert_notebooks": [], "readme": False})

    assert plan.tasks == {"notebook_report": TaskStatus.PENDING}
