import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThemeProvider, useTheme } from "./ThemeProvider";

function Probe() {
  const { mode } = useTheme();
  return <span>{mode}</span>;
}

function installColorSchemePreference(initiallyDark: boolean) {
  let matches = initiallyDark;
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  const mediaQuery = {
    get matches() {
      return matches;
    },
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: (
      type: string,
      listener: (event: MediaQueryListEvent) => void,
    ) => {
      if (type === "change") listeners.add(listener);
    },
    removeEventListener: (
      type: string,
      listener: (event: MediaQueryListEvent) => void,
    ) => {
      if (type === "change") listeners.delete(listener);
    },
    dispatchEvent: () => true,
  } as MediaQueryList;

  vi.spyOn(window, "matchMedia").mockReturnValue(mediaQuery);

  return {
    setDark(nextMatches: boolean) {
      matches = nextMatches;
      const event = {
        matches,
        media: mediaQuery.media,
      } as MediaQueryListEvent;
      listeners.forEach((listener) => listener(event));
    },
  };
}

describe("theme state", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => vi.restoreAllMocks());

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

  it("tracks operating-system color-scheme changes in system mode", () => {
    const colorScheme = installColorSchemePreference(false);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(document.documentElement.dataset.theme).toBe("light");

    act(() => colorScheme.setDark(true));
    expect(document.documentElement.dataset.theme).toBe("dark");

    act(() => colorScheme.setDark(false));
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
