import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export default function SolverTraceShell({
  title,
  subtitle,
  children,
  backTo,
  testId,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  backTo?: string;
  testId?: string;
}) {
  return (
    <div className="solverTraceShell" data-testid={testId}>
      <div className="solverTraceHeader">
        <div>
          <div className="solverTraceKicker">Technical Dashboard</div>
          <h1 className="solverTraceTitle">{title}</h1>
          {subtitle ? <p className="solverTraceSubtitle">{subtitle}</p> : null}
        </div>

        {backTo ? (
          <div className="solverTraceNav">
            <Link className="solverTraceBack" to={backTo}>
              Back to Results
            </Link>
          </div>
        ) : null}
      </div>

      <div className="solverTracePanel">{children}</div>
    </div>
  );
}

