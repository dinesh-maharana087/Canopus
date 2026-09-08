import { BrowserRouter, Route, Routes } from "react-router";

import { AppShell } from "../components/layout/AppShell";
import { ThemeProvider } from "../theme/ThemeProvider";
import { pageFor, routes } from "./routes";

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            {routes.map((route) => (
              <Route key={route.path} path={route.path} element={pageFor(route.label)} />
            ))}
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
