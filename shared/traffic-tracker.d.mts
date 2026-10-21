export const OPT_OUT_KEY: string;
export function pagePath(site: 'space' | 'video', input: string): string | null;
export function optedOut(): boolean;
export function setOptOut(value: boolean): void;
export function createPageTracker(options: { site: 'space' | 'video'; endpoint: string; enabled?: boolean; ignore?: () => boolean }): { track(path: string): void; stop(): void };
