import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export default function WizardShell({
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
    <div className="wizard" data-testid={testId}>
      <div className="wizardHeader">
        <div className="brand">
          <img
            className="brandLogo"
            src="/branding/cubesat-logo-small.png"
            alt="CubeSat Mission Configurator logo"
          />
          <div>
            <div className="brandText">CubeSat Configurator</div>
          </div>
        </div>

        <h1 className="h1">{title}</h1>
        {subtitle ? <p className="subtitle">{subtitle}</p> : null}
      </div>

      <div className="wizardPanel">{children}</div>

      <div className="wizardFooter">
        {backTo ? (
          <Link className="btn btnGhost" to={backTo}>
            Back
          </Link>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}
