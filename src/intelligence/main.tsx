import { useEffect, useState, useRef, useMemo } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  MagnifyingGlass,
  SlidersHorizontal,
  Check,
  X,
  Sun,
  Moon,
  ShieldCheck,
  FileText,
  Clock,
  ArrowClockwise,
  WarningCircle,
  Trash,
  Lightning,
  Stack,
  Target,
  CaretDown,
} from "@phosphor-icons/react";
import "@fontsource-variable/manrope";
import { api } from "./api";
import type { Bootstrap, Profile, Run, Ranked, JobState } from "./types";
import "./styles.css";
import "./studio.css";
import { MotionHero } from "./MotionHero";
import { IntelligencePanel } from "./IntelligencePanel";

import { date, Tag, Link, Modal } from "./shared";
import { PreferencesForm } from "./PreferencesForm";
import { RunStatus } from "./RunStatus";
import { JobCard } from "./JobCard";
import { ProfileEditor } from "./ProfileEditor";
import { SourcesEditor } from "./SourcesEditor";
import { JobDetail } from "./JobDetail";
import { ImportModal } from "./ImportModal";
import { Settings } from "./Settings";
function App() {
  const [data, setData] = useState<Bootstrap | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [tab, setTab] = useState("Research"),
    [modal, setModal] = useState<"import" | "settings" | "delete" | null>(null);
  const [run, setRun] = useState<Run | null>(null),
    [selected, setSelected] = useState<Ranked | null>(null),
    [busy, setBusy] = useState(false);
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [sort, setSort] = useState("priority");
  const [dark, setDark] = useState(
    () => localStorage.getItem("signal-theme") === "dark",
  );
  const searchRef = useRef<HTMLInputElement>(null);
  async function refresh(reset = false) {
    const result = await api<Bootstrap>("/bootstrap");
    setData((previous) => ({
      ...result,
      preferences: reset
        ? result.preferences
        : (previous?.preferences ?? result.preferences),
    }));
    return result;
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("signal-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    function keys(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setTab("Research");
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    }
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(t);
  }, [notice]);
  useEffect(() => {
    if (run?.status !== "running") return;
    let active = true;
    let t: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await api<Run>("/searches/" + run!.id);
        if (!active) return;
        setRun(next);
        if (next.status === "running") t = setTimeout(poll, 1100);
        else refresh().catch(() => {});
      } catch (e) {
        if (active) {
          setError((e as Error).message);
          t = setTimeout(poll, 3000);
        }
      }
    }
    t = setTimeout(poll, 500);
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [run?.id, run?.status]);
  async function act(fn: () => Promise<void>) {
    setError("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function start(demo = false) {
    if (!data) return;
    await act(async () => {
      const prefs = demo
        ? {
            ...data.preferences,
            roles: ["Social Media Manager", "Content Marketing Specialist"],
            location: "Noida · demo",
            origin: {
              latitude: 28.505,
              longitude: 77.41,
              precision: "user",
              source: "Demo origin",
            },
            work_modes: ["on-site", "hybrid", "remote"],
            strict_radius: true,
          }
        : data.preferences;
      setRun(await api<Run>("/searches", "POST", { preferences: prefs, demo }));
      setTab("Research");
      setFilter("all");
      setQuery("");
    });
  }
  async function state(row: Ranked, next: JobState) {
    await act(async () => {
      await api(
        "/jobs/" + encodeURIComponent(row.job.job_id) + "/state",
        "PUT",
        { state: next },
      );
      const update = (r: Ranked) =>
        r.job.job_id === row.job.job_id
          ? { ...r, job: { ...r.job, state: next } }
          : r;
      setRun((r) => (r ? { ...r, results: r.results.map(update) } : r));
      setSelected((r) => (r ? update(r) : r));
      setNotice(
        next === "new" ? "Removed from saved jobs" : `Job marked ${next}`,
      );
    });
  }
  const results = useMemo(() => {
    let rows =
      run?.results.filter((r) =>
        filter === "all" ? r.job.state !== "ignored" : r.job.state === filter,
      ) || [];
    const q = query.toLowerCase();
    rows = rows.filter((r) =>
      (r.job.title + " " + r.job.company + " " + r.job.location)
        .toLowerCase()
        .includes(q),
    );
    return [...rows].sort((a, b) =>
      sort === "distance"
        ? (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity)
        : sort === "fit"
          ? (b.cv_fit ?? -1) - (a.cv_fit ?? -1)
          : b.priority - a.priority,
    );
  }, [run, filter, query, sort]);
  if (!data)
    return (
      <main className="boot">
        <div className="brand">
          <span className="brand-mark">s</span>signal
          <span className="tiny">/ job intelligence</span>
        </div>
        {error ? (
          <>
            <h1>Let’s connect your local engine.</h1>
            <p role="alert">{error}</p>
            <p>
              Run <code>.\START.ps1</code> in the project folder, then reload.
            </p>
            <button className="primary" onClick={() => location.reload()}>
              Reconnect <ArrowClockwise />
            </button>
          </>
        ) : (
          <>
            <div className="skeleton" />
            <p>Opening your private workspace…</p>
          </>
        )}
      </main>
    );
  const running = run?.status === "running";
  return (
    <div className="app">
      <aside className="rail">
        <a
          className="brand"
          href="#"
          aria-label="Signal home"
          onClick={(e) => {
            e.preventDefault();
            setTab("Research");
          }}
        >
          <span className="brand-mark">s</span>signal
          <span className="beta">LOCAL</span>
        </a>
        <div className="workspace">
          <span className="avatar">{data.profile.name?.[0] || "Y"}</span>
          <div>
            <strong>{data.profile.name || "Your workspace"}</strong>
            <small>Personal job intelligence</small>
          </div>
        </div>
        <span className="eyebrow nav-label">WORKSPACE</span>
        <nav>
          {[
            ["Research", MagnifyingGlass],
            ["My profile", FileText],
            ["Sources", Stack],
            ["History", Clock],
          ].map(([name, Icon]) => (
            <button
              key={name as string}
              aria-label={name as string}
              className={tab === name ? "active" : ""}
              onClick={() => setTab(name as string)}
            >
              <Icon size={20} />
              {name as string}
              {name === "Research" && run && (
                <span className="nav-count">{run.results.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="rail-note">
          <ShieldCheck size={23} />
          <strong>Private by design.</strong>
          <p>
            Your CV is parsed locally. You control sources and optional AI
            sharing.
          </p>
          <button className="text-button" onClick={() => setModal("settings")}>
            Privacy & settings <ArrowUpRight />
          </button>
        </div>
        <div className="rail-bottom">
          <button onClick={() => setDark(!dark)} className="text-button">
            {dark ? <Sun size={19} /> : <Moon size={19} />}{" "}
            {dark ? "Light" : "Dark"} appearance
          </button>
          <small>
            <span className="status-dot" />
            Local engine connected
          </small>
        </div>
      </aside>
      <div className="shell">
        <header className="topbar">
          <div className="crumb">
            Workspace <span>/</span> <strong>{tab}</strong>
          </div>
          <div className="top-actions">
            <button
              className="icon"
              aria-label="Toggle theme"
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <span className="private-label">
              <ShieldCheck size={15} /> Stored on this device
            </span>
            <button
              className="icon"
              title="Settings"
              aria-label="Settings"
              onClick={() => setModal("settings")}
            >
              <SlidersHorizontal size={20} />
            </button>
          </div>
        </header>
        <main id="main">
          <div aria-live="polite">
            {notice && (
              <div className="toast">
                <Check size={18} />
                {notice}
              </div>
            )}
          </div>
          {error && (
            <div className="alert" role="alert">
              <WarningCircle size={20} />
              <span>{error}</span>
              <button
                className="icon"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X />
              </button>
            </div>
          )}
          {tab === "Research" && (
            <>
              <MotionHero
                profile={data.profile}
                run={run}
                onImport={() => setModal("import")}
              />
              <section className="research-grid">
                <div className="search-panel">
                  <div className="section-title">
                    <h2>Search brief</h2>
                    <Target size={20} />
                  </div>
                  <PreferencesForm
                    value={data.preferences}
                    change={(p) => setData({ ...data, preferences: p })}
                    report={setError}
                  />
                  <button
                    className="primary full"
                    disabled={busy || running}
                    onClick={() => start()}
                  >
                    <MagnifyingGlass size={19} />
                    {busy ? "Starting…" : "Start research"}
                    <ArrowRight size={18} />
                  </button>
                  <small className="search-foot">
                    Up to {data.preferences.limit} results · configured sources
                  </small>
                </div>
                <div className="results-panel">
                  <IntelligencePanel run={run} />
                  <div className="summary-strip">
                    <div>
                      <span>SHORTLIST</span>
                      <strong>
                        {run ? run.results.length : "—"}
                        <small>/ {run?.preferences.limit || 50}</small>
                      </strong>
                    </div>
                    <div>
                      <span>DISCOVERED</span>
                      <strong>{run?.counts.discovered ?? "—"}</strong>
                    </div>
                    <div>
                      <span>OFFICE LOCATED</span>
                      <strong>
                        {run
                          ? run.results.filter(
                              (r) =>
                                r.job.coordinates?.precision === "office" &&
                                r.job.work_mode !== "remote",
                            ).length
                          : "—"}
                      </strong>
                    </div>
                    <div>
                      <span>SOURCES COMPLETE</span>
                      <strong>
                        {run
                          ? run.sources.filter((s) => s.status === "Complete")
                              .length
                          : "—"}
                        <small>{run ? `/ ${run.sources.length}` : ""}</small>
                      </strong>
                    </div>
                  </div>
                  {run?.demo && (
                    <div className="demo-banner">
                      <Lightning size={18} />
                      <span>
                        <strong>Demo workspace.</strong> Fictional employers and
                        coordinates. No live jobs or verification.
                      </span>
                    </div>
                  )}
                  {run && (
                    <RunStatus
                      run={run}
                      cancel={() =>
                        act(async () => {
                          await api("/searches/" + run.id + "/cancel", "POST");
                          setRun(await api("/searches/" + run.id));
                        })
                      }
                    />
                  )}
                  <div className="result-toolbar">
                    <div className="segmented" aria-label="Result status">
                      {["all", "saved", "applied", "ignored"].map((f) => (
                        <button
                          key={f}
                          aria-pressed={filter === f}
                          className={filter === f ? "chosen" : ""}
                          onClick={() => setFilter(f)}
                        >
                          {f === "all"
                            ? "All matches"
                            : f[0].toUpperCase() + f.slice(1)}
                        </button>
                      ))}
                    </div>
                    <label className="sort">
                      <span className="sr-only">Sort results</span>
                      <select
                        value={sort}
                        onChange={(e) => setSort(e.target.value)}
                      >
                        <option value="priority">Best evidence + fit</option>
                        <option value="fit">Highest CV fit</option>
                        <option value="distance">Nearest office</option>
                      </select>
                    </label>
                  </div>
                  <div className="list-search">
                    <MagnifyingGlass size={18} />
                    <input
                      ref={searchRef}
                      placeholder="Filter by role, company or location"
                      aria-label="Filter results"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                    <kbd>Ctrl K</kbd>
                  </div>
                  {!run ? (
                    <div className="empty">
                      <div className="signal-art" aria-hidden="true">
                        <i />
                        <i />
                        <i />
                        <span>
                          <MagnifyingGlass size={32} />
                        </span>
                      </div>
                      <span className="eyebrow">
                        LESS GUESSWORK. BETTER DIRECTION.
                      </span>
                      <h2>
                        Your next chapter starts
                        <br />
                        with a little intelligence.
                      </h2>
                      <p>
                        Add your CV, choose where you want to work,
                        <br />
                        and connect the sources you trust.
                      </p>
                      <div className="empty-actions">
                        <button
                          className="primary"
                          onClick={() => setTab("My profile")}
                        >
                          Build my profile <ArrowRight size={18} />
                        </button>
                        <button
                          className="text-button"
                          onClick={() => start(true)}
                          disabled={busy}
                        >
                          Explore the demo <ArrowUpRight size={17} />
                        </button>
                      </div>
                      <div className="three-steps">
                        <span>
                          <b>01</b> Your experience
                        </span>
                        <span>
                          <b>02</b> Real sources
                        </span>
                        <span>
                          <b>03</b> Clear reasons
                        </span>
                      </div>
                    </div>
                  ) : (
                    <>
                      {results.map((row) => (
                        <JobCard
                          key={row.job.job_id}
                          row={row}
                          open={() => {
                            setSelected(row);
                            if (row.job.state === "new") state(row, "viewed");
                          }}
                          save={() =>
                            state(
                              row,
                              row.job.state === "saved" ? "new" : "saved",
                            )
                          }
                        />
                      ))}
                      {running && !results.length && (
                        <div
                          className="loading-list"
                          aria-label="Research in progress"
                        >
                          {[1, 2, 3].map((n) => (
                            <div key={n} className="skeleton job-skeleton" />
                          ))}
                          <p>
                            Researching your configured sources. Results appear
                            as evidence is checked.
                          </p>
                        </div>
                      )}
                      {!running && !results.length && (
                        <div className="empty compact">
                          <MagnifyingGlass size={35} />
                          <h2>
                            {run.results.length
                              ? "No results in this view."
                              : "No eligible jobs found."}
                          </h2>
                          <p>
                            {run.results.length
                              ? "Try another filter or clear your search."
                              : "Review the source report and excluded jobs below. Strict radius requires a known office."}
                          </p>
                          <button
                            className="secondary"
                            onClick={() => setTab("Sources")}
                          >
                            Review sources <ArrowRight />
                          </button>
                        </div>
                      )}
                      <details className="diagnostics">
                        <summary>
                          Research notes & diagnostics <CaretDown />
                        </summary>
                        <p>
                          Scores are explainable heuristics, not hiring
                          probabilities. Unknown fields are unscored; evidence
                          coverage affects ranking.
                        </p>
                        {run.warnings.map((w, i) => (
                          <p key={i} className="warning-text">
                            {w}
                          </p>
                        ))}
                        <div className="diagnostic-grid">
                          <div>
                            <h3>Search strategy</h3>
                            {run.plan.strategies.map((s) => (
                              <p key={s.name}>
                                <strong>{s.name}</strong>
                                <br />
                                {s.queries.join(", ") || "Not supplied"}
                              </p>
                            ))}
                          </div>
                          <div>
                            <h3>Exclusions</h3>
                            {Object.entries(run.exclusions).map(([k, v]) => (
                              <p key={k}>
                                {k} <b>{v}</b>
                              </p>
                            ))}
                            <p>
                              Duplicates merged <b>{run.counts.duplicates}</b>
                            </p>
                            <p>
                              Requests <b>{run.network?.requests ?? 0}</b> ·
                              Cache hits <b>{run.network?.cache_hits ?? 0}</b>
                            </p>
                            <p>Started {date(run.started_at)}</p>
                          </div>
                        </div>
                        {run.linkedin.length > 0 && (
                          <>
                            <h3>Continue manually on LinkedIn</h3>
                            <p>
                              Past 7 days, newest first. These are search links;
                              LinkedIn was not searched by this engine.
                            </p>
                            <div className="chips">
                              {run.linkedin.map((l) => (
                                <Link key={l.role} href={l.url}>
                                  {l.role}
                                </Link>
                              ))}
                            </div>
                          </>
                        )}
                      </details>
                    </>
                  )}
                </div>
              </section>
            </>
          )}
          {tab === "My profile" && (
            <ProfileEditor
              initial={data.profile}
              busy={busy}
              save={(p) =>
                act(async () => {
                  const saved = await api<Profile>("/profile", "PUT", p);
                  setData({ ...data, profile: saved });
                  setNotice("Profile saved on this device");
                })
              }
              report={setError}
            />
          )}
          {tab === "Sources" && (
            <SourcesEditor
              initial={data.sources}
              count={data.imports}
              save={(s) =>
                act(async () => {
                  await api("/sources", "PUT", s);
                  setData({ ...data, sources: s });
                  setNotice("Source preferences saved");
                })
              }
              busy={busy}
              importJob={() => setModal("import")}
            />
          )}
          {tab === "History" && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR RESEARCH TRAIL</div>
                  <h1>Pick up where you left off.</h1>
                  <p>The latest 20 searches, encrypted on this device.</p>
                </div>
              </div>
              <div className="history-list">
                {!data.history.length && (
                  <div className="empty compact">
                    <Clock size={32} />
                    <h2>No searches yet.</h2>
                    <p>
                      Your completed and interrupted research will appear here.
                    </p>
                  </div>
                )}
                {data.history.map((h) => (
                  <button
                    key={h.id}
                    className="history-row"
                    onClick={() =>
                      act(async () => {
                        setRun(await api<Run>("/searches/" + h.id));
                        setTab("Research");
                      })
                    }
                  >
                    <span className="history-icon">
                      <MagnifyingGlass size={22} />
                    </span>
                    <span>
                      <strong>
                        {h.demo ? "Demo research" : "Job research"}
                      </strong>
                      <small>{date(h.started_at)}</small>
                    </span>
                    <Tag>{h.status}</Tag>
                    <span>{h.counts.eligible} eligible</span>
                    <ArrowUpRight size={20} />
                  </button>
                ))}
              </div>
            </>
          )}
          <footer>
            <span>Signal / Job intelligence</span>
            <span>Evidence over assumptions. Always.</span>
          </footer>
        </main>
      </div>
      {selected && (
        <JobDetail
          searchId={run?.id || ""}
          row={selected}
          close={() => setSelected(null)}
          state={(s) => state(selected, s)}
          busy={busy}
          demo={!!run?.demo}
        />
      )}
      {modal === "import" && (
        <ImportModal
          close={() => setModal(null)}
          done={() => {
            setModal(null);
            refresh();
            setNotice(
              "Listing imported. Start a new search to match and check it.",
            );
          }}
          report={setError}
        />
      )}
      {modal === "settings" && (
        <Settings
          error={error}
          initial={data.llm}
          close={() => setModal(null)}
          save={(llm) =>
            act(async () => {
              await api("/llm", "PUT", llm);
              await refresh();
              setNotice("AI settings saved");
              setModal(null);
            })
          }
          busy={busy}
          erase={() => setModal("delete")}
        />
      )}
      {modal === "delete" && (
        <Modal title="Delete local workspace?" close={() => setModal(null)}>
          <p>
            This removes your profile, imports, job states, search history, API
            key and cached pages from this app. It stops active searches first.
            Export anything you need before continuing.
          </p>
          <div className="modal-actions">
            <button className="secondary" onClick={() => setModal(null)}>
              Keep my data
            </button>
            <button
              className="danger"
              disabled={busy}
              onClick={() =>
                act(async () => {
                  await api("/data", "DELETE");
                  setRun(null);
                  setSelected(null);
                  await refresh(true);
                  setModal(null);
                  setNotice("Local workspace deleted");
                })
              }
            >
              <Trash />
              Delete all local data
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
