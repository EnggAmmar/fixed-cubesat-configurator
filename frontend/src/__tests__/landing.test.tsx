import { render, screen } from "@testing-library/react";
import { test, expect } from "vitest";
import { MemoryRouter } from "react-router-dom";

import MissionFamilyPage from "../pages/MissionFamilyPage";
import { MissionProvider } from "../state/mission";

test("renders mission family landing heading", () => {
  render(
    <MemoryRouter>
      <MissionProvider>
        <MissionFamilyPage />
      </MissionProvider>
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "Select Mission Family" })).toBeInTheDocument();
});
