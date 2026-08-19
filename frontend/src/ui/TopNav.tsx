import { NavLink } from "react-router-dom";

type TopNavLink = {
  to: string;
  label: string;
  end?: boolean;
};

const links: TopNavLink[] = [
  { to: "/", label: "Mission Setup", end: true },
  { to: "/solver-trace", label: "Solver Trace" },
  { to: "/help", label: "Help" },
  { to: "/contact", label: "Contact" },
];

export default function TopNav() {
  return (
    <nav className="topNav" aria-label="Top navigation">
      <div className="topNavBrand">
        <img
          className="topNavLogo"
          src="/branding/cubesat-logo-small.png"
          alt="CubeSat Mission Configurator logo"
        />
        <div className="topNavTitle">CubeSat Mission Configurator</div>
      </div>
      <div className="topNavLinks">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => `topNavLink${isActive ? " topNavLinkActive" : ""}`}
          >
            {l.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
