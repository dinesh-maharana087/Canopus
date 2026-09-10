import { Outlet } from "react-router";

import { useTheme, type ThemeMode } from "../../theme/ThemeProvider";
import { Button } from "../ui/Button";
import { Navigation } from "./Navigation";

const themeModes: ThemeMode[] = ["system", "light", "dark"];

export function AppShell() {
  const { mode, setMode } = useTheme();
  const nextMode = themeModes[(themeModes.indexOf(mode) + 1) % themeModes.length];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="brand-kicker">Infrastructure observability</p>
          <div className="brand">Device Watch</div>
        </div>
        <Button
          className="theme-button"
          type="button"
          aria-label={`Switch theme from ${mode} to ${nextMode}`}
          onClick={() => setMode(nextMode)}
        >
          Theme: {mode}
        </Button>
      </header>
      <Navigation />
      <Outlet />
    </div>
  );
}
