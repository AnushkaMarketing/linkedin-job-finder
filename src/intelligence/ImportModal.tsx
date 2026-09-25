import { useState } from "react";
import { ArrowUpRight, Plus } from "@phosphor-icons/react";
import { api } from "./api";

import { Field, Modal } from "./shared";
export function ImportModal({
  close,
  done,
}: {
  close: () => void;
  done: () => void;
  report: (s: string) => void;
}) {
  const [url, setUrl] = useState(""),
    [title, setTitle] = useState(""),
    [company, setCompany] = useState(""),
    [desc, setDesc] = useState(""),
    [location, setLocation] = useState(""),
    [mode, setMode] = useState("unknown"),
    [office, setOffice] = useState(""),
    [lat, setLat] = useState(""),
    [lon, setLon] = useState(""),
    [companyUrl, setCompanyUrl] = useState(""),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState("");
  async function submit(automatic = false) {
    setBusy(true);
    setErr("");
    try {
      if (automatic) await api("/jobs/import-url", "POST", { url });
      else {
        if ((lat === "") !== (lon === ""))
          throw new Error(
            "Enter both office latitude and longitude, or leave both blank.",
          );
        await api("/jobs/import", "POST", {
          title,
          company,
          description: desc,
          location,
          work_mode: mode,
          application_url: url,
          source_url: url,
          company_url: companyUrl,
          coordinates:
            lat !== "" && lon !== ""
              ? {
                  latitude: Number(lat),
                  longitude: Number(lon),
                  precision: office === "confirmed" ? "office" : "city",
                  source: "User supplied; confirm against employer address",
                }
              : null,
        });
      }
      done();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Bring a job into your research" close={close}>
      <p>
        Import a public JobPosting page or paste details from a listing you can
        view. It will be matched and checked on your next search.
      </p>
      {err && (
        <p role="alert" className="warning-text">
          {err}
        </p>
      )}
      <Field label="Listing / application URL">
        <input
          type="url"
          placeholder="https://…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </Field>
      <button
        className="secondary"
        disabled={busy || !url}
        onClick={() => submit(true)}
      >
        {busy ? "Working…" : "Read public job page"}
        <ArrowUpRight />
      </button>
      <div className="divider">or enter the details yourself</div>
      <div className="field-pair">
        <Field label="Job title *">
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Company *">
          <input value={company} onChange={(e) => setCompany(e.target.value)} />
        </Field>
      </div>
      <Field label="Full description & requirements">
        <textarea
          rows={6}
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
        />
      </Field>
      <div className="field-pair">
        <Field label="Location / office address">
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </Field>
        <Field label="Work mode">
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="unknown">Unknown</option>
            <option value="on-site">On-site</option>
            <option value="hybrid">Hybrid</option>
            <option value="remote">Remote</option>
          </select>
        </Field>
      </div>
      <Field
        label="Company careers URL (optional)"
        hint="A separate company JobPosting page can corroborate the employer and title."
      >
        <input
          type="url"
          value={companyUrl}
          onChange={(e) => setCompanyUrl(e.target.value)}
        />
      </Field>
      <details className="advanced">
        <summary>
          Office coordinates <Plus />
        </summary>
        <div className="field-pair">
          <Field label="Latitude">
            <input
              type="number"
              min={-90}
              max={90}
              step="any"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
            />
          </Field>
          <Field label="Longitude">
            <input
              type="number"
              min={-180}
              max={180}
              step="any"
              value={lon}
              onChange={(e) => setLon(e.target.value)}
            />
          </Field>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={office === "confirmed"}
            onChange={(e) => setOffice(e.target.checked ? "confirmed" : "")}
          />
          <span>
            These coordinates are the actual reporting office, not a city
            centre.
          </span>
        </label>
      </details>
      <div className="modal-actions">
        <button className="secondary" onClick={close}>
          Cancel
        </button>
        <button
          className="primary"
          disabled={busy || !title.trim() || !company.trim()}
          onClick={() => submit()}
        >
          Import listing <Plus />
        </button>
      </div>
    </Modal>
  );
}
