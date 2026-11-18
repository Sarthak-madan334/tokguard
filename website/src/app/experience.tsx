"use client";

import { useEffect, useState } from "react";

const proofSteps = [
  { key: "map", title: "Map", command: "tg map", output: "tg/map.py → generate_repo_map(), find_symbol()\ntg/cli.py → cmd_map(), cmd_find(), cmd_read()", note: "TokGuard’s repository map lists real project files and symbols." },
  { key: "find", title: "Find", command: "tg find generate_repo_map", output: "tg/map.py → generate_repo_map()", note: "The symbol is defined in TokGuard’s map module." },
  { key: "read", title: "Read", command: "tg read tg/map.py 1-25", output: "Selected source range from tg/map.py", note: "Read only the range needed to inspect the implementation." },
];

export function MobileMenu() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mobile-menu">
      <button type="button" aria-expanded={open} aria-controls="mobile-links" onClick={() => setOpen((value) => !value)}>
        <span>{open ? "Close" : "Menu"}</span><span aria-hidden="true">{open ? "×" : "☰"}</span>
      </button>
      <nav id="mobile-links" className={open ? "open" : ""} aria-label="Mobile navigation" hidden={!open}>
        {[ ["How it works", "#how"], ["TokGuard 2.0", "#whats-new"], ["Results", "#results"], ["Agents", "#agents"], ["Get started", "#install"] ].map(([label, href]) => (
          <a href={href} key={href} onClick={() => setOpen(false)}>{label}</a>
        ))}
      </nav>
    </div>
  );
}

export function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };
  return <button className="copy-button" type="button" onClick={copy} aria-label={`Copy command: ${command}`}>{copied ? "Copied" : "Copy"}<span aria-hidden="true">{copied ? "✓" : "⧉"}</span></button>;
}

export function TerminalDemo() {
  return (
    <div className="terminal-card reveal" aria-label="TokGuard terminal example">
      <div className="terminal-heading"><div><span className="terminal-dot" aria-hidden="true" /><span>TokGuard in a repository</span></div></div>
      <div className="terminal-output">
        <p className="terminal-command"><span aria-hidden="true">›</span> tg map</p>
        <pre className="terminal-result">tg/map.py <span>generate_repo_map(), find_symbol()</span><br />tg/cli.py <span>cmd_map(), cmd_find(), cmd_read()</span></pre>
        <p className="terminal-command"><span aria-hidden="true">›</span> tg find generate_repo_map</p>
        <pre className="terminal-result terminal-last">tg/map.py <span>generate_repo_map()</span></pre>
      </div>
    </div>
  );
}

export function ProofScene() {
  const [active, setActive] = useState(0);
  const [replay, setReplay] = useState(0);
  const current = proofSteps[active];
  return (
    <div className="proof-scene reveal">
      <div className="proof-prompt"><p className="eyebrow">The task</p><p>“Find where the total is calculated and inspect the implementation.”</p><span>One request. A few focused steps.</span></div>
      <div className="proof-workflow">
        <div className="proof-heading"><span>Follow the context</span><button type="button" className="replay-button" onClick={() => { setActive(0); setReplay((value) => value + 1); }} aria-label="Replay the workflow">Replay <span aria-hidden="true">↻</span></button></div>
        <div className="proof-tabs" role="tablist" aria-label="Workflow steps">
          {proofSteps.map((step, index) => <button type="button" role="tab" id={`proof-tab-${step.key}`} aria-controls="proof-panel" aria-selected={active === index} tabIndex={active === index ? 0 : -1} key={step.key} onClick={() => setActive(index)}>{step.title}</button>)}
        </div>
        <div className="proof-panel" role="tabpanel" id="proof-panel" aria-labelledby={`proof-tab-${current.key}`} key={replay}>
          {proofSteps.map((step, index) => <article className={`proof-step-row ${active === index ? "active" : ""}`} key={step.key}>
            <span className="proof-step-icon" aria-hidden="true">{active === index ? "✓" : "↳"}</span>
            <div className="proof-step-content"><div className="proof-step-title"><strong>{step.title}</strong><code>{step.command}</code></div><pre>{step.output}</pre><p>{step.note}</p></div>
          </article>)}
        </div>
        <p className="proof-disclaimer">Illustrative tool flow, not a benchmark task.</p>
      </div>
    </div>
  );
}

export function ScrollEffects() {
  useEffect(() => {
    const targets = document.querySelectorAll<HTMLElement>(".reveal");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const showAll = () => targets.forEach((target) => target.classList.add("visible"));
    if (reduce.matches || !("IntersectionObserver" in window)) {
      showAll();
      return;
    }
    document.documentElement.classList.add("motion-ready");
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    }), { threshold: 0.08 });
    targets.forEach((target) => observer.observe(target));
    const onMotionChange = () => { if (reduce.matches) { showAll(); observer.disconnect(); } };
    reduce.addEventListener("change", onMotionChange);
    return () => { observer.disconnect(); reduce.removeEventListener("change", onMotionChange); };
  }, []);
  return null;
}
