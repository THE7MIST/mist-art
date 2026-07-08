import json
import re
from pathlib import Path

from app.database.repository import repository
from app.schemas import PreviewResponse
from app.services.source_resolver import source_resolver


PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{4,}")


class PreviewEngine:
    def preview(self, file_id: str, max_bytes: int = 65536) -> PreviewResponse:
        file_record = repository.get_catalog_file(file_id)
        if file_record is None:
            raise KeyError(file_id)

        category = file_record["category"]
        extension = file_record["extension"]
        sample = source_resolver.read_sample(file_record["source_ref"], max_bytes)
        metadata = {
            "path": file_record["path"],
            "size": file_record["size"],
            "category": category,
            "extension": extension,
            "hashes": file_record["hashes"],
            "flags": file_record["flags"],
            "timeline": file_record["timeline"],
        }

        if category == "Images":
            return PreviewResponse(
                file_id=file_id,
                filename=file_record["filename"],
                preview_type="image",
                metadata=metadata,
                hex=self._hex(sample[:512]),
                strings=self._strings(sample),
                download_path=file_record["source_ref"],
            )
        if category == "PDF":
            return PreviewResponse(
                file_id=file_id,
                filename=file_record["filename"],
                preview_type="pdf",
                metadata=metadata,
                content=self._decode_text(sample),
                hex=self._hex(sample[:512]),
                strings=self._strings(sample),
                download_path=file_record["source_ref"],
            )
        if category == "Office Documents":
            return PreviewResponse(
                file_id=file_id,
                filename=file_record["filename"],
                preview_type="office",
                metadata=metadata,
                content="Office document preview is metadata-first in the MVP. Full rendering can be added through LibreOffice or python-docx/openpyxl extraction.",
                hex=self._hex(sample[:512]),
                strings=self._strings(sample),
            )
        if self._is_text_like(extension, sample):
            content = self._decode_text(sample)
            pretty = self._pretty_if_json(extension, content)
            return PreviewResponse(
                file_id=file_id,
                filename=file_record["filename"],
                preview_type="text",
                content=pretty,
                encoding="utf-8-or-fallback",
                metadata=metadata,
                strings=self._strings(sample),
            )
        return PreviewResponse(
            file_id=file_id,
            filename=file_record["filename"],
            preview_type="hex" if sample else "unsupported",
            metadata=metadata,
            hex=self._hex(sample),
            strings=self._strings(sample),
        )

    def _is_text_like(self, extension: str, sample: bytes) -> bool:
        if extension in {"txt", "csv", "html", "htm", "xml", "json", "log", "md", "py", "js", "ts", "ps1", "sh", "ini", "cfg", "yaml", "yml"}:
            return True
        if not sample:
            return False
        control = sum(1 for byte in sample[:1024] if byte < 9 or 13 < byte < 32)
        return control < 8

    def _decode_text(self, sample: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return sample.decode(encoding)
            except UnicodeDecodeError:
                continue
        return sample.decode("utf-8", errors="replace")

    def _pretty_if_json(self, extension: str, content: str) -> str:
        if extension != "json":
            return content
        try:
            return json.dumps(json.loads(content), indent=2)
        except json.JSONDecodeError:
            return content

    def _hex(self, sample: bytes) -> str:
        lines: list[str] = []
        for offset in range(0, len(sample), 16):
            chunk = sample[offset : offset + 16]
            hex_bytes = " ".join(f"{byte:02x}" for byte in chunk)
            ascii_text = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
            lines.append(f"{offset:08x}  {hex_bytes:<47}  {ascii_text}")
        return "\n".join(lines)

    def _strings(self, sample: bytes) -> list[str]:
        return [match.group(0).decode("ascii", errors="ignore") for match in PRINTABLE_RE.finditer(sample)][:80]


preview_engine = PreviewEngine()
