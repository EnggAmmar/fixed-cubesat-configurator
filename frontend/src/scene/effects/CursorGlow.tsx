import { useEffect, useState } from "react";

export function CursorGlow() {
  const [pos, setPos] = useState({ x: 50, y: 50 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      setPos({ x, y });
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <div
      style={{
        pointerEvents: "none",
        position: "fixed",
        inset: 0,
        background: `radial-gradient(circle at ${pos.x}% ${pos.y}%, rgba(120,180,255,0.08), transparent 18%)`,
        mixBlendMode: "screen",
        zIndex: 1,
      }}
    />
  );
}

