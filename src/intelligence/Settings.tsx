import { useState } from "react";
import { Check, Trash } from "@phosphor-icons/react";

import type { LLM } from "./types";
import { Field, Modal } from "./shared";
export function Settings({
  initial,
  close,
  save,
  busy,
  erase,
  error,
}: {
  initial: LLM;
  close: () => void;
  save: (l: LLM) => void;
  busy: boolean;
  erase: () => void;
  error: string;
}) {
  const [l, setL] = useState(initial);
  return (
    <Modal title="Your data. Your controls." close={close}>
      {error && (
        <p className="warning-text" role="alert">
          {error}
        </p>
      )}
      <section>
        <h3>Local storage</h3>
        <p>
          Structured profiles, saved jobs, search history, cached pages and API
          keys are encrypted in the local SQLite database. On Windows, the
          encryption key is protected by your Windows account. This does not
          protect against software already running as you.
        </p>
        <p>
          Raw CV files and pasted text are not saved. Search preferences and
          location queries are sent only to sources you choose. No analytics or
          telemetry.
        </p>
      </section>
      <section className="detail-section">
        <div className="section-title">
          <h3>Optional AI interpretation</h3>
          <label className="switch-label">
            <input
              type="checkbox"
              checked={l.enabled}
              onChange={(e) => setL({ ...l, enabled: e.target.checked })}
            />{" "}
            Enable
          </label>
        </div>
        <p>
          The core matching engine works without a model. An OpenAI-compatible
          provider can add advice for the top 3 jobs. AI cannot set scores or
          verification status.
        </p>
        <Field label="Provider endpoint">
          <input
            value={l.endpoint}
            onChange={(e) => setL({ ...l, endpoint: e.target.value })}
          />
        </Field>
        <div className="field-pair">
          <Field label="Model name">
            <input
              value={l.model}
              onChange={(e) => setL({ ...l, model: e.target.value })}
            />
          </Field>
          <Field
            label="API key"
            hint={
              l.key_saved
                ? "Key saved. Blank keeps it for the same endpoint."
                : "Optional for local models"
            }
          >
            <input
              type="password"
              autoComplete="off"
              value={l.api_key || ""}
              onChange={(e) => setL({ ...l, api_key: e.target.value })}
            />
          </Field>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            checked={l.consent}
            onChange={(e) => setL({ ...l, consent: e.target.checked })}
          />
          <span>
            I allow this configured provider to receive my skills, experience
            years, current role, and the job title and description.
            <small>
              Name, CV document and contact details are excluded. A remote
              provider has its own retention policy.
            </small>
          </span>
        </label>
        <button
          className="primary"
          disabled={busy}
          onClick={() => {
            const { key_saved, ...config } = l;
            save(config);
          }}
        >
          Save settings <Check />
        </button>
      </section>
      <section className="detail-section">
        <h3>Reset this workspace</h3>
        <p>
          Delete all stored records, including search caches and provider
          credentials.
        </p>
        <button className="danger" onClick={erase}>
          <Trash />
          Delete local data
        </button>
      </section>
    </Modal>
  );
}
