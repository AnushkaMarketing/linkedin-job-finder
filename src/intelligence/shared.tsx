import {
  useEffect,
  useRef,
  useId,
  Children,
  cloneElement,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react";
import { ArrowUpRight, X } from "@phosphor-icons/react";
import type { Salary } from "./types";
export const split = (s: string) => (s ? s.split(/,\s*|\n/) : []);
export const number = (s: string) => (s === "" ? null : Number(s));
export const pct = (n: number | null) => (n === null ? "—" : Math.round(n));
export const date = (s: string) =>
  new Date(s).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
export const salary = (s: Salary) =>
  s.minimum !== null || s.maximum !== null
    ? `${s.currency} ${s.minimum?.toLocaleString() ?? "?"} – ${s.maximum?.toLocaleString() ?? "?"} / ${s.period}`
    : s.text || "Salary not disclosed";
export function Link({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return /^https?:\/\//.test(href) ? (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
      <ArrowUpRight size={14} />
    </a>
  ) : null;
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  const id = useId();
  const annotate = (nodes: ReactNode): ReactNode =>
    Children.map(nodes, (child) => {
      if (!isValidElement(child)) return child;
      const element = child as ReactElement<{
        id?: string;
        children?: ReactNode;
        "aria-describedby"?: string;
      }>;
      if (
        typeof element.type === "string" &&
        ["input", "textarea", "select"].includes(element.type)
      )
        return cloneElement(element, {
          id,
          "aria-describedby": hint ? id + "-hint" : undefined,
        });
      return element.props.children
        ? cloneElement(element, { children: annotate(element.props.children) })
        : element;
    });
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {annotate(children)}
      {hint && <small id={id + "-hint"}>{hint}</small>}
    </div>
  );
}
export function Tag({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"tag " + tone}>{children}</span>;
}
export function Modal({
  title,
  children,
  close,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={wide ? "modal wide" : "modal"}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
    >
      <div className="modal-head">
        <h2 id={titleId}>{title}</h2>
        <button className="icon" aria-label="Close dialog" onClick={close}>
          <X size={22} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
