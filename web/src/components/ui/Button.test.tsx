import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { Button } from "./Button";

it("defaults to non-submitting button semantics", () => {
  let submissions = 0;
  render(
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submissions += 1;
      }}
    >
      <Button>Change theme</Button>
    </form>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Change theme" }));

  expect(submissions).toBe(0);
});
