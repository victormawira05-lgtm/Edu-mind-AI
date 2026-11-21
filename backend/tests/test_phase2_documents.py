import io
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import ContentStream, DictionaryObject, NameObject

from backend import main as backend_main


def _make_pdf_bytes(page_texts: list[str]) -> bytes:
    writer = PdfWriter()
    for text in page_texts:
        writer.add_blank_page(width=200, height=200)
        if text:
            page = writer.pages[-1]
            safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = ContentStream(None, writer)
            stream._data = f"BT /F1 12 Tf 20 100 Td ({safe}) Tj ET".encode("latin-1")
            page[NameObject("/Contents")] = stream
            font_dict = writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/Font"),
                        NameObject("/Subtype"): NameObject("/Type1"),
                        NameObject("/BaseFont"): NameObject("/Helvetica"),
                    }
                )
            )
            page[NameObject("/Resources")] = writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Font"): DictionaryObject(
                            {NameObject("/F1"): font_dict}
                        )
                    }
                )
            )
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def setup_function():
    backend_main.STORE.workspaces.clear()
    backend_main.STORE.quizzes.clear()
    backend_main.STORE.attempts.clear()
    backend_main.STORE.documents.clear()
    backend_main.STORE.chunks.clear()


def test_scanned_pdf_returns_clear_unsupported_message(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    client = TestClient(backend_main.app)

    scanned_bytes = _make_pdf_bytes([""])
    res = client.post(
        "/api/units/general/documents",
        headers={"X-Dev-User-Id": "student-1"},
        files={"file": ("scanned_exam.pdf", io.BytesIO(scanned_bytes), "application/pdf")},
        data={"category": "past_paper"},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "SCANNED_PDF_UNSUPPORTED"
    assert "not supported yet until ocr is implemented" in detail["message"].lower()


def test_multi_document_chunking_source_metadata_and_unit_isolation(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH_BYPASS", "true")
    client = TestClient(backend_main.app)
    headers = {"X-Dev-User-Id": "student-1"}

    notes_pdf = _make_pdf_bytes([
        "Chain rule computes derivatives of composite functions like f(g(x)).",
        "Integration by parts uses integral of u dv equals uv minus integral of v du.",
    ])
    paper_pdf = _make_pdf_bytes([
        "Past exam question: Apply the chain rule to differentiate sin(x^2).",
    ])

    r1 = client.post(
        "/api/units/MAT120/documents",
        headers=headers,
        files={"file": ("calc_notes.pdf", io.BytesIO(notes_pdf), "application/pdf")},
        data={"title": "Calculus Lecture Notes", "category": "lecture_notes"},
    )
    assert r1.status_code == 201
    assert r1.json()["chunk_count"] >= 2

    r2 = client.post(
        "/api/units/MAT120/documents",
        headers=headers,
        files={"file": ("past_2025.pdf", io.BytesIO(paper_pdf), "application/pdf")},
        data={"title": "2025 Past Paper", "category": "past_paper"},
    )
    assert r2.status_code == 201

    ret = client.post(
        "/api/units/MAT120/retrieve",
        headers=headers,
        json={"query": "chain rule", "top_k": 5},
    )
    assert ret.status_code == 200
    results = ret.json()["results"]
    assert len(results) >= 2
    sources = {item["source"]["document_title"] for item in results}
    assert "Calculus Lecture Notes" in sources
    assert "2025 Past Paper" in sources
    for item in results:
        assert item["source"]["unit_id"] == "MAT120"
        assert item["source"]["page_number"] >= 1

    other_ret = client.post(
        "/api/units/MAT120/retrieve",
        headers={"X-Dev-User-Id": "student-other"},
        json={"query": "chain rule", "top_k": 5},
    )
    assert other_ret.status_code == 200
    assert other_ret.json()["results"] == []
