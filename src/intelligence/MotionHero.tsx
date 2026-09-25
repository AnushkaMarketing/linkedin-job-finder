import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { motion } from "motion/react";
import { Pause, Play, Plus, ArrowUpRight } from "@phosphor-icons/react";
import type { Profile, Run } from "./types";

const preference = '(prefers-reduced-motion: reduce)';
function subscribeMotion(change:()=>void) {const query=window.matchMedia(preference);query.addEventListener('change',change);return()=>query.removeEventListener('change',change);}
const motionSnapshot=()=>window.matchMedia(preference).matches;

export function MotionHero({
  profile,
  run,
  onImport,
}: {
  profile: Profile;
  run: Run | null;
  onImport: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [paused, setPaused] = useState(false);
  const reduced = useSyncExternalStore(subscribeMotion,motionSnapshot,()=>true);
  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const context = el.getContext("2d");
    if (!context) return;
    let width = 600,
      height = 300,
      frame = 0,
      last = 0,
      visible = true;
    const pointer = { x: -999, y: -999 };
    const points = Array.from({ length: 200 }, (_, i) => ({
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      seed: i,
      group: i % 4,
    }));
    const centers = [
      [0.19, 0.48],
      [0.46, 0.26],
      [0.53, 0.76],
      [0.82, 0.48],
    ];
    function base(i: number, t: number) {
      const p = points[i],
        c = centers[p.group],
        a = i * 2.399963,
        r = 12 + Math.sqrt((i * 17) % 51) * 7;
      return {
        x: c[0] * width + Math.cos(a + t * 0.13) * r,
        y: c[1] * height + Math.sin(a + t * 0.13) * r * 0.65,
      };
    }
    function resize() {
      const box = el!.getBoundingClientRect();
      width = box.width;
      height = box.height;
      const dpr = Math.min(devicePixelRatio, 2);
      el!.width = width * dpr;
      el!.height = height * dpr;
      context!.setTransform(dpr, 0, 0, dpr, 0, 0);
      points.forEach((p, i) => Object.assign(p, base(i, 0)));
      draw(0);
    }
    function draw(time: number) {
      context!.clearRect(0, 0, width, height);
      const dark = document.documentElement.dataset.theme === "dark";
      const colors = dark
        ? ["#afa4ff", "#dfb1fa", "#7fbeb9", "#edb3a5"]
        : ["#6555d8", "#a487c3", "#509d96", "#d38370"];
      for (let i = 0; i < points.length; i++) {
        const p = points[i],
          b = base(i, time),
          dx = p.x - pointer.x,
          dy = p.y - pointer.y,
          d = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = Math.max(0, 1 - d / 95) * 2.4;
        p.vx = (p.vx + (b.x - p.x) * 0.024 + (dx / d) * force) * 0.84;
        p.vy = (p.vy + (b.y - p.y) * 0.024 + (dy / d) * force) * 0.84;
        p.x += p.vx;
        p.y += p.vy;
        context!.fillStyle = colors[p.group];
        context!.globalAlpha = 0.25 + ((i * 7) % 10) / 15;
        context!.beginPath();
        context!.arc(p.x, p.y, i % 9 === 0 ? 2.3 : 1.3, 0, Math.PI * 2);
        context!.fill();
      }
      // Traveling evidence points; these illustrate the workflow, not task progress.
      if (!paused && !reduced)
        for (let n = 0; n < 12; n++) {
          const t = (time * 0.09 + n / 12) % 1;
          context!.globalAlpha = Math.sin(t * Math.PI) * 0.55;
          context!.fillStyle = colors[n % 4];
          context!.beginPath();
          context!.arc(
            width * (0.19 + 0.63 * t),
            height * (0.48 + Math.sin(t * Math.PI * 2 + n) * 0.13),
            2,
            0,
            Math.PI * 2,
          );
          context!.fill();
        }
      context!.globalAlpha = 1;
    }
    function tick(t: number) {
      if (visible && !document.hidden && !paused && !reduced && t - last > 30) {
        draw(t / 1000);
        last = t;
      }
      frame = requestAnimationFrame(tick);
    }
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    const intersection = new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    });
    intersection.observe(el);
    const move = (e: PointerEvent) => {
      const b = el.getBoundingClientRect();
      pointer.x = e.clientX - b.left;
      pointer.y = e.clientY - b.top;
    };
    const leave = () => {
      pointer.x = -999;
      pointer.y = -999;
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", leave);
    const theme = new MutationObserver(() => draw(0));
    theme.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    if (!paused && !reduced) frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      intersection.disconnect();
      theme.disconnect();
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", leave);
    };
  }, [paused, reduced]);
  return (
    <section className="motion-hero">
      <div className="hero-copy">
        <span className="studio-label">
          <span />
          Personal career intelligence
        </span>
        <h1>
          Find the fit.
          <br />
          See the evidence.
        </h1>
        <p>
          Your experience becomes a map of possibilities.
          <br />
          Follow the ones with evidence behind them.
        </p>
        <div className="hero-actions">
          <button className="primary" onClick={onImport}>
            <Plus size={18} />
            Import a job
          </button>
          <span>
            {profile.skills.length
              ? `${profile.skills.length} profile skills ready to match`
              : "Start with your CV. Keep your data local."}
          </span>
        </div>
      </div>
      <div className="career-map">
        <canvas ref={canvas} aria-hidden="true" />
        <div className="map-caption">
          Your opportunity map <ArrowUpRight size={14} />
        </div>
        {[
          {
            label: "Your experience",
            sub: profile.current_role || "Skills · projects · strengths",
            className: "profile-node",
          },
          {
            label: "Role alignment",
            sub: "Requirements + alternatives",
            className: "role-node",
          },
          {
            label: "Evidence",
            sub: "Sources + uncertainty",
            className: "evidence-node",
          },
          {
            label: "Your shortlist",
            sub: run
              ? `${run.results.length} ${run.demo ? "demo" : "researched"} matches`
              : "Clear reasons to apply",
            className: "shortlist-node",
          },
        ].map((node, i) => (
          <motion.div
            key={node.label}
            className={"map-node " + node.className}
            initial={reduced ? false : { opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.12, duration: 0.5 }}
            whileHover={reduced ? {} : { y: -5, rotate: i % 2 ? 2 : -2 }}
          >
            <span className="node-symbol">{["✦", "↗", "✓", "↗"][i]}</span>
            <strong>{node.label}</strong>
            <small>{node.sub}</small>
          </motion.div>
        ))}
        <div className="map-bottom">
          <span>Move your pointer to explore · illustrative map</span>
          <button
            className="icon"
            aria-label={paused ? "Play motion" : "Pause motion"}
            onClick={() => setPaused(!paused)}
            disabled={!!reduced}
          >
            {paused || reduced ? <Play size={15} /> : <Pause size={15} />}
          </button>
        </div>
      </div>
    </section>
  );
}
