const steps = [
  "Question",
  "Objective",
  "Theory",
  "Procedure",
  "FTK",
  "Autopsy",
  "TSK",
  "Evidence",
  "Reasoning",
  "Report"
];

export function Pipeline() {
  return (
    <div className="pipeline" aria-label="Investigation pipeline">
      {steps.map((step) => (
        <div className="pipeline-step" key={step}>
          {step}
        </div>
      ))}
    </div>
  );
}
