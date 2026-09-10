import type { ComponentProps } from "react";

export type ButtonProps = ComponentProps<"button">;

export function Button({ type = "button", ...props }: ButtonProps) {
  return <button type={type} {...props} />;
}
