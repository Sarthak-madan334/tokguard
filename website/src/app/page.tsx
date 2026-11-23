import {
  CopyCommand,
  MobileMenu,
  ProofScene,
  ScrollEffects,
  TerminalDemo,
} from "./experience";

const agents = [
  { mark: "◈", name: "Codex", description: "Add TokGuard tools and repository guidance to your Codex workflow." },
  { mark: "✳", name: "Claude Code", description: "Use compact maps, targeted reads, and quieter command output." },
  { mark: "✦", name: "Antigravity", description: "Register TokGuard as an MCP server for your projects." },
  { mark: "+", name: "Other MCP clients", description: "Connect from another client that supports the Model Context Protocol." },
];

function Logo() {
  return (
    <a className="wordmark" href="#top" aria-label="TokGuard home">
      <svg viewBox="0 0 34 34" aria-hidden="true"><path d="M17 2.7 29 7v9.2c0 7.5-5 12.3-12 15.1C10 28.5 5 23.7 5 16.2V7l12-4.3Z" /><path d="m11.2 17.2 3.7 3.7 7.9-8" /></svg>
      <span>tokguard<span className="wordmark-stop">.</span></span>
    </a>
  );
}

export default function Home() {
  return (
    <>
      <ScrollEffects />
      <a className="skip-link" href="#main">Skip to content</a>
      <div className="announcement">
        <p>Open source <span aria-hidden="true">·</span> Works with Codex, Claude Code, and Antigravity</p>
        <a href="https://github.com/Sarthak-madan334/tokguard" target="_blank" rel="noreferrer">Visit GitHub <span aria-hidden="true">↗</span></a>
      </div>

      <header className="site-header">
        <div className="page-width header-inner">
          <Logo />
          <nav className="desktop-nav" aria-label="Main navigation">
            <a href="#how">How it works</a><a href="#whats-new">TokGuard 2.0</a><a href="#results">Results</a><a href="#agents">Agents</a>
          </nav>
          <a className="button button-primary header-cta" href="#install">Get started</a>
          <MobileMenu />
        </div>
      </header>

      <main id="main" tabIndex={-1}>
        <section className="hero-section" id="top">
          <div className="page-width hero-inner">
            <p className="eyebrow">A calmer way to explore a codebase</p>
            <h1>Less context.<br /><em>More coding.</em></h1>
            <p className="hero-lede">TokGuard helps your coding agent find the right files, read only what matters, and keep command output under control.</p>
            <div className="hero-actions">
              <a className="button button-primary" href="#install">Set it up <span aria-hidden="true">↗</span></a>
              <a className="button button-secondary" href="#how">See how it works <span aria-hidden="true">↓</span></a>
            </div>
            <TerminalDemo />
          </div>
        </section>

        <section className="idea-section section-pad" id="idea">
          <div className="page-width idea-grid">
            <div className="section-copy reveal">
              <p className="eyebrow">A more focused starting point</p>
              <h2>Your agent doesn’t need<br className="desktop-break" /> the whole repo.</h2>
              <p>Large file dumps and noisy command output can fill a conversation with details the agent may not need. Repeated reads add more of the same.</p>
              <p>TokGuard offers a compact map, targeted search, careful reads, and cleaner command results, so the conversation can stay focused on the task.</p>
            </div>
            <div className="context-card reveal" aria-label="Strong benchmark token comparison">
              <div className="context-card-head"><span>Strong benchmark</span><span>Measured tokens</span></div>
              <div className="bar-row"><div className="bar-label"><span>Without TokGuard</span><strong>47,383</strong></div><div className="bar-track"><span className="bar-full" /></div></div>
              <div className="bar-row"><div className="bar-label"><span>With TokGuard</span><strong>17,295</strong></div><div className="bar-track"><span className="bar-focused" /></div></div>
              <p className="context-caption">Token count calculated from the reported 63.5% reduction.</p>
            </div>
          </div>
        </section>

        <section className="how-section section-pad" id="how">
          <div className="page-width">
            <div className="section-heading reveal">
              <p className="eyebrow">A task, followed through</p>
              <h2>See a task find its path.</h2>
              <p>Start with the request. Follow the useful context from a repository map to the implementation.</p>
            </div>
            <ProofScene />
          </div>
        </section>

        <section className="tools-section section-pad">
          <div className="page-width">
            <div className="section-heading reveal">
              <p className="eyebrow">Four tools, one workflow</p>
              <h2>Just enough to keep moving.</h2>
            </div>
            <div className="tool-grid">
              <article className="tool-card reveal"><span className="tool-icon" aria-hidden="true">⌘</span><h3>Map</h3><p>Get a compact outline of files and symbols before opening code.</p><code>tg map</code></article>
              <article className="tool-card reveal"><span className="tool-icon" aria-hidden="true">⌕</span><h3>Find</h3><p>Locate a symbol or pattern and see a small amount of nearby context.</p><code>tg find calculate_total</code></article>
              <article className="tool-card reveal"><span className="tool-icon" aria-hidden="true">↙</span><h3>Read</h3><p>Open a relevant line range or symbol body instead of a whole file.</p><code>tg read src/app.py 42-58</code></article>
              <article className="tool-card reveal"><span className="tool-icon" aria-hidden="true">›_</span><h3>Run</h3><p>Filter progress noise and keep useful summaries and errors visible.</p><code>tg run -- pytest -q</code></article>
            </div>
          </div>
        </section>

        <section className="release-section section-pad" id="whats-new">
          <div className="page-width">
            <div className="release-intro reveal">
              <div>
                <p className="eyebrow">A new chapter · TokGuard 2.0</p>
                <h2>Keep the agent<br />with the task.</h2>
                <p>TokGuard 2.0 brings planning, drift checks, verification, and automatic updates into the same focused workflow.</p>
              </div>
              <div className="release-stamp" aria-label="TokGuard version 2.0">
                <span className="release-stamp-ring"><span>2.0</span></span>
                <small>THE TASK, START TO FINISH</small>
              </div>
            </div>
            <div className="release-grid">
              <article className="release-card reveal">
                <div className="release-card-top"><span>01 / PLAN</span><span aria-hidden="true">↗</span></div>
                <h3>A task manager for the original request</h3>
                <p>TokGuard locks the request, then helps the agent make a clear work order with scope, ordered steps, and checkable acceptance criteria.</p>
                <div className="release-flow" aria-label="Prompt to work order to steps"><span>Prompt</span><i>→</i><span>Work order</span><i>→</i><span>Steps</span></div>
              </article>
              <article className="release-card reveal">
                <div className="release-card-top"><span>02 / DRIFT</span><span aria-hidden="true">⌁</span></div>
                <h3>Notice scope drift as it happens</h3>
                <p>Baseline-aware checks compare changes with the approved scope and steps. When work drifts, TokGuard explains why and points the agent back.</p>
                <div className="release-status"><span className="release-status-dot" /> Scope check <strong>ON TRACK</strong></div>
              </article>
              <article className="release-card reveal">
                <div className="release-card-top"><span>03 / FINISH</span><span aria-hidden="true">✓</span></div>
                <h3>Verify, hand off, keep going</h3>
                <p>Run the declared verification and acceptance checks. When a session budget fills, TokGuard saves context and rolls into a fresh session.</p>
                <div className="release-checks"><span><b>✓</b> Acceptance</span><span><b>✓</b> Verification</span><span><b>↻</b> Handoff</span></div>
              </article>
              <article className="release-card release-card-update reveal">
                <div className="release-card-top"><span>04 / STAY CURRENT</span><span aria-hidden="true">↻</span></div>
                <h3>Automatic updates at launch</h3>
                <p>With TokGuard 2.0.1, a global install checks npm when it starts. If a newer release is available, it updates and resumes your command. <code>npx tokguard@latest</code> already requests the latest release.</p>
                <div className="release-update-note">Older global installs need one update to 2.0.1 to receive the updater.</div>
              </article>
            </div>
          </div>
        </section>

        <section className="results-section section-pad" id="results">
          <div className="page-width results-grid">
            <div className="result-stat reveal"><p className="eyebrow">Strong benchmark</p><p className="stat-value">−63.5%</p><p>fewer input tokens used with TokGuard</p></div>
            <div className="result-detail reveal">
              <h2>More room<br />for the work.</h2>
              <div className="benchmark-card">
                <div className="benchmark-bar-row"><div><span>Without TokGuard</span><strong>47,383 tokens</strong></div><div className="benchmark-track"><i className="benchmark-before" /></div></div>
                <div className="benchmark-bar-row"><div><span>With TokGuard</span><strong>17,295 tokens</strong></div><div className="benchmark-track"><i className="benchmark-after" /></div></div>
              </div>
              <p className="benchmark-method">8–10 repositories · 10 tasks per repository · 5 runs per task · 800–1,000 total runs across two modes</p>
              <a className="text-link" href="https://github.com/Sarthak-madan334/tokguard/tree/main/bench" target="_blank" rel="noreferrer">Explore the benchmark <span aria-hidden="true">↗</span></a>
            </div>
          </div>
        </section>

        <section className="agents-section section-pad" id="agents">
          <div className="page-width">
            <div className="section-heading reveal">
              <p className="eyebrow">One setup, familiar tools</p>
              <h2>One setup. Your usual tools.</h2>
              <p>Connect TokGuard to the coding agent you already use.</p>
            </div>
            <div className="agent-grid">
              {agents.map((agent) => <article className="agent-card reveal" key={agent.name}>
                <span className="agent-mark" aria-hidden="true">{agent.mark}</span>
                <h3>{agent.name}</h3><p>{agent.description}</p>
                <a href="#install">See setup steps <span aria-hidden="true">↗</span></a>
              </article>)}
            </div>
          </div>
        </section>

        <section className="compare-section section-pad">
          <div className="page-width">
            <div className="section-heading reveal"><p className="eyebrow">A useful distinction</p><h2>Why not just grep?</h2><p>Each tool has a place. TokGuard helps shape what an agent receives across a few common repository tasks.</p></div>
            <div className="comparison-wrap reveal">
              <table className="comparison-table">
                <caption>What each approach typically returns to a coding conversation</caption>
                <thead><tr><th scope="col">Approach</th><th scope="col">What it returns</th><th scope="col">Context size</th></tr></thead>
                <tbody>
                  <tr><th scope="row">grep / ripgrep</th><td>Matching lines from a search pattern</td><td>Depends on the match and command options</td></tr>
                  <tr><th scope="row">Agent built-in search</th><td>Search results chosen by the client</td><td>Varies by agent and configuration</td></tr>
                  <tr className="comparison-highlight"><th scope="row">TokGuard</th><td>Repo maps, focused matches and reads, filtered command output</td><td>Designed to keep results targeted</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="install-section section-pad" id="install">
          <div className="page-width install-grid">
            <div className="install-copy reveal">
              <p className="eyebrow">Start in a minute</p>
              <h2>Put TokGuard to work.</h2>
              <p>Run setup in PowerShell, restart your coding agent, then start with a map of the repository.</p>
              <ol className="install-steps">
                <li><span>1</span><div><strong>Run the command</strong><p>Setup adds TokGuard’s MCP connection and guidance.</p></div></li>
                <li><span>2</span><div><strong>Restart your agent</strong><p>Let it load the updated configuration.</p></div></li>
                <li><span>3</span><div><strong>Start with a map</strong><p>Ask your agent to run <code>tg map</code>.</p></div></li>
              </ol>
            </div>
            <div className="install-panel reveal">
              <div className="install-panel-head"><span>PowerShell</span><span>Recommended</span></div>
              <div className="install-command"><code>npx -y tokguard@latest setup</code><CopyCommand command="npx -y tokguard@latest setup" /></div>
              <div className="global-install">
                <div className="global-install-head"><p>Prefer a global install?</p><CopyCommand command={'npm install -g tokguard@latest; tokguard setup'} /></div>
                <code>npm install -g tokguard@latest</code><br /><code>tokguard setup</code>
              </div>
              <div className="uninstall-info">
                <p>Uninstall TokGuard</p>
                <div className="uninstall-info-command"><code>npm uninstall -g tokguard</code><CopyCommand command="npm uninstall -g tokguard" /></div>
                <span>Removes the global package. Project files and agent settings stay in place. For a project-local install, run <code>npm uninstall tokguard</code> in that project.</span>
              </div>
            </div>
          </div>
        </section>

        <section className="limits-section section-pad">
          <div className="page-width limits-card reveal">
            <div><p className="eyebrow">Clear expectations</p><h2>Smaller context.<br />Clear expectations.</h2></div>
            <div><p>TokGuard reduces unnecessary repository and command output. It can’t control hidden model reasoning, and savings depend on the agent following its instructions.</p><a className="text-link" href="https://github.com/Sarthak-madan334/tokguard#known-limits" target="_blank" rel="noreferrer">Read the known limits <span aria-hidden="true">↗</span></a></div>
          </div>
        </section>

      </main>

      <footer className="site-footer">
        <div className="page-width">
          <div className="footer-grid">
            <div className="footer-brand"><Logo /><p>Focused context for coding agents.</p></div>
            <div><h2>Product</h2><a href="#how">How it works</a><a href="#results">Results</a><a href="#agents">Agents</a></div>
            <div><h2>Docs &amp; community</h2><a href="https://github.com/Sarthak-madan334/tokguard" target="_blank" rel="noreferrer">GitHub repository</a><a href="https://github.com/Sarthak-madan334/tokguard/issues" target="_blank" rel="noreferrer">Issues and support</a><a href="https://github.com/Sarthak-madan334/tokguard/tree/main/bench" target="_blank" rel="noreferrer">Benchmark</a></div>
            <div><h2>Legal</h2><a href="/privacy">Privacy policy</a><a href="https://github.com/Sarthak-madan334/tokguard/blob/main/package.json" target="_blank" rel="noreferrer">MIT license</a></div>
          </div>
          <div className="footer-bottom"><Logo /><p>© 2026 TokGuard. Open source.</p></div>
        </div>
      </footer>
    </>
  );
}
