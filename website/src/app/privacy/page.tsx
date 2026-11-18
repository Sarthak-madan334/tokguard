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
          This policy describes the TokGuard website at tokguard.vercel.app. It does not cover
          the TokGuard command-line tool, the GitHub repository, or other services that have
          their own privacy practices.
        </p>

        <h2>Information collected by this website</h2>
        <p>
          The website does not ask you to create an account or submit personal information.
          It has no contact forms, advertising trackers, or site analytics configured in the
          application. The site does not use cookies for analytics or advertising.
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
          The site links to GitHub for the source code, issues, and documentation. When you
          follow those links, GitHub&apos;s privacy practices apply. Review the{" "}
          <a href="https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement" target="_blank" rel="noreferrer">
            GitHub Privacy Statement
          </a>
          .
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
