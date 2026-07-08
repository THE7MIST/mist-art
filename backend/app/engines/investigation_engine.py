from pathlib import Path

from app.database.repository import repository
from app.engines.question_planner import question_planner
from app.engines.verification import verification_engine
from app.schemas import AnswerResult, EvidenceItem
from app.services.plugin_manager import plugin_manager


class InvestigationEngine:
    def analyze_case(
        self,
        case_id: str,
        question_ids: list[str] | None = None,
        learning_mode: bool = True,
        include_gui_steps: bool = True,
        include_cli_verification: bool = True,
    ) -> list[AnswerResult]:
        evidence = repository.list_evidence(case_id)
        questions = repository.get_questions(case_id, question_ids)
        answers: list[AnswerResult] = []
        for question in questions:
            plan = question_planner.plan(question["text"])
            repository.update_question(question["id"], intent=plan.intent, status="analyzing")
            selected_plugins = plugin_manager.select_for_intent(plan.intent)
            answer, confidence, evidence_items, raw = self._answer_from_available_evidence(plan.intent, evidence)
            reasoning = self._reasoning(plan.intent, answer, evidence_items, learning_mode)
            report_paragraph = (
                f"For question '{question['text']}', MIST identified the objective as: {plan.objective} "
                f"The current answer is: {answer} Confidence is {round(confidence * 100)}%. "
                f"This conclusion is based on {len(evidence_items)} structured evidence item(s) and should be "
                "cross-verified using the listed GUI and CLI procedures before final testimony or submission."
            )
            result = AnswerResult(
                question_id=question["id"],
                question=question["text"],
                objective=plan.objective,
                theory=plan.theory,
                answer=answer,
                confidence=confidence,
                required_artifacts=plan.required_artifacts,
                selected_plugins=[manifest.id for manifest in selected_plugins],
                procedure=plan.procedure,
                gui_workflows=verification_engine.gui_workflows(plan.intent) if include_gui_steps else [],
                cli_verification=verification_engine.cli_steps(plan.intent) if include_cli_verification else [],
                evidence=evidence_items,
                reasoning=reasoning,
                alternative_verification=[
                    "Repeat the analysis with a second forensic tool and compare artifact paths, hashes, and timestamps.",
                    "Export the relevant file or metadata record and calculate an independent SHA-256 hash.",
                    "Preserve screenshots of tool views showing the same values reported here.",
                ],
                expected_output=self._expected_output(plan.intent),
                report_paragraph=report_paragraph,
                raw=raw,
            )
            repository.update_question(question["id"], status="answered")
            answers.append(result)
        return answers

    def _answer_from_available_evidence(self, intent: str, evidence: list[dict]) -> tuple[str, float, list[EvidenceItem], dict]:
        evidence_items = [
            EvidenceItem(
                label="Evidence SHA-256",
                value=item["sha256"],
                source=item["filename"],
                confidence=1.0,
            )
            for item in evidence
        ]
        type_items = [
            EvidenceItem(
                label="Detected type",
                value=item["detected_type"],
                source=item["filename"],
                confidence=0.8 if item["detected_type"] != "unknown" else 0.3,
            )
            for item in evidence
        ]
        all_items = evidence_items + type_items

        if intent == "zip_count":
            zip_candidates = [
                item
                for item in evidence
                if item["detected_type"] == "zip" or Path(item["filename"]).suffix.lower() == ".zip"
            ]
            for item in zip_candidates:
                all_items.append(
                    EvidenceItem(
                        label="ZIP candidate",
                        value=item["filename"],
                        source=item["storage_path"],
                        confidence=0.95 if item["detected_type"] == "zip" else 0.7,
                    )
                )
            if zip_candidates:
                return (
                    f"{len(zip_candidates)} ZIP file(s) identified among uploaded evidence containers.",
                    0.82,
                    all_items,
                    {"zip_candidate_ids": [item["id"] for item in zip_candidates], "mode": "container-level-scan"},
                )
            return (
                "No ZIP files were confirmed at the uploaded-container level. Recursive disk-image scanning is queued for the disk plugin.",
                0.45 if evidence else 0.2,
                all_items,
                {"zip_candidate_ids": [], "mode": "planning-only"},
            )

        disk_like = [item for item in evidence if item["detected_type"] in {"raw-disk-image", "ewf", "virtual-disk"}]
        memory_like = [item for item in evidence if item["detected_type"] == "memory-image"]

        if intent == "filesystem":
            if disk_like:
                names = ", ".join(item["filename"] for item in disk_like)
                return (
                    f"Filesystem determination requires fsstat/mmls execution against {names}; disk evidence is present and ready.",
                    0.55,
                    all_items,
                    {"disk_evidence_ids": [item["id"] for item in disk_like]},
                )
            return ("No disk image evidence is available for filesystem determination.", 0.2, all_items, {})

        if intent == "memory":
            if memory_like:
                return (
                    "Memory image evidence is present; Volatility plugins should be executed in the isolated worker.",
                    0.55,
                    all_items,
                    {"memory_evidence_ids": [item["id"] for item in memory_like]},
                )
            return ("No memory image evidence is available for volatile analysis.", 0.2, all_items, {})

        if not evidence:
            return (
                "No evidence has been uploaded yet. MIST generated the investigation plan and verification workflow only.",
                0.15,
                all_items,
                {"mode": "planning-only"},
            )
        return (
            "Evidence is uploaded and classified. The selected plugins define the next artifact-specific extraction steps.",
            0.5,
            all_items,
            {"evidence_count": len(evidence), "mode": "scaffold-analysis"},
        )

    def _reasoning(self, intent: str, answer: str, evidence_items: list[EvidenceItem], learning_mode: bool) -> str:
        evidence_summary = f"{len(evidence_items)} evidence facts were available."
        if intent == "zip_count":
            base = (
                "ZIP identification requires two checks: filename/extension discovery and content signature validation. "
                "The current MVP validates uploaded containers directly and prepares recursive disk-image verification "
                "through Sleuth Kit for embedded files."
            )
        elif intent == "filesystem":
            base = (
                "Filesystem answers should be accepted only when partition metadata and filesystem statistics agree. "
                "The generated workflow asks FTK, Autopsy, and fsstat to verify the same volume."
            )
        else:
            base = (
                "The answer is derived from structured evidence classification plus the plugin plan. "
                "Final confidence increases when independent tools report the same artifact values."
            )
        if learning_mode:
            return f"{base} {evidence_summary} Answer produced: {answer}"
        return f"{base} {evidence_summary}"

    def _expected_output(self, intent: str) -> str:
        outputs = {
            "zip_count": "A count of ZIP files with path, size, hash, signature status, and tool source.",
            "filesystem": "Filesystem type, partition offset, block size, and corroborating tool output.",
            "deleted_files": "Deleted file records separated by recoverable and metadata-only status.",
            "mac_time": "Created, Modified, Accessed, and Changed timestamps with timezone context.",
            "user_profile": "Correlated user identifiers, profile paths, documents, browser activity, and confidence.",
            "timeline": "Chronological event list with source artifact and normalized timestamp.",
            "memory": "Volatility plugin output for processes, network, DLLs, handles, or malware indicators.",
        }
        return outputs.get(intent, "A structured answer with evidence, verification steps, and report-ready reasoning.")


investigation_engine = InvestigationEngine()
