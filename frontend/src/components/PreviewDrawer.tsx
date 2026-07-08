import type { PreviewResponse } from "../types/mist";
import { StatusPill } from "./StatusPill";

interface PreviewDrawerProps {
  preview: PreviewResponse | null;
}

export function PreviewDrawer({ preview }: PreviewDrawerProps) {
  if (!preview) {
    return (
      <section className="panel preview-panel">
        <h2>Preview</h2>
        <p className="muted">Select a file to inspect content, strings, metadata, and hex without leaving MIST.</p>
      </section>
    );
  }

  return (
    <section className="panel preview-panel">
      <div className="section-heading">
        <div>
          <h2>Preview</h2>
          <p className="muted">{preview.filename}</p>
        </div>
        <StatusPill label={preview.preview_type} tone="working" />
      </div>

      {preview.content && (
        <div className="preview-block">
          <h3>Content</h3>
          <pre>{preview.content}</pre>
        </div>
      )}

      <div className="preview-block">
        <h3>Metadata</h3>
        <pre>{JSON.stringify(preview.metadata, null, 2)}</pre>
      </div>

      {preview.strings.length > 0 && (
        <div className="preview-block">
          <h3>Strings</h3>
          <pre>{preview.strings.join("\n")}</pre>
        </div>
      )}

      {preview.hex && (
        <div className="preview-block">
          <h3>Hex</h3>
          <pre>{preview.hex}</pre>
        </div>
      )}
    </section>
  );
}
