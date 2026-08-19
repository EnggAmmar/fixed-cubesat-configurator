import { useEffect, useMemo, useRef, useState } from "react";

type DockState = {
  width: number;
  collapsed: boolean;
};

const STORAGE_KEY = "cubesat_dock_v1";

function loadState(): DockState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { width: 520, collapsed: false };
    const parsed = JSON.parse(raw) as Partial<DockState>;
    const width = typeof parsed.width === "number" ? parsed.width : 520;
    const collapsed = Boolean(parsed.collapsed);
    return { width: Math.max(360, Math.min(720, width)), collapsed };
  } catch {
    return { width: 520, collapsed: false };
  }
}

function saveState(state: DockState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

export default function LeftDock({ children }: { children: React.ReactNode }) {
  const initial = useMemo(loadState, []);
  const [width, setWidth] = useState(initial.width);
  const [collapsed, setCollapsed] = useState(initial.collapsed);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const next = { width, collapsed };
    saveState(next);
    document.documentElement.style.setProperty("--dockW", `${collapsed ? 56 : width}px`);
    document.documentElement.style.setProperty("--dockCollapsed", collapsed ? "1" : "0");
  }, [collapsed, width]);

  return (
    <div className={`dock ${collapsed ? "dockCollapsed" : ""}`}>
      <div className="dockHeader">
        <button
          type="button"
          className="dockToggle"
          aria-label={collapsed ? "Expand panel" : "Collapse panel"}
          onClick={() => setCollapsed((c) => !c)}
        >
          {collapsed ? "›" : "‹"}
        </button>

        {!collapsed ? (
          <div className="dockControls">
            <div className="dockLabel">Panel</div>
            <input
              aria-label="Panel width"
              className="dockSlider"
              type="range"
              min={360}
              max={720}
              value={width}
              onChange={(e) => setWidth(Number(e.target.value))}
            />
          </div>
        ) : null}
      </div>

      <div
        ref={scrollRef}
        className="dockScroll"
        onWheelCapture={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
