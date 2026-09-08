import type { ReactNode } from "react";

import { FoundationPage } from "../pages/FoundationPage";

export const routes = [
  { path: "/", label: "Dashboard" },
  { path: "/devices", label: "Devices" },
  { path: "/alerts", label: "Alerts" },
  { path: "/inventory", label: "Inventory" },
  { path: "/settings", label: "Settings" },
] as const;

export function pageFor(label: string): ReactNode {
  return <FoundationPage title={label} />;
}
