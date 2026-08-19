import { Link } from "react-router-dom";
import WizardShell from "../components/WizardShell";

export default function HelpPage() {
  return (
    <WizardShell
      title="Help"
      subtitle="Quick reference for the mission setup wizard and solver trace."
      testId="page-help"
      backTo="/"
    >
      <div className="muted" style={{ lineHeight: 1.55 }}>
        This is a placeholder help page. Add usage docs, FAQ, and troubleshooting guidance here.
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link className="btn btnGhost" to="/solver-trace">
          Open Solver Trace
        </Link>
        <Link className="btn btnGhost" to="/contact">
          Contact
        </Link>
      </div>
    </WizardShell>
  );
}
