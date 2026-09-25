import { useEffect, useState } from "react";
import { ThumbsUp, ThumbsDown, Sparkle } from "@phosphor-icons/react";
import { api } from "./api";
import type { Ranked, Run } from "./types";

export function IntelligencePanel({ run }: { run: Run | null }) {
  const [learning, setLearning] = useState<{
    ready: boolean;
    labels: number;
    positive: number;
    negative: number;
  } | null>(null);
  useEffect(() => {
    let alive = true;
    api<typeof learning>("/learning")
      .then((value) => {
        if (alive) setLearning(value);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [run?.id, run?.status]);
  return (
    <section className="intelligence-strip">
      <div className="intelligence-title">
        <Sparkle size={21} />
        <div>
          <strong>
            {learning?.ready
              ? "Learning from your judgement"
              : "An engine you can teach"}
          </strong>
          <p>
            {learning
              ? `${learning.labels} explicit labels · ${learning.ready ? "personalization active, bounded to ±4 priority points" : "8 labels, with at least 3 positive and 3 negative, activate local learning"}`
              : "Local feedback learning; no CV leaves your device."}
          </p>
        </div>
        <span className="engine-version">Engine 2</span>
      </div>
      {run?.insights && run.insights.gap_opportunities.length > 0 && (
        <div className="gap-opportunities">
          <span>Skills that could open more of this shortlist</span>
          {run.insights.gap_opportunities.map((g) => (
            <span className="opportunity-chip" key={g.skill}>
              {g.skill}
              <b>
                {g.jobs} {g.jobs === 1 ? "role" : "roles"}
              </b>
            </span>
          ))}
          <small>{run.insights.note}</small>
        </div>
      )}
    </section>
  );
}

export function TeachEngine({
  row,
  searchId,
  demo,
}: {
  row: Ranked;
  searchId: string;
  demo: boolean;
}) {
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [vote, setVote] = useState("");
  async function teach(label: string) {
    setBusy(true);
    try {
      await api("/feedback", "POST", {
        search_id: searchId,
        job_id: row.job.job_id,
        label,
      });
      setVote(label);
      setMessage("Saved locally. Your next search will use eligible feedback.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="teach-engine">
      <div>
        <Sparkle size={20} />
        <h3>Teach the engine your judgement</h3>
      </div>
      <p>
        {demo
          ? "Demo labels never train your personal model. Try this on a real result."
          : "Is this opportunity relevant to you? This trains preference ranking, not your qualifications or hiring chances."}
      </p>
      <div className="chips">
        <button
          className={vote === "relevant" ? "primary" : "secondary"}
          disabled={busy || demo}
          onClick={() => teach("relevant")}
        >
          <ThumbsUp />
          Relevant to me
        </button>
        <button
          className={vote === "not_relevant" ? "primary" : "secondary"}
          disabled={busy || demo}
          onClick={() => teach("not_relevant")}
        >
          <ThumbsDown />
          Not relevant
        </button>
      </div>
      <small role="status">{message}</small>
    </section>
  );
}
