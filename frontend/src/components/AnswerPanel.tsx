import type { AnswerResult } from "../types/mist";
import { StatusPill } from "./StatusPill";

interface AnswerPanelProps {
  answer: AnswerResult;
}

export function AnswerPanel({ answer }: AnswerPanelProps) {
  return (
    <article className="answer-panel">
      <div className="answer-header">
        <div>
          <p className="eyebrow">Question</p>
          <h3>{answer.question}</h3>
        </div>
        <StatusPill label={`${Math.round(answer.confidence * 100)}% confidence`} tone="ready" />
      </div>

      <div className="answer-grid">
        <section>
          <h4>Answer</h4>
          <p>{answer.answer}</p>
        </section>
        <section>
          <h4>Objective</h4>
          <p>{answer.objective}</p>
        </section>
        <section>
          <h4>Evidence</h4>
          {answer.evidence.length === 0 ? (
            <p>No evidence facts available yet.</p>
          ) : (
            <ul className="compact-list">
              {answer.evidence.slice(0, 6).map((item, index) => (
                <li key={`${item.label}-${index}`}>
                  <strong>{item.label}:</strong> {item.value}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <h4>CLI Verification</h4>
          <ul className="compact-list">
            {answer.cli_verification.map((step) => (
              <li key={step.method}>
                <strong>{step.method}:</strong> <code>{step.command ?? "manual"}</code>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <details>
        <summary>Report paragraph and reproduction steps</summary>
        <p>{answer.report_paragraph}</p>
        {answer.gui_workflows.map((workflow) => (
          <div className="workflow-block" key={workflow.tool}>
            <h4>{workflow.tool}</h4>
            <ol>
              {workflow.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="muted">Expected: {workflow.expected_observation}</p>
          </div>
        ))}
      </details>
    </article>
  );
}
