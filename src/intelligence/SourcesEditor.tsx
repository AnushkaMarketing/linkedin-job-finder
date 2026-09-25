import { useState } from "react";
import { Check, Plus, LinkSimple, Buildings } from "@phosphor-icons/react";

import type { Sources } from "./types";
import { split, Link, Field, Tag } from "./shared";
export function SourcesEditor({
  initial,
  count,
  save,
  busy,
  importJob,
}: {
  initial: Sources;
  count: number;
  save: (s: Sources) => void;
  busy: boolean;
  importJob: () => void;
}) {
  const [s, setS] = useState(initial);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">KNOW WHERE YOUR RESULTS COME FROM</div>
          <h1>Sources with a paper trail.</h1>
          <p>
            Connect public employer boards, permitted careers pages, or jobs you
            find yourself.
          </p>
        </div>
        <button className="primary" disabled={busy} onClick={() => save(s)}>
          Save sources <Check />
        </button>
      </div>
      <div className="source-grid">
        <section className="panel">
          <div className="section-title">
            <h2>Employer boards</h2>
            <Buildings size={24} />
          </div>
          <p>
            Enter the board IDs from employers you want to research. These
            connectors search those employers, not the entire web.
          </p>
          <Field
            label="Greenhouse board IDs"
            hint="Up to 8 IDs, comma separated. From boards.greenhouse.io/BOARD"
          >
            <textarea
              rows={3}
              placeholder="Employer board IDs"
              value={s.greenhouse.join(", ")}
              onChange={(e) =>
                setS({ ...s, greenhouse: split(e.target.value) })
              }
            />
          </Field>
          <Field
            label="Lever site IDs"
            hint="Up to 8 IDs. From jobs.lever.co/SITE"
          >
            <textarea
              rows={3}
              value={s.lever.join(", ")}
              onChange={(e) => setS({ ...s, lever: split(e.target.value) })}
            />
          </Field>
          <Tag>Public API · cached 15 minutes</Tag>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Company job pages</h2>
            <LinkSimple size={24} />
          </div>
          <p>
            Public pages containing JobPosting structured data. JavaScript-only
            pages may require manual import. Robots rules are respected.
          </p>
          <Field
            label="Job page URLs"
            hint="One URL per line, up to 8. Use individual job pages where possible."
          >
            <textarea
              rows={7}
              placeholder="https://company.example/careers/role"
              value={s.career_pages.join("\n")}
              onChange={(e) =>
                setS({
                  ...s,
                  career_pages: e.target.value
                    .split("\n")
                    .map((x) => x.trim())
                    .filter(Boolean),
                })
              }
            />
          </Field>
          <Tag>Public HTTP(S) only</Tag>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Remotive</h2>
            <label className="switch-label">
              <input
                type="checkbox"
                checked={s.remotive}
                onChange={(e) => setS({ ...s, remotive: e.target.checked })}
              />{" "}
              Enable
            </label>
          </div>
          <p>
            Remote roles with location restrictions. The public feed is delayed
            by 24 hours and cached here for 6 hours. Source links and
            attribution stay with every result.
          </p>
          <Link href="https://remotive.com">Visit Remotive</Link>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Manual imports</h2>
            <label className="switch-label">
              <input
                type="checkbox"
                checked={s.manual}
                onChange={(e) => setS({ ...s, manual: e.target.checked })}
              />{" "}
              Enable
            </label>
          </div>
          <p>
            {count} listing{count !== 1 ? "s" : ""} stored locally. Paste jobs
            you can legitimately view, including LinkedIn listings, and add an
            office address or coordinates if available.
          </p>
          <button className="secondary" onClick={importJob}>
            <Plus />
            Import a listing
          </button>
        </section>
        <section className="panel linkedin-panel">
          <div>
            <h2>LinkedIn, with clear boundaries.</h2>
            <p>
              No authorized browser bridge is connected. This app creates
              role-specific search links with recency filters. Open LinkedIn
              normally and import a listing you can view.
            </p>
          </div>
          <Tag>Browser not connected</Tag>
        </section>
      </div>
    </>
  );
}
