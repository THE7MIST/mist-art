import { FileArchive, FileImage, FileText, ShieldAlert, Trash2, Unlock, Zap } from "lucide-react";

import type { EvidenceCatalog } from "../types/mist";
import { StatusPill } from "./StatusPill";

interface CatalogDashboardProps {
  catalog: EvidenceCatalog | null;
  onFilter: (filter: string) => void;
}

const cards = [
  { key: "total_files", label: "Total Files", filter: "all", icon: FileText },
  { key: "deleted_files", label: "Deleted Files", filter: "deleted", icon: Trash2 },
  { key: "recovered_files", label: "Recovered Files", filter: "recovered", icon: Unlock },
  { key: "images", label: "Images", filter: "Images", icon: FileImage },
  { key: "pdf_documents", label: "PDF Documents", filter: "PDF", icon: FileText },
  { key: "zip_archives", label: "ZIP Archives", filter: "zip", icon: FileArchive },
  { key: "encrypted_files", label: "Encrypted Files", filter: "encrypted", icon: ShieldAlert },
  { key: "interesting_files", label: "Interesting Files", filter: "interesting", icon: Zap }
];

export function CatalogDashboard({ catalog, onFilter }: CatalogDashboardProps) {
  if (!catalog) {
    return (
      <section className="panel">
        <div className="section-heading">
          <h2>Automatic Evidence Catalog</h2>
          <StatusPill label="not indexed" tone="neutral" />
        </div>
        <p className="muted">Start analysis or build the catalog to enumerate evidence, classify artifacts, detect deleted files, and generate recovery reports.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>Automatic Evidence Catalog</h2>
          <p className="muted">Generated {new Date(catalog.generated_at).toLocaleString()}</p>
        </div>
        <StatusPill label={catalog.status} tone="ready" />
      </div>

      <div className="catalog-summary">
        <pre>{catalog.ai_summary}</pre>
        <div className="general-info">
          <span>Evidence</span>
          <strong>{catalog.general_info.evidence_filename}</strong>
          <span>Format</span>
          <strong>{catalog.general_info.evidence_format}</strong>
          <span>SHA-256</span>
          <code>{catalog.general_info.hashes.sha256?.slice(0, 24) ?? "pending"}...</code>
          <span>Verification</span>
          <strong>{catalog.general_info.verification_status}</strong>
        </div>
      </div>

      {catalog.warnings.length > 0 && (
        <div className="warning-list">
          {catalog.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}

      <div className="catalog-card-grid">
        {cards.map(({ key, label, filter, icon: Icon }) => (
          <button className="catalog-card" key={key} onClick={() => onFilter(filter)} type="button">
            <Icon size={18} />
            <span>{catalog.statistics[key as keyof typeof catalog.statistics]}</span>
            <p>{label}</p>
          </button>
        ))}
      </div>

      <div className="category-grid">
        {catalog.categories.map((category) => (
          <button className="category-chip" key={category.name} onClick={() => onFilter(category.name)} type="button">
            <span>{category.name}</span>
            <strong>{category.count}</strong>
            <small>{formatBytes(category.total_size)}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unit]}`;
}
