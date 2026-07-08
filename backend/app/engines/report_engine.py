import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.database.repository import repository
from app.schemas import AnswerResult, InvestigationReport


class ReportEngine:
    def create_report(self, case_id: str, answers: list[AnswerResult]) -> InvestigationReport:
        settings = get_settings()
        case = repository.get_case(case_id)
        if case is None:
            raise KeyError(case_id)

        report_id = str(uuid4())
        generated_at = datetime.now(timezone.utc)
        case_report_dir = settings.report_dir / case_id
        case_report_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = case_report_dir / f"{report_id}.md"
        json_path = case_report_dir / f"{report_id}.json"

        report = InvestigationReport(
            id=report_id,
            case_id=case_id,
            title=f"MIST Artifact Report - {case['name']}",
            generated_at=generated_at,
            answers=answers,
            markdown_path=str(markdown_path),
            json_path=str(json_path),
        )

        markdown_path.write_text(self.to_markdown(report), encoding="utf-8")
        json_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
        repository.save_report(report.model_dump(mode="json"))
        return report

    def to_markdown(self, report: InvestigationReport) -> str:
        lines = [
            f"# {report.title}",
            "",
            f"Generated: {report.generated_at.isoformat()}",
            "",
            "## Executive Summary",
            "",
            f"MIST analyzed {len(report.answers)} investigation question(s). Each answer below includes objective, theory, procedure, evidence, reasoning, GUI reproduction, CLI verification, expected output, and a report paragraph.",
            "",
        ]
        for index, answer in enumerate(report.answers, start=1):
            lines.extend(
                [
                    f"## Question {index}",
                    "",
                    answer.question,
                    "",
                    "### Objective",
                    "",
                    answer.objective,
                    "",
                    "### Theory",
                    "",
                    answer.theory,
                    "",
                    "### Investigation Procedure",
                    "",
                ]
            )
            lines.extend(f"{step_index}. {step}" for step_index, step in enumerate(answer.procedure, start=1))
            lines.extend(["", "### GUI Steps (FTK / Autopsy)", ""])
            for workflow in answer.gui_workflows:
                lines.extend([f"#### {workflow.tool}", ""])
                lines.extend(f"{step_index}. {step}" for step_index, step in enumerate(workflow.steps, start=1))
                lines.extend(["", f"Expected observation: {workflow.expected_observation}", ""])
            lines.extend(["### CLI Verification", ""])
            for step in answer.cli_verification:
                command = f"`{step.command}`" if step.command else "Manual verification"
                lines.extend(
                    [
                        f"- Method: {step.method}",
                        f"- Command: {command}",
                        f"- Expected output: {step.expected_output}",
                        "",
                    ]
                )
            lines.extend(["### Evidence Found", ""])
            if answer.evidence:
                lines.extend(
                    f"- {item.label}: {item.value} (source: {item.source}, confidence: {round(item.confidence * 100)}%)"
                    for item in answer.evidence
                )
            else:
                lines.append("- No evidence facts were available.")
            lines.extend(
                [
                    "",
                    "### Why This Is The Answer",
                    "",
                    answer.reasoning,
                    "",
                    "### Alternative Verification",
                    "",
                ]
            )
            lines.extend(f"- {item}" for item in answer.alternative_verification)
            lines.extend(
                [
                    "",
                    "### Expected Output",
                    "",
                    answer.expected_output,
                    "",
                    "### Answer",
                    "",
                    f"{answer.answer}",
                    "",
                    f"Confidence: {round(answer.confidence * 100)}%",
                    "",
                    "### Report Paragraph",
                    "",
                    answer.report_paragraph,
                    "",
                ]
            )
        return "\n".join(lines)


report_engine = ReportEngine()
