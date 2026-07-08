import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Download, Eye, RotateCcw } from "lucide-react";

import type { CatalogFileRecord } from "../types/mist";
import { StatusPill } from "./StatusPill";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface EvidenceExplorerProps {
  files: CatalogFileRecord[];
  onPreview: (file: CatalogFileRecord) => void;
  onRecover: (file: CatalogFileRecord) => void;
}

const columnHelper = createColumnHelper<CatalogFileRecord>();

export function EvidenceExplorer({ files, onPreview, onRecover }: EvidenceExplorerProps) {
  const table = useReactTable({
    data: files,
    columns: [
      columnHelper.accessor("filename", {
        header: "Filename",
        cell: (info) => <strong>{info.getValue()}</strong>
      }),
      columnHelper.accessor("path", {
        header: "Path",
        cell: (info) => <span className="path-cell">{info.getValue()}</span>
      }),
      columnHelper.accessor("extension", {
        header: "Ext"
      }),
      columnHelper.accessor("category", {
        header: "Category"
      }),
      columnHelper.accessor("size", {
        header: "Size",
        cell: (info) => formatBytes(info.getValue())
      }),
      columnHelper.accessor("deleted", {
        header: "Deleted",
        cell: (info) => (info.getValue() ? <StatusPill label="yes" tone="warn" /> : <span>No</span>)
      }),
      columnHelper.accessor("recovered", {
        header: "Recovered",
        cell: (info) => (info.getValue() ? <StatusPill label="yes" tone="ready" /> : <span>No</span>)
      }),
      columnHelper.accessor("encrypted", {
        header: "Encrypted",
        cell: (info) => (info.getValue() ? <StatusPill label="yes" tone="warn" /> : <span>No</span>)
      }),
      columnHelper.accessor("timeline.modified_time", {
        header: "Modified",
        cell: (info) => (info.getValue() ? new Date(info.getValue() as string).toLocaleString() : "n/a")
      }),
      columnHelper.accessor("hashes.sha256", {
        header: "Hash",
        cell: (info) => <code>{info.getValue()?.slice(0, 12) ?? "pending"}</code>
      }),
      columnHelper.accessor("interest_score", {
        header: "Interest",
        cell: (info) => <strong>{info.getValue()}</strong>
      }),
      columnHelper.display({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="row-actions">
            <button className="icon-button" onClick={() => onPreview(row.original)} title="Preview" type="button">
              <Eye size={15} />
            </button>
            <a
              className="icon-link"
              href={`${API_BASE_URL}/api/cases/${row.original.case_id}/catalog/files/${row.original.id}/download`}
              title="Download"
            >
              <Download size={15} />
            </a>
            <button className="icon-button" onClick={() => onRecover(row.original)} title="Recover" type="button">
              <RotateCcw size={15} />
            </button>
          </div>
        )
      })
    ],
    getCoreRowModel: getCoreRowModel()
  });

  return (
    <div className="evidence-table-wrap">
      <table className="evidence-table">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id}>
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {files.length === 0 && <p className="muted table-empty">No files match the current filter.</p>}
    </div>
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
