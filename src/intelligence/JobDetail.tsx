import { TeachEngine } from "./IntelligencePanel";

import {
  Check,
  BookmarkSimple,
  DownloadSimple,
  CaretDown,
} from "@phosphor-icons/react";

import type { Ranked, JobState } from "./types";
import { pct, date, salary, Link, Tag, Modal } from "./shared";
export function JobDetail({
  row: r,
  close,
  state,
  busy,
  demo,
  searchId,
}: {
  row: Ranked;
  close: () => void;
  state: (s: JobState) => void;
  busy: boolean;
  demo: boolean;
  searchId: string;
}) {
  return (
    <Modal wide title="The evidence behind the match" close={close}>
      <div className="detail-heading">
        <span className="eyebrow">{r.job.company}</span>
        <h2>{r.job.title}</h2>
        <p>
          {r.job.location || "Location unknown"} · {r.job.work_mode} ·{" "}
          {salary(r.job.salary)}
        </p>
        <div className="chips">
          <Tag tone="green">CV fit {pct(r.cv_fit)}%</Tag>
          <Tag>Preferences {pct(r.preference_fit)}%</Tag>
          <Tag>{r.coverage}% CV evidence coverage</Tag>
          <Tag>Priority {r.priority}/100</Tag>
        </div>
      </div>
      <div className="detail-actions">
        <button
          className="secondary"
          disabled={busy}
          onClick={() => state(r.job.state === "saved" ? "new" : "saved")}
        >
          <BookmarkSimple />
          {r.job.state === "saved" ? "Unsave" : "Save role"}
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => state("applied")}
        >
          Mark applied
        </button>
        <button
          className="text-button"
          disabled={busy}
          onClick={() => state("ignored")}
        >
          Ignore
        </button>
        {!demo && r.job.application_url && (
          <Link href={r.job.application_url}>Open application</Link>
        )}
      </div>
      <TeachEngine row={r} searchId={searchId} demo={demo} />
      {r.intelligence && (
        <details className="detail-section" open>
          <summary>
            Requirement reasoning <CaretDown />
          </summary>
          <div className="requirement-grid">
            {r.intelligence.requirements.map((g, i) => (
              <div className="requirement-row" key={i}>
                <div>
                  <strong>
                    {g.skills.join(g.operator === "any" ? " or " : ", ")}
                  </strong>
                  <small>
                    {g.importance} ·{" "}
                    {g.operator === "any"
                      ? "one alternative needed"
                      : "explicit skill"}{" "}
                    · {g.relationship}
                  </small>
                </div>
                <span className="requirement-value">{g.score}%</span>
                <blockquote>{g.evidence}</blockquote>
              </div>
            ))}
          </div>
          {r.intelligence.flags.map((f) => (
            <p className="warning-text" key={f}>
              {f}
            </p>
          ))}
          {r.intelligence.priority_cap_reason && (
            <p className="warning-text">
              Priority capped at {r.intelligence.priority_cap}:{" "}
              {r.intelligence.priority_cap_reason}.
            </p>
          )}
          <h3>Questions worth asking</h3>
          <ul>
            {r.intelligence.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
          <small>
            Feedback adjustment:{" "}
            {r.intelligence.priority_adjustment > 0 ? "+" : ""}
            {r.intelligence.priority_adjustment} priority points.{" "}
            {r.intelligence.feedback_labels || 0} eligible labels.
          </small>
        </details>
      )}
      <div className="detail-grid">
        <section>
          <h3>Why it fits</h3>
          <ul className="evidence-list">
            {r.strengths.map((s) => (
              <li key={s}>
                <Check size={16} />
                {s}
              </li>
            ))}
            {!r.strengths.length && (
              <li>No exact strengths established from the available fields.</li>
            )}
          </ul>
          <h3>Related experience</h3>
          <ul>
            {r.related.map((s) => (
              <li key={s}>{s}</li>
            ))}
            {!r.related.length && (
              <li>No partial skill relationships found.</li>
            )}
          </ul>
          <h3>Gaps to consider</h3>
          <ul>
            {r.gaps.map((s) => (
              <li key={s}>{s}</li>
            ))}
            {!r.gaps.length && (
              <li>
                No detected skill gaps. This does not confirm every
                qualification.
              </li>
            )}
          </ul>
          <h3>Application preparation</h3>
          <ul>
            {r.readiness.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>
        <section className="evidence-panel">
          <h3>Listing evidence</h3>
          <Tag>{r.verification.status}</Tag>
          <p>{r.verification.note}</p>
          {r.verification.checks.map((c, i) => (
            <div className="verification-check" key={i}>
              <strong>{c.check}</strong>
              <p>{c.status}</p>
              {c.source && <Link href={c.source}>Inspect source</Link>}
            </div>
          ))}
          <h3>Location</h3>
          <p>
            {r.distance_km !== null ? `${r.distance_km} km · ` : ""}
            {r.location_status}
          </p>
          <small>
            {r.job.coordinates?.source || "Office coordinates not supplied"}
          </small>
          <p>{r.job.remote_restrictions}</p>
          <h3>Freshness</h3>
          <p>
            Collected {date(r.job.collected_at)}
            <br />
            Posted {r.job.posted_date || "not stated"}
          </p>
          <small>Collection time is not the vacancy posting date.</small>
        </section>
      </div>
      <details open className="detail-section">
        <summary>
          Score breakdown <CaretDown />
        </summary>
        <p>
          CV fit is a weighted mean of known factors. Priority = 65%
          coverage-adjusted CV fit + 20% preference fit + 15% verification
          confidence. It is not a hiring probability.
        </p>
        <div className="factor-list">
          {r.factors.map((f) => (
            <div key={f.name}>
              <div>
                <strong>{f.name}</strong>
                <small>{f.explanation}</small>
              </div>
              <div className="score-track">
                <span style={{ width: `${f.score ?? 0}%` }} />
              </div>
              <strong>{pct(f.score)}</strong>
              <small>w {f.weight}</small>
            </div>
          ))}
        </div>
      </details>
      <details className="detail-section">
        <summary>
          Requirements & signals <CaretDown />
        </summary>
        {Object.entries(r.analysis).map(
          ([k, v]) =>
            v.length > 0 && (
              <section key={k}>
                <h3>{k.replaceAll("_", " ")}</h3>
                <ul>
                  {v.map((a, i) => (
                    <li key={i}>
                      {typeof a === "string"
                        ? a
                        : `${a.signal} · inferred from “${a.evidence}”`}
                    </li>
                  ))}
                </ul>
              </section>
            ),
        )}
      </details>
      {r.llm_advice && (
        <section className="detail-section">
          <h3>Optional AI reading</h3>
          <Tag>{r.llm_advice.kind}</Tag>
          <p>{r.llm_advice.summary}</p>
          {r.llm_advice.evidence_quotes.map((q) => (
            <blockquote key={q}>{q}</blockquote>
          ))}
          <ul>
            {r.llm_advice.questions_to_ask.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      )}
      <details className="detail-section">
        <summary>
          Company information <CaretDown />
        </summary>
        {Object.entries(r.verification.company_information || {}).length ? (
          Object.entries(r.verification.company_information || {}).map(
            ([key, info]) => (
              <div className="verification-check" key={key}>
                <strong>{key.replaceAll("_", " ")}</strong>
                <p>
                  {typeof info.value === "string"
                    ? info.value
                    : JSON.stringify(info.value)}
                </p>
                <small>{info.kind}</small>
                <br />
                <Link href={info.source}>Published source</Link>
              </div>
            ),
          )
        ) : (
          <p>
            No attributed company details were established. Industry, size,
            headquarters and reputation remain unknown.
          </p>
        )}
      </details>
      <details className="detail-section">
        <summary>
          Original description & provenance <CaretDown />
        </summary>
        <p className="description-text">
          {r.job.description || "No description supplied"}
        </p>
        <div className="chips">
          {r.job.source_url && (
            <Link href={r.job.source_url}>{r.job.source}</Link>
          )}
          {r.job.company_url && (
            <Link href={r.job.company_url}>Company website</Link>
          )}
        </div>
        {Object.entries(r.job.evidence).map(([k, e]) => (
          <p key={k}>
            <strong>{k}</strong> · {e.kind} · {e.source}
            {e.note ? ` · ${e.note}` : ""}
          </p>
        ))}
      </details>
      <button
        className="text-button"
        onClick={() => {
          const url = URL.createObjectURL(
            new Blob([JSON.stringify(r, null, 2)], {
              type: "application/json",
            }),
          );
          const a = document.createElement("a");
          a.href = url;
          a.download = "job-evidence.json";
          a.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }}
      >
        <DownloadSimple size={18} />
        Export this evidence
      </button>
    </Modal>
  );
}
