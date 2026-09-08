import { render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { ThemeProvider, useTheme } from "./ThemeProvider";

function Probe() {
  const { mode } = useTheme();
  return <span>{mode}</span>;
}

describe("theme state", () => {
  beforeEach(() => window.localStorage.clear());

  it("restores the persisted mode", () => {
    window.localStorage.setItem("device-watch-theme", "dark");
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(screen.getByText("dark")).toBeInTheDocument();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
