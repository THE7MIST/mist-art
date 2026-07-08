import io
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator

from app.database.repository import repository


class SourceResolutionError(RuntimeError):
    pass


class SourceResolver:
    @contextmanager
    def open(self, source_ref: str) -> Iterator[BinaryIO]:
        if source_ref.startswith("evidence://"):
            evidence_id = source_ref.removeprefix("evidence://")
            evidence = repository.get_evidence(evidence_id)
            if evidence is None:
                raise SourceResolutionError(f"Evidence {evidence_id} not found")
            with Path(evidence["storage_path"]).open("rb") as handle:
                yield handle
            return

        if source_ref.startswith("zip://"):
            evidence_id, member_name = self._parse_zip_ref(source_ref)
            evidence = repository.get_evidence(evidence_id)
            if evidence is None:
                raise SourceResolutionError(f"Evidence {evidence_id} not found")
            with zipfile.ZipFile(evidence["storage_path"]) as archive:
                with archive.open(member_name) as member:
                    yield member
            return

        if source_ref.startswith("recovered://"):
            path = Path(source_ref.removeprefix("recovered://"))
            with path.open("rb") as handle:
                yield handle
            return

        raise SourceResolutionError(f"Unsupported source reference: {source_ref}")

    def read_sample(self, source_ref: str, limit: int = 65536) -> bytes:
        with self.open(source_ref) as handle:
            return handle.read(limit)

    def copy_to(self, source_ref: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.open(source_ref) as source, destination.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)

    def _parse_zip_ref(self, source_ref: str) -> tuple[str, str]:
        remainder = source_ref.removeprefix("zip://")
        if "/" not in remainder:
            raise SourceResolutionError("ZIP source reference is missing member path")
        evidence_id, member_name = remainder.split("/", 1)
        return evidence_id, member_name


source_resolver = SourceResolver()


def bytes_to_seekable(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)
