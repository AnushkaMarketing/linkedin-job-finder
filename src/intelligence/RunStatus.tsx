import { Pause, CaretDown } from "@phosphor-icons/react";

import type { Run } from "./types";

export function RunStatus({ run, cancel }: { run: Run; cancel: () => void }) {
  return (
    <details className="run-status" open={run.status === "running"}>
      <summary>
        <span
          className={run.status === "running" ? "pulse-dot" : "status-dot"}
        />
        <strong>{run.stage}</strong>
        <span>{run.elapsed}s</span>
        <CaretDown size={16} />
      </summary>
      <div className="source-report">
        {run.sources.map((s, i) => (
          <div key={s.source + i}>
            <div>
              <strong>{s.source}</strong>
              <small>{s.detail}</small>
            </div>
            <span className={s.status === "Complete" ? "positive" : "muted"}>
              {s.status}
              {s.count ? ` · ${s.count}` : ""}
            </span>
          </div>
        ))}
        {run.status === "running" && (
          <button className="secondary" onClick={cancel}>
            <Pause size={17} /> Stop research
          </button>
        )}
      </div>
    </details>
  );
}
