import { Link } from "react-router-dom";
import WizardShell from "../components/WizardShell";

export default function ContactPage() {
  return (
    <WizardShell title="Contact" subtitle="How to reach the team." testId="page-contact" backTo="/">
      <div className="muted" style={{ lineHeight: 1.55 }}>
        This is a placeholder contact page. Add an email address, issue tracker link, or support form here.
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link className="btn btnGhost" to="/help">
          Help
        </Link>
      </div>
    </WizardShell>
  );
}

