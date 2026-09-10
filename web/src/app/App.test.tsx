import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "./App";

const routeCases = [
  { path: "/", label: "Dashboard" },
  { path: "/devices", label: "Devices" },
  { path: "/alerts", label: "Alerts" },
  { path: "/inventory", label: "Inventory" },
  { path: "/settings", label: "Settings" },
] as const;

describe("Stage 1 application shell", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
    window.localStorage.clear();
  });

  it("renders the five approved navigation links", () => {
    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: "Primary navigation",
    });
    const links = within(navigation).getAllByRole("link");
    expect(links).toHaveLength(5);
    routeCases.forEach(({ path, label }) => {
      expect(within(navigation).getByRole("link", { name: label })).toHaveAttribute(
        "href",
        path,
      );
    });
    expect(screen.queryByText(/device count|online|offline|healthy/i)).not.toBeInTheDocument();
  });

  it.each(routeCases)(
    "renders only the $label empty state and marks its link current",
    ({ path, label }) => {
      window.history.pushState({}, "", path);
      render(<App />);

      const page = screen.getByRole("main");
      expect(page.children).toHaveLength(2);
      expect(within(page).getByRole("heading", { name: label })).toBeInTheDocument();
      expect(within(page).getByText("Not implemented in Stage 1")).toBeInTheDocument();
      expect(within(page).queryByText("Device Watch / Stage 1")).not.toBeInTheDocument();

      routeCases.forEach(({ label: linkLabel }) => {
        const link = screen.getByRole("link", { name: linkLabel });
        if (linkLabel === label) {
          expect(link).toHaveAttribute("aria-current", "page");
        } else {
          expect(link).not.toHaveAttribute("aria-current");
        }
      });
    },
  );

  it("cycles the persistent theme mode", () => {
    render(<App />);
    const button = screen.getByRole("button", { name: /switch theme/i });

    fireEvent.click(button);
    expect(button).toHaveTextContent("Theme: light");
    expect(window.localStorage.getItem("device-watch-theme")).toBe("light");

    fireEvent.click(button);
    expect(button).toHaveTextContent("Theme: dark");
    expect(window.localStorage.getItem("device-watch-theme")).toBe("dark");

    fireEvent.click(button);
    expect(button).toHaveTextContent("Theme: system");
    expect(window.localStorage.getItem("device-watch-theme")).toBe("system");
  });
});
