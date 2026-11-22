import React, { useState } from "react";
import type { WorkspaceProfile } from "../types/quiz";

interface Props {
  profile: WorkspaceProfile;
  onSave: (next: WorkspaceProfile) => Promise<void>;
}

export const WorkspacePanel: React.FC<Props> = ({ profile, onSave }) => {
  const [institution, setInstitution] = useState(profile.institution ?? "");
  const [programme, setProgramme] = useState(profile.programme ?? "");
  const [semester, setSemester] = useState(profile.semester ?? "");
  const [unitInput, setUnitInput] = useState("");
  const [units, setUnits] = useState<string[]>(profile.units ?? []);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const addUnit = () => {
    const trimmed = unitInput.trim();
    if (!trimmed || units.includes(trimmed)) return;
    setUnits([...units, trimmed]);
    setUnitInput("");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatusMsg(null);
    try {
      await onSave({
        institution: institution.trim() || null,
        programme: programme.trim() || null,
        semester: semester.trim() || null,
        units,
      });
      setStatusMsg("Workspace saved.");
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : "Could not save workspace.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section aria-label="Private Academic Workspace">
      <h2>Private Workspace (Optional Setup)</h2>
      <p>
        You can start quizzes immediately without selecting an institution or uploading past papers.
      </p>
      <form onSubmit={handleSave}>
        <label>
          Institution (optional)
          <input
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            placeholder="Optional"
          />
        </label>
        <label>
          Programme (optional)
          <input
            value={programme}
            onChange={(e) => setProgramme(e.target.value)}
            placeholder="Optional"
          />
        </label>
        <label>
          Semester (optional)
          <input
            value={semester}
            onChange={(e) => setSemester(e.target.value)}
            placeholder="Optional"
          />
        </label>
        <div>
          <label>
            Academic Unit (optional)
            <input
              value={unitInput}
              onChange={(e) => setUnitInput(e.target.value)}
              placeholder="e.g., Calculus I"
            />
          </label>
          <button type="button" onClick={addUnit}>
            Add Unit
          </button>
        </div>
        <ul>
          {units.map((u) => (
            <li key={u}>{u}</li>
          ))}
        </ul>
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save Workspace"}
        </button>
        {statusMsg && <p role="status">{statusMsg}</p>}
      </form>
    </section>
  );
};
