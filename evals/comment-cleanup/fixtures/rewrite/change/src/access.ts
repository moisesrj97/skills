import type { User } from "./types.ts";

// Whether the user has admin rights
export function flag(u: User): boolean {
  return u.roles.includes("admin");
}
