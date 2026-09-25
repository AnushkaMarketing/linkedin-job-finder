import { useState } from "react";
import {
  ArrowRight,
  UploadSimple,
  Check,
  ShieldCheck,
} from "@phosphor-icons/react";
import { api } from "./api";
import type { Profile } from "./types";
import { split, number, Field, Tag } from "./shared";
export function ProfileEditor({
  initial,
  save,
  busy,
  report,
}: {
  initial: Profile;
  save: (p: Profile) => void;
  busy: boolean;
  report: (s: string) => void;
}) {
  const [p, setP] = useState(initial),
    [text, setText] = useState(""),
    [extracting, setExtracting] = useState(false);
  const set = (v: Partial<Profile>) => setP({ ...p, ...v });
  async function extract(file?: File) {
    setExtracting(true);
    try {
      if (file) {
        const form = new FormData();
        form.append("file", file);
        setP(await api("/profile/upload", "POST", form));
      } else setP(await api("/profile/extract", "POST", { text }));
      setText("");
    } catch (e) {
      report((e as Error).message);
    } finally {
      setExtracting(false);
    }
  }
  const lists: [keyof Profile, string][] = [
    ["skills", "Core skills"],
    ["technical_skills", "Technical skills"],
    ["soft_skills", "Soft skills"],
    ["preferred_roles", "Preferred roles"],
    ["previous_roles", "Previous roles"],
    ["companies", "Companies"],
    ["industries", "Industries"],
    ["education", "Education"],
    ["certifications", "Certifications"],
    ["projects", "Projects"],
    ["preferred_locations", "Preferred locations"],
    ["work_mode", "Preferred work modes"],
    ["employment_type", "Employment types"],
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">START WITH YOUR STORY</div>
          <h1>Your experience. In focus.</h1>
          <p>
            Extract a CV locally, then review the details that shape your
            matches.
          </p>
        </div>
      </div>
      <div className="profile-layout">
        <section className="panel">
          <h2>Bring your CV</h2>
          <label className="upload-zone">
            <UploadSimple size={30} />
            <strong>
              {extracting ? "Reading your document…" : "Choose a CV"}
            </strong>
            <span>PDF, DOCX or TXT · up to 5 MB</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              disabled={extracting}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) extract(f);
                e.target.value = "";
              }}
            />
          </label>
          <div className="divider">or paste your experience</div>
          <Field label="CV text">
            <textarea
              rows={9}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the text of your CV here. It is parsed locally and not stored as raw text."
            />
          </Field>
          <button
            className="secondary full"
            disabled={extracting || text.trim().length < 30}
            onClick={() => extract()}
          >
            {extracting ? "Extracting…" : "Extract profile"}
            <ArrowRight />
          </button>
          <div className="privacy-note">
            <ShieldCheck size={21} />
            <p>
              No upload to an AI service. Original document bytes are discarded
              after parsing. Scanned PDFs need OCR first.
            </p>
          </div>
        </section>
        <section className="panel profile-fields">
          <div className="section-title">
            <h2>Review & refine</h2>
            <Tag>{p.skills.length} skills</Tag>
          </div>
          {p.warnings.map((w, i) => (
            <p key={i} className="warning-text">
              {w}
            </p>
          ))}
          <div className="field-pair">
            <Field label="Name">
              <input
                value={p.name}
                onChange={(e) => set({ name: e.target.value })}
              />
            </Field>
            <Field label="Experience in years">
              <input
                type="number"
                min={0}
                max={70}
                step="0.1"
                value={p.experience_years ?? ""}
                onChange={(e) =>
                  set({ experience_years: number(e.target.value) })
                }
              />
            </Field>
          </div>
          <div className="field-pair">
            <Field label="Current / most recent role">
              <input
                value={p.current_role}
                onChange={(e) => set({ current_role: e.target.value })}
              />
            </Field>
            <Field label="Seniority">
              <select
                value={p.seniority}
                onChange={(e) => set({ seniority: e.target.value })}
              >
                <option value="">Unknown</option>
                <option value="entry">Entry</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="leadership">Leadership</option>
              </select>
            </Field>
          </div>
          {lists.map(([key, label]) => (
            <Field
              key={key}
              label={label}
              hint={
                p.evidence[key]
                  ? `${p.evidence[key].kind} · ${p.evidence[key].source}`
                  : "Comma or newline separated; leave blank if unknown"
              }
            >
              <textarea
                rows={key === "skills" ? 3 : 2}
                value={(p[key] as string[]).join(", ")}
                onChange={(e) => set({ [key]: split(e.target.value) })}
              />
            </Field>
          ))}
          <div className="field-pair">
            <Field label="Current location">
              <input
                value={p.location}
                onChange={(e) => set({ location: e.target.value })}
              />
            </Field>
            <Field label="Notice period">
              <input
                value={p.notice_period}
                onChange={(e) => set({ notice_period: e.target.value })}
              />
            </Field>
          </div>
          <div className="field-pair">
            <Field label="Expected salary minimum">
              <input
                type="number"
                min={0}
                value={p.salary_expectation.minimum ?? ""}
                onChange={(e) =>
                  set({
                    salary_expectation: {
                      ...p.salary_expectation,
                      minimum: number(e.target.value),
                    },
                  })
                }
              />
            </Field>
            <Field label="Currency / annual">
              <input
                value={p.salary_expectation.currency}
                onChange={(e) =>
                  set({
                    salary_expectation: {
                      ...p.salary_expectation,
                      currency: e.target.value,
                      period: "year",
                    },
                  })
                }
              />
            </Field>
          </div>
          <div className="sticky-save">
            <small>Review before saving. Extraction is an estimate.</small>
            <button
              className="primary"
              disabled={busy || extracting}
              onClick={() => save(p)}
            >
              <Check size={18} />
              Save profile
            </button>
          </div>
        </section>
      </div>
    </>
  );
}
