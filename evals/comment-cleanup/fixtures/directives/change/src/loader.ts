/*
 * Copyright (c) 2026 Example Corp. Licensed under the MIT License.
 */
import { oldLoad } from "./legacy.ts";

// The cache of loaded modules
const cache = new Map<string, unknown>();

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function loadChart(): Promise<any> {
  // Load the chart module lazily
  return import(/* webpackChunkName: "chart" */ "./legacy.ts");
}

export const registry = /*#__PURE__*/ new Map<string, string>();

/* istanbul ignore next */
export function debugDump(): string {
  // Dump the cache size
  return String(cache.size);
}

/**
 * @deprecated Use loadChart instead.
 * @see loadChart
 */
export function load(): string {
  return oldLoad();
}

export function width(el: { offsetWidth: number }): number {
  // @ts-expect-error
  return el.offsetWidht ?? el.offsetWidth;
}
