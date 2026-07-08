from app.engines.question_planner import question_planner


def test_zip_question_maps_to_zip_count() -> None:
    plan = question_planner.plan("How many ZIP files are present?")

    assert plan.intent == "zip_count"
    assert "File signatures" in plan.required_artifacts


def test_filesystem_question_maps_to_filesystem() -> None:
    plan = question_planner.plan("What is the filesystem?")

    assert plan.intent == "filesystem"
    assert "Partition table" in plan.required_artifacts
