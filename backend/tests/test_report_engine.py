from app.engines.investigation_engine import investigation_engine
from app.engines.report_engine import report_engine
from app.database.repository import repository


def test_report_contains_forensic_sections() -> None:
    repository.reset()
    case = repository.create_case("Unit Test Case", "tester", None)
    question = repository.add_question(case["id"], "How many ZIP files are present?", "zip_count")

    answers = investigation_engine.analyze_case(case["id"], [question["id"]])
    report = report_engine.create_report(case["id"], answers)
    markdown = report_engine.to_markdown(report)

    assert "### GUI Steps (FTK / Autopsy)" in markdown
    assert "### CLI Verification" in markdown
    assert "### Why This Is The Answer" in markdown
