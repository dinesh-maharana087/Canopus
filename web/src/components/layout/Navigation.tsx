import { NavLink } from "react-router";

import { routes } from "../../app/routes";

export function Navigation() {
  return (
    <nav aria-label="Primary navigation">
      <ul className="navigation-list">
        {routes.map((route) => (
          <li key={route.path}>
            <NavLink
              end={route.path === "/"}
              className={({ isActive }) => (isActive ? "active" : undefined)}
              to={route.path}
            >
              {route.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
