import re
from io import BytesIO

from fastapi import UploadFile


QUESTION_LINE = re.compile(r"^\s*(?:\d+[\).:-]\s*)?(?P<question>.+\?)\s*$")


def extract_questions_from_text(text: str) -> list[str]:
    questions: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = QUESTION_LINE.match(line)
        if match:
            questions.append(match.group("question").strip())
    if questions:
        return questions

    normalized = re.split(r"(?<=[?])\s+", text.strip())
    return [item.strip() for item in normalized if item.strip().endswith("?")]


async def extract_questions_from_upload(upload: UploadFile) -> list[str]:
    content = await upload.read()
    filename = (upload.filename or "").lower()
    if filename.endswith(".pdf") or upload.content_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return extract_questions_from_text(text)
    return extract_questions_from_text(content.decode("utf-8", errors="ignore"))
