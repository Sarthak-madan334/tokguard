import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — TokGuard",
  description: "How the TokGuard website handles information when you visit.",
};

export default function PrivacyPolicyPage() {
  return (
    <main className="page-width section-pad">
      <article style={{ maxWidth: 760, marginInline: "auto" }}>
        <p className="eyebrow">Legal</p>
        <h1>Privacy policy</h1>
        <p>Effective November 18, 2026</p>

        <h2>About this policy</h2>
        <p>
          This policy covers the TokGuard website at tokguard.vercel.app, the TokGuard command-line
          tool (CLI), and how this project uses GitHub. It explains what the project handles and
          what stays on your device.
        </p>

        <h2>Information collected by this website</h2>
        <p>
          The website does not ask you to create an account or submit personal information.
          It has no contact forms, advertising trackers, or site analytics configured in the
          application. The site does not use cookies for analytics or advertising.
        </p>

        <h2>TokGuard CLI and your files</h2>
        <p>
          The CLI runs on your computer. It reads repository files and command output when you
          use its commands, and keeps its configuration, maps, task/session history, and generated
          handoffs in the local project&apos;s <code>.tokguard</code> directory. Full command output
          may be saved under <code>.tokguard/raw</code>. This data is not sent to TokGuard servers;
          the project does not operate a service that receives it. If you share logs, handoffs,
          or repository content yourself, the receiving service&apos;s privacy practices apply.
          When you use TokGuard with an AI agent, command output and requested file excerpts are
          returned to that agent; its provider may process them under its own privacy terms.
        </p>

        <h2>CLI network requests and updates</h2>
        <p>
          When installed globally, the CLI checks the npm registry for a newer TokGuard version
          and can install that update automatically. If the required Python MCP dependency is
          missing, the launcher may also install it from the Python Package Index. These requests
          are for package metadata or software packages; TokGuard does not include repository
          contents in those requests. npm or PyPI may process technical request information under
          their own policies. You can disable the automatic version check by setting
          <code> TOKGUARD_AUTO_UPDATE=0</code> or <code>TOKGUARD_AUTO_UPDATE=false</code>.
        </p>

        <h2>GitHub and public project activity</h2>
        <p>
          TokGuard&apos;s source code and issue tracker are hosted on GitHub. Visiting the repository,
          downloading releases, or opening an issue is handled by GitHub. Issues and comments in
          this public repository can be visible to anyone, so do not post secrets or sensitive
          personal information there. See the{" "}
          <a href="https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement" target="_blank" rel="noreferrer">
            GitHub Privacy Statement
          </a>
          .
        </p>

        <h2>Hosting and technical information</h2>
        <p>
          The website is hosted on Vercel. Like other hosting providers, Vercel may process
          technical request information, such as your IP address, browser details, and the
          time of a request, to deliver, secure, and troubleshoot the website. Vercel handles
          that information under its own policies. See the{" "}
          <a href="https://vercel.com/legal/privacy-policy" target="_blank" rel="noreferrer">
            Vercel Privacy Policy
          </a>
          .
        </p>

        <h2>Links to other services</h2>
        <p>
          TokGuard may run commands that you choose, and those commands can contact other
          services independently. This policy does not cover those commands or services.
        </p>

        <h2>Changes and contact</h2>
        <p>
          This policy may be updated when the website changes. Questions about this policy can
          be raised in the project&apos;s{" "}
          <a href="https://github.com/Sarthak-madan334/tokguard/issues" target="_blank" rel="noreferrer">
            GitHub issues
          </a>
          . Please avoid sharing sensitive personal information in a public issue.
        </p>
      </article>
    </main>
  );
}
