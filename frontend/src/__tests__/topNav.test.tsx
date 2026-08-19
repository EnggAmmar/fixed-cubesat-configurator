import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("../scene/SceneCanvas", () => ({
  default: function SceneCanvasMock() {
    return <div data-testid="scene-canvas" />;
  },
}));

import App from "../App";
import { MissionProvider } from "../state/mission";
import TopNav from "../ui/TopNav";

test("TopNav renders title and route links", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <TopNav />
    </MemoryRouter>,
  );

  expect(screen.getByAltText("CubeSat Mission Configurator logo")).toHaveAttribute(
    "src",
    "/branding/cubesat-logo-small.png",
  );
  expect(screen.getByText("CubeSat Mission Configurator")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Mission Setup" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: "Solver Trace" })).toHaveAttribute(
    "href",
    "/solver-trace",
  );
  expect(screen.getByRole("link", { name: "Help" })).toHaveAttribute("href", "/help");
  expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact");
});

test("index.html declares CubeSat favicon and app icons", () => {
  const html = readFileSync(join(process.cwd(), "index.html"), "utf-8");

  expect(html).toContain('<link rel="icon" type="image/x-icon" href="/favicon.ico" />');
  expect(html).toContain(
    '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />',
  );
  expect(html).toContain(
    '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />',
  );
  expect(html).toContain(
    '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />',
  );
  expect(html).toContain('<link rel="manifest" href="/site.webmanifest" />');
  expect(html).toContain("<title>CubeSat Mission Configurator</title>");
});

test("App renders Help route", async () => {
  render(
    <MemoryRouter initialEntries={["/help"]}>
      <MissionProvider>
        <App />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Help" })).toBeInTheDocument();
});

test("App renders Contact route", async () => {
  render(
    <MemoryRouter initialEntries={["/contact"]}>
      <MissionProvider>
        <App />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "Contact" })).toBeInTheDocument();
});
