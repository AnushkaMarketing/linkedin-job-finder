import {
  ArrowRight,
  MapPin,
  BookmarkSimple,
  ShieldCheck,
} from "@phosphor-icons/react";

import type { Ranked } from "./types";
import { pct, salary, Tag } from "./shared";
export function JobCard({
  row: r,
  open,
  save,
}: {
  row: Ranked;
  open: () => void;
  save: () => void;
}) {
  return (
    <article className="job-card">
      <div className="job-top">
        <span className="company-avatar">
          {r.job.company.slice(0, 2).toUpperCase()}
        </span>
        <div className="job-title">
          <small>{r.job.company}</small>
          <h3>
            <button onClick={open}>{r.job.title}</button>
          </h3>
        </div>
        <button
          className={"icon save " + (r.job.state === "saved" ? "saved" : "")}
          aria-label={
            r.job.state === "saved"
              ? "Unsave " + r.job.title
              : "Save " + r.job.title
          }
          onClick={save}
        >
          <BookmarkSimple
            size={21}
            weight={r.job.state === "saved" ? "fill" : "regular"}
          />
        </button>
      </div>
      <div className="job-meta">
        <span>
          <MapPin size={14} />
          {r.job.location || "Location not stated"}
        </span>
        <span>{r.job.work_mode}</span>
        <span>{salary(r.job.salary)}</span>
      </div>
      <div className="job-insights">
        <div className="fit-score">
          <strong>
            {pct(r.cv_fit)}
            <small>{r.cv_fit === null ? "" : "%"}</small>
          </strong>
          <span>
            CV fit<small>{r.coverage}% evidence coverage</small>
          </span>
        </div>
        <div className="match-reason">
          {r.strengths[0] ||
            r.related[0] ||
            "Open the evidence breakdown before deciding."}
          <small>
            {r.distance_km !== null
              ? `${r.distance_km} km · ${r.location_status}`
              : r.location_status}
          </small>
        </div>
      </div>
      <div className="job-bottom">
        <Tag tone={r.verification.status === "Verified" ? "green" : ""}>
          <ShieldCheck size={13} />
          {r.verification.status}
        </Tag>
        <span className="source-label">{r.job.source}</span>
        <button className="text-button" onClick={open}>
          View evidence <ArrowRight size={16} />
        </button>
      </div>
    </article>
  );
}
