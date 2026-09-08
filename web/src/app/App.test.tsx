import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

const paths = ["/", "/devices", "/alerts", "/inventory", "/settings"];

describe("Stage 1 application shell", () => {
  it("renders accessible navigation and the dashboard boundary", () => {
    render(<App />);
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Not implemented in Stage 1")).toBeInTheDocument();
    expect(screen.queryByText(/device count|online|offline|healthy/i)).not.toBeInTheDocument();
  });

  it.each(paths)("renders the route boundary for %s", (path) => {
    window.history.pushState({}, "", path);
    render(<App />);
    const label = path === "/" ? "Dashboard" : path.slice(1)[0].toUpperCase() + path.slice(2);
    expect(screen.getByRole("heading", { name: label })).toBeInTheDocument();
  });

  it("cycles the persistent theme mode", () => {
    render(<App />);
    const button = screen.getByRole("button", { name: /switch theme/i });
    fireEvent.click(button);
    expect(button).toHaveTextContent("Theme: light");
    expect(window.localStorage.getItem("device-watch-theme")).toBe("light");
  });
});
