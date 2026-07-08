from app.engines.investigation_engine import investigation_engine
from app.engines.catalog_engine import catalog_engine
from app.engines.report_engine import report_engine
from app.tasks.celery_app import celery_app


@celery_app.task(name="mist.analyze_case")
def analyze_case_task(case_id: str, question_ids: list[str] | None = None) -> dict:
    if catalog_engine:
        catalog_engine.build_catalog(case_id)
    answers = investigation_engine.analyze_case(case_id=case_id, question_ids=question_ids)
    report = report_engine.create_report(case_id, answers)
    return report.model_dump(mode="json")


@celery_app.task(name="mist.build_catalog")
def build_catalog_task(case_id: str, selected_timezone: str = "UTC") -> dict:
    catalog = catalog_engine.build_catalog(case_id, selected_timezone)
    return catalog.model_dump(mode="json")
