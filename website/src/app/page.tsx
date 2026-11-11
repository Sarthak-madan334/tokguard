import type { CSSProperties } from "react";
import {
  CinematicField,
  CopyCommand,
  MobileMenu,
  MotionToggle,
  ProofScene,
  ScrollEffects,
  WorkflowScene,
} from "./experience";

function Logo() {
  return (
    <a className="wordmark" href="#top" aria-label="TokGuard home">
      <svg viewBox="0 0 34 34" aria-hidden="true"><path d="M17 2.7 29 7v9.2c0 7.5-5 12.3-12 15.1C10 28.5 5 23.7 5 16.2V7l12-4.3Z" /><path d="m11.2 17.2 3.7 3.7 7.9-8" /></svg>
      <span>tokguard<span className="wordmark-stop">.</span></span>
    </a>
  );
}

const agents = [
  { initials: "◈", name: "Codex", type: "OPENAI CODING AGENT", body: "Connect TokGuard tools and repository guidance to Codex." },
  { initials: "✳", name: "Claude Code", type: "ANTHROPIC CODING AGENT", body: "Use compact maps, targeted reads, and quieter command output." },
  { initials: "✦", name: "Antigravity", type: "GOOGLE CODING AGENT", body: "Register TokGuard as an MCP server across your projects." },
  { initials: "+", name: "MCP-compatible agents", type: "OPEN MCP SERVER", body: "Connect directly from another client that supports MCP." },
];

export default function Home() {
  return (
    <>
      <ScrollEffects />
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <div className="header-inner page-width">
          <Logo />
          <nav className="desktop-nav" aria-label="Main navigation">
            <a href="#idea">The idea</a><a href="#how">How it works</a><a href="#savings">The proof</a><a href="#agents">Agents</a>
          </nav>
          <a className="header-cta" href="#install">Get started <span aria-hidden="true">↗</span></a>
          <MobileMenu />
        </div>
      </header>

      <main id="main" tabIndex={-1}>
        <section className="cinema-hero" id="top">
          <CinematicField />
          <div className="hero-scrim" aria-hidden="true" />
          <div className="page-width hero-grid">
            <div className="hero-content">
              <div className="hero-kicker"><i /> OPEN-SOURCE CONTEXT TOOLKIT</div>
              <h1>Less context.<br /><span>More coding.</span></h1>
              <p className="hero-lede">TokGuard helps your coding agent find the right files, read only what matters, and keep command output under control.</p>
              <div className="hero-buttons">
                <a className="hero-action" href="#install">Set it up <span aria-hidden="true">↗</span></a>
                <a className="text-link" href="#how">See how it works <span aria-hidden="true">↓</span></a>
              </div>
              <div className="hero-support"><span className="support-pulse" /> FOR CODEX · CLAUDE CODE · ANTIGRAVITY</div>
            </div>
            <div className="hero-showcase" aria-label="TokGuard command-line preview">
              <div className="hero-orbit orbit-a" /><div className="hero-orbit orbit-b" />
              <div className="float-label float-label-a"><span>01</span> MAP THE REPO</div>
              <div className="float-label float-label-b"><span>02</span> FIND A SYMBOL</div>
              <div className="terminal-window">
                <div className="terminal-top"><div className="window-lights"><i /><i /><i /></div><span className="terminal-title">tokguard / focused context</span><span className="terminal-live"><i /> LIVE</span></div>
                <div className="terminal-content">
                  <div className="terminal-cmd"><span>›</span> tg map</div>
                  <div className="terminal-tree"><div className="tree-folder">src/</div><div className="tree-row"><span>├─ checkout.py</span><b>calculate_total()</b></div><div className="tree-row"><span>├─ cart.py</span><b>class Cart</b></div><div className="tree-row"><span>└─ inventory.py</span><b>check_stock()</b></div><div className="tree-more">… compact outline ready</div></div>
                  <div className="terminal-rule" />
                  <div className="terminal-cmd"><span>›</span> tg find calculate_total</div>
                  <div className="terminal-result"><span className="result-mark">✓</span><div><b>src/checkout.py:42</b><small>1 match · 1 line of context</small></div><span className="result-open">↗</span></div>
                  <div className="terminal-meter"><span>CONTEXT SPENT</span><div><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div><b>focused</b></div>
                </div>
              </div>
              <span className="hero-spark spark-1" aria-hidden="true">✳</span><span className="hero-spark spark-2" aria-hidden="true">✳</span><span className="hero-spark spark-3" aria-hidden="true">·</span>
            </div>
          </div>
          <div className="hero-bottom page-width"><span>THE RIGHT CONTEXT, WITHOUT THE REPO DUMP</span><span className="scroll-thread" /><a href="#idea">SCROLL TO EXPLORE <span aria-hidden="true">↓</span></a></div>
        </section>

        <div className="proof-ticker" aria-hidden="true"><div>MAP <i>✳</i> FIND <i>✳</i> READ <i>✳</i> RUN <i>✳</i> TRACK <i>✳</i> MAP <i>✳</i> FIND <i>✳</i> READ <i>✳</i> RUN <i>✳</i> TRACK <i>✳</i></div></div>

        <section className="belief-section page-width" id="idea">
          <div className="section-overline"><span>01</span><span>THE IDEA</span></div>
          <div className="belief-grid reveal"><h2>Your agent doesn’t need<br />the <span>whole repo.</span></h2><div><p>Large file dumps and noisy command output fill a conversation with details the agent may not need. Repeated reads add more of the same.</p><p>TokGuard makes repository context smaller and more useful: a compact map, targeted search, careful reads, and cleaner command results.</p></div></div>
          <div className="belief-ribbon"><span>LESS SCANNING</span><i>✳</i><span>BETTER SIGNAL</span><i>✳</i><span>MORE ROOM TO BUILD</span><i>✳</i><span>LESS SCANNING</span><i>✳</i><span>BETTER SIGNAL</span></div>
        </section>

        <section className="proof-section" id="proof">
          <div className="page-width">
            <div className="section-overline"><span>02</span><span>ONE TASK, FOLLOWED THROUGH</span></div>
            <div className="section-intro reveal"><h2>See a task<br /><span>find its path.</span></h2><p>Instead of sweeping every file into the conversation, the agent can move from a small outline to one symbol and then a targeted read.</p></div>
            <ProofScene />
          </div>
        </section>

        <section className="workflow-section page-width" id="how">
          <div className="section-overline"><span>03</span><span>HOW TOKGUARD WORKS</span></div>
          <div className="section-intro reveal"><h2>Follow the thread.<br /><span>Skip the noise.</span></h2><p>Four practical tools help the agent orient, inspect, and act without dragging the whole repository into every turn.</p></div>
          <WorkflowScene />
        </section>

        <section className="benchmark-section" id="savings">
          <div className="page-width">
            <div className="section-overline"><span>04</span><span>MEASURED IN A BENCHMARK</span></div>
            <div className="benchmark-layout">
              <div className="benchmark-copy reveal"><h2>More room<br />for the <span>work.</span></h2><p>Across five sample coding tasks, TokGuard reduced measured input tokens by about <strong>62.5%</strong>.</p><p className="benchmark-caveat">One benchmark, not a guarantee. Actual savings vary with the task, repository, and how the agent uses TokGuard.</p></div>
              <div className="benchmark-card reveal" aria-label="Benchmark comparison: 5,227 baseline input tokens compared with 1,962 TokGuard input tokens">
                <div className="benchmark-card-top"><span>INPUT TOKENS / 5 TASKS</span><span className="benchmark-tag">LOCAL BENCHMARK</span></div>
                <div className="benchmark-result"><strong>−62.5<span>%</span></strong><span>approx. fewer input tokens</span></div>
                <div className="bar-group"><div className="bar-label"><span>Baseline workflow</span><b>5,227</b></div><div className="bar-track"><i className="bar-baseline" /></div></div>
                <div className="bar-group"><div className="bar-label"><span>With TokGuard</span><b>1,962</b></div><div className="bar-track"><i className="bar-tokguard" /></div></div>
                <div className="benchmark-card-foot"><span>5 sample coding tasks · input tokens</span><a href="https://github.com/Sarthak-madan334/tokguard/tree/main/bench" target="_blank" rel="noreferrer">Explore benchmark ↗</a></div>
              </div>
            </div>
          </div>
        </section>

        <section className="agents-section page-width" id="agents">
          <div className="section-overline"><span>05</span><span>MADE FOR CODING AGENTS</span></div>
          <div className="section-intro reveal"><h2>One setup.<br /><span>Your usual tools.</span></h2><p>TokGuard connects through MCP and adds concise project guidance for compatible coding agents.</p></div>
          <div className="agent-grid">{agents.map((agent, index) => <article className="agent-card reveal" key={agent.name} style={{ "--agent-order": index } as CSSProperties}><div className={`agent-symbol agent-symbol-${index}`} aria-hidden="true">{agent.initials}</div><div className="agent-copy"><span className="agent-type">{agent.type}</span><h3>{agent.name}</h3><p>{agent.body}</p><span className="agent-supported"><i /> SUPPORTED</span></div><span className="agent-arrow" aria-hidden="true">↗</span></article>)}</div>
        </section>

        <section className="install-section page-width" id="install">
          <div className="install-panel reveal"><div className="install-constellation" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /><svg viewBox="0 0 500 500"><path d="M45 335 150 220l77 41 112-140 106 160"/><path d="m150 220 48-110 100 10"/></svg></div><div className="install-content"><div className="section-overline"><span>06</span><span>GET STARTED</span></div><h2>Put your context<br />on a <span>diet.</span></h2><p>One PowerShell command installs the TokGuard MCP connection and the guidance your agents need.</p><div className="install-command"><div><span>POWERSHELL</span><code>npx -y tokguard@latest setup</code></div><CopyCommand command="npx -y tokguard@latest setup" /></div><div className="install-after"><span>Then restart your coding agent.</span><a href="https://github.com/Sarthak-madan334/tokguard" target="_blank" rel="noreferrer">View source on GitHub ↗</a></div></div></div>
          <div className="install-steps"><article><span>01</span><div><b>Run the command</b><p>Use PowerShell from any folder.</p></div></article><article><span>02</span><div><b>Restart the agent</b><p>TokGuard appears in its available tools.</p></div></article><article><span>03</span><div><b>Start with a map</b><p>Ask the agent to map the repository first.</p></div></article></div>
          <div className="global-install"><span>Prefer a global command?</span><code>npm install -g tokguard@latest</code><span>then run <code>tokguard setup</code></span></div>
        </section>

        <section className="limits-section page-width">
          <div className="section-overline"><span>07</span><span>HONEST LIMITS</span></div>
          <div className="limits-grid reveal"><h2>Smaller context.<br /><span>Clear expectations.</span></h2><div><p>TokGuard reduces unnecessary repository and command output. It can’t control hidden model reasoning, and savings depend on the agent following its instructions.</p><a href="https://github.com/Sarthak-madan334/tokguard#known-limits" target="_blank" rel="noreferrer">Read project notes <span aria-hidden="true">↗</span></a></div></div>
        </section>
      </main>

      <footer className="site-footer"><div className="footer-main page-width"><Logo /><span>Less context. More room to think.</span><nav aria-label="Footer navigation"><a href="#how">How it works</a><a href="#savings">Savings</a><a href="#install">Install</a><a href="https://github.com/Sarthak-madan334/tokguard" target="_blank" rel="noreferrer">GitHub ↗</a></nav><MotionToggle /></div><div className="footer-bottom page-width"><span>© 2026 TokGuard</span><span>Open source · Your repository stays on your machine</span></div></footer>
    </>
  );
}
