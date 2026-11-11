"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

type WorkflowKey = "map" | "find" | "read" | "run";

const workflow: Record<WorkflowKey, { label: string; command: string; output: ReactNode; note: string }> = {
  map: {
    label: "01 / ORIENT BEFORE YOU OPEN FILES",
    command: "tg map",
    output: <><span className="code-dim">src/</span><br />├─ checkout.py <span>calculate_total()</span><br />├─ cart.py <span>class Cart</span><br />└─ inventory.py <span>check_stock()</span><br /><br /><span className="code-success">✓ Compact outline ready</span></>,
    note: "A fast orientation before targeted inspection.",
  },
  find: {
    label: "02 / SEARCH FOR A SYMBOL OR PATTERN",
    command: "tg find calculate_total",
    output: <><span className="code-dim">src/checkout.py:42</span><br />  41 │ def checkout(cart):<br /><span className="code-highlight">&gt; 42 │ def calculate_total(cart):</span><br />  43 │ &nbsp;&nbsp;&nbsp;&nbsp;return sum(cart.items)<br /><br /><span className="code-success">✓ Match found with nearby context</span></>,
    note: "Search returns focused matches with surrounding lines.",
  },
  read: {
    label: "03 / OPEN ONLY THE RELEVANT RANGE",
    command: "tg read src/checkout.py 42-58",
    output: <><span className="code-dim">42 │ def calculate_total(cart):</span><br />43 │ &nbsp;&nbsp;&nbsp;&nbsp;subtotal = cart.subtotal()<br />44 │ &nbsp;&nbsp;&nbsp;&nbsp;tax = calculate_tax(subtotal)<br />45 │ &nbsp;&nbsp;&nbsp;&nbsp;return subtotal + tax<br /><br /><span className="code-success">✓ 17 lines read</span></>,
    note: "Targeted reads keep large files out of the conversation.",
  },
  run: {
    label: "04 / KEEP COMMAND OUTPUT USEFUL",
    command: "tg run -- pytest -q",
    output: <><span className="code-dim">tests/test_checkout.py</span><br /><span className="code-success">✓ 18 passed</span><br /><span className="code-dim">1.42s · output compressed</span><br /><br /><span className="code-highlight">Raw log saved for follow-up search</span></>,
    note: "Progress noise is filtered; errors and useful summaries stay visible.",
  },
};

export function CinematicField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    let width = 0;
    let height = 0;
    let frame = 0;
    let visible = true;
    let reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let pointer = { x: -1000, y: -1000 };
    const particles = Array.from({ length: 68 }, () => ({
      x: Math.random(), y: Math.random(),
      dx: (Math.random() - 0.5) * 0.00013,
      dy: (Math.random() - 0.5) * 0.0001,
      size: Math.random() * 1.5 + 0.35,
      alpha: Math.random() * 0.55 + 0.15,
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);
      const points = particles.map((p) => {
        if (!reduced) {
          p.x += p.dx;
          p.y += p.dy;
          if (p.x < -0.05) p.x = 1.05;
          if (p.x > 1.05) p.x = -0.05;
          if (p.y < -0.05) p.y = 1.05;
          if (p.y > 1.05) p.y = -0.05;
        }
        const wave = reduced ? 0 : Math.sin(time * 0.0003 + p.x * 5) * 3;
        return { x: p.x * width + wave, y: p.y * height, p };
      });

      for (let i = 0; i < points.length; i += 1) {
        const a = points[i];
        for (let j = i + 1; j < points.length; j += 1) {
          const b = points[j];
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 100) {
            ctx.strokeStyle = `rgba(211, 173, 125, ${((1 - dist / 100) * 0.105).toFixed(3)})`;
            ctx.lineWidth = 0.65;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        const mouseDist = Math.hypot(a.x - pointer.x, a.y - pointer.y);
        const glow = mouseDist < 150 ? (1 - mouseDist / 150) * 0.8 : 0;
        ctx.fillStyle = `rgba(232, 192, 139, ${Math.min(0.95, a.p.alpha + glow)})`;
        ctx.beginPath();
        ctx.arc(a.x, a.y, a.p.size + glow * 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
      if (visible && !document.hidden && !reduced && document.documentElement.dataset.quiet !== "true") {
        frame = requestAnimationFrame(draw);
      }
    };

    const start = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(draw);
    };
    const motionChange = (event: MediaQueryListEvent) => { reduced = event.matches; start(); };
    const quietChange = () => start();
    const visibilityChange = () => start();
    const pointerMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };
    const pointerLeave = () => { pointer = { x: -1000, y: -1000 }; };
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; start(); }, { threshold: 0.01 });

    resize();
    observer.observe(canvas);
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", pointerMove, { passive: true });
    canvas.addEventListener("pointerleave", pointerLeave);
    document.addEventListener("visibilitychange", visibilityChange);
    media.addEventListener("change", motionChange);
    window.addEventListener("tokguard-motion-change", quietChange);
    start();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", pointerMove);
      canvas.removeEventListener("pointerleave", pointerLeave);
      document.removeEventListener("visibilitychange", visibilityChange);
      media.removeEventListener("change", motionChange);
      window.removeEventListener("tokguard-motion-change", quietChange);
    };
  }, []);

  return <canvas ref={canvasRef} className="cinematic-field" aria-hidden="true" />;
}

export function MobileMenu() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mobile-menu">
      <button type="button" aria-expanded={open} aria-controls="mobile-links" onClick={() => setOpen((value) => !value)}>
        <span>{open ? "Close" : "Menu"}</span><span aria-hidden="true">{open ? "×" : "☰"}</span>
      </button>
      <nav id="mobile-links" className={open ? "open" : ""} aria-label="Mobile navigation">
        {[ ["How it works", "#how"], ["Savings", "#savings"], ["Agents", "#agents"], ["Install", "#install"] ].map(([label, href]) => (
          <a href={href} key={href} onClick={() => setOpen(false)}>{label}</a>
        ))}
      </nav>
    </div>
  );
}

export function WorkflowScene() {
  const [step, setStep] = useState<WorkflowKey>("map");
  const selected = workflow[step];
  const keys = Object.keys(workflow) as WorkflowKey[];
  return (
    <div className="workflow-layout">
      <div className="workflow-list" role="tablist" aria-label="TokGuard workflow">
        {keys.map((key, index) => (
          <button className={`workflow-step ${step === key ? "active" : ""}`} id={`tab-${key}`} key={key} role="tab" aria-selected={step === key} aria-controls="workflow-panel" onClick={() => setStep(key)}>
            <span className="step-number">0{index + 1}</span><span className="step-copy"><b>{key[0].toUpperCase() + key.slice(1)}</b><small>{["Get a compact repo outline", "Search by symbol or pattern", "Open a range or symbol body", "Keep output focused and capped"][index]}</small></span><span className="step-icon" aria-hidden="true">{["⌘", "⌕", "↙", "›_"][index]}</span>
          </button>
        ))}
      </div>
      <div className="workflow-panel" id="workflow-panel" role="tabpanel" aria-labelledby={`tab-${step}`} key={step}>
        <div className="panel-top"><span><i className="panel-status" /> TOKGUARD / WORKFLOW</span><span className="panel-file">POWERSHELL</span></div>
        <div className="panel-content"><div className="panel-caption">{selected.label}</div><div className="code-block"><div className="code-line"><span className="code-prompt">PS&gt;</span><code>{selected.command}</code></div><div className="code-output">{selected.output}</div></div><div className="panel-bottom"><span>{selected.note}</span><span className="panel-badge">READ ONLY</span></div></div>
      </div>
    </div>
  );
}

const proofSteps = [
  { label: "MAP", title: "Get oriented", command: "tg map", result: "checkout.py → calculate_total()\ncart.py → class Cart\ninventory.py → check_stock()", detail: "A compact outline points to likely files and symbols." },
  { label: "FIND", title: "Locate the work", command: "tg find calculate_total", result: "src/checkout.py:42\n1 matching symbol\n1 line of context", detail: "Search finds the implementation without reading every file into chat." },
  { label: "READ", title: "Inspect only what matters", command: "tg read src/checkout.py 42-58", result: "17 lines returned\nRelevant function body\nNearby context preserved", detail: "The agent gets the useful range, then continues with the actual task." },
];

export function ProofScene() {
  const [active, setActive] = useState(0);
  const current = proofSteps[active];
  return (
    <div className="proof-scene">
      <div className="proof-scene-top"><span><i /> INTERACTIVE WORKFLOW</span><span>EXAMPLE TASK / 01</span></div>
      <div className="proof-scene-body">
        <div className="proof-claim"><span className="claim-label">A TASK COMES IN</span><p>“Find where the total is calculated and inspect the implementation.”</p><span className="claim-foot">NO FULL REPO DUMP REQUIRED</span></div>
        <div className="proof-evidence"><div className="evidence-head"><span>{current.label} / {current.title}</span><span>STEP 0{active + 1}</span></div><div className="evidence-command"><span>›</span> {current.command}</div><pre>{current.result}</pre><p>{current.detail}</p><div className="proof-steps" role="tablist" aria-label="Workflow example steps">{proofSteps.map((item, index) => <button key={item.label} className={active === index ? "active" : ""} role="tab" aria-selected={active === index} onClick={() => setActive(index)}><span>0{index + 1}</span>{item.label}</button>)}</div></div>
      </div>
      <div className="proof-scene-foot"><span>Illustrative tool flow, not a benchmark task.</span><span>MAP <i>→</i> FIND <i>→</i> READ</span></div>
    </div>
  );
}

export function CopyCommand({ command, label = "COPY" }: { command: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timeout.current) clearTimeout(timeout.current); }, []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      if (timeout.current) clearTimeout(timeout.current);
      timeout.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };
  return <button className="copy-button" type="button" onClick={copy} aria-label={`Copy ${command}`}>{copied ? "COPIED" : label}<span aria-hidden="true">{copied ? "✓" : "⧉"}</span></button>;
}

export function MotionToggle() {
  const [quiet, setQuiet] = useState(false);
  useEffect(() => {
    setQuiet(document.documentElement.dataset.quiet === "true");
  }, []);
  const toggle = () => {
    const next = !quiet;
    setQuiet(next);
    document.documentElement.dataset.quiet = String(next);
    window.dispatchEvent(new Event("tokguard-motion-change"));
  };
  return <button className="motion-toggle" type="button" aria-pressed={quiet} onClick={toggle}>Motion {quiet ? "off" : "on"}</button>;
}

export function ScrollEffects() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const targets = document.querySelectorAll<HTMLElement>(".reveal");
    if (reduce || !("IntersectionObserver" in window)) {
      targets.forEach((target) => target.classList.add("visible"));
      return;
    }
    document.documentElement.classList.add("motion-ready");
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, []);
  return null;
}
