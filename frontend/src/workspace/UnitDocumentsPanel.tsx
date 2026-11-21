import React, { useEffect, useState } from "react";
import {
  listUnitDocumentsApi,
  retrieveUnitChunksApi,
  uploadUnitDocumentApi,
} from "../api/client";
import { AuthHeadersInput } from "../api/client";
import {
  DocumentCategory,
  RetrievedChunkResult,
  UploadedDocumentSummary,
} from "../types/documents";

interface Props {
  auth: AuthHeadersInput;
  unitId: string;
}

export const UnitDocumentsPanel: React.FC<Props> = ({ auth, unitId }) => {
  const activeUnit = unitId.trim() || "general";
  const [docs, setDocs] = useState<UploadedDocumentSummary[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [category, setCategory] = useState<DocumentCategory>("lecture_notes");
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<RetrievedChunkResult[]>([]);

  useEffect(() => {
    listUnitDocumentsApi(auth, activeUnit)
      .then(setDocs)
      .catch(() => {});
  }, [auth.accessToken, auth.devUserId, activeUnit]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setUploading(true);
    setErrorMsg(null);
    try {
      const created = await uploadUnitDocumentApi(auth, {
        unitId: activeUnit,
        file: selectedFile,
        title: docTitle.trim() || undefined,
        category,
      });
      setDocs((prev) => [...prev, created]);
      setSelectedFile(null);
      setDocTitle("");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setErrorMsg(null);
    try {
      const res = await retrieveUnitChunksApi(auth, activeUnit, query.trim());
      setMatches(res.results);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Retrieval failed.");
    }
  };

  return (
    <section aria-label="Unit Study Materials">
      <h2>Unit Study Materials ({activeUnit})</h2>
      <p>
        Upload lecture notes or optional past papers. Scanned image-only PDFs are not supported yet
        until OCR is implemented.
      </p>

      <form onSubmit={handleUpload}>
        <label>
          Document Title (optional)
          <input
            value={docTitle}
            onChange={(e) => setDocTitle(e.target.value)}
            placeholder="Optional title"
          />
        </label>
        <label>
          Type
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as DocumentCategory)}
          >
            <option value="lecture_notes">Lecture Notes</option>
            <option value="past_paper">Past Paper (Optional)</option>
            <option value="other">Other</option>
          </select>
        </label>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={!selectedFile || uploading}>
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      </form>

      {errorMsg && <p role="alert">{errorMsg}</p>}

      <ul>
        {docs.map((d) => (
          <li key={d.document_id}>
            <strong>{d.title}</strong> [{d.category}] — {d.page_count} pages, {d.chunk_count} chunks
          </li>
        ))}
      </ul>

      <form onSubmit={handleSearch}>
        <label>
          Search Unit Notes & Past Papers
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search key concept..."
          />
        </label>
        <button type="submit">Retrieve Passages</button>
      </form>

      <ul>
        {matches.map((m) => (
          <li key={m.chunk_id}>
            <p>{m.content}</p>
            <small>
              Source: {m.source.document_title} ({m.source.category}), Page {m.source.page_number},
              Chunk #{m.source.chunk_index}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
};
