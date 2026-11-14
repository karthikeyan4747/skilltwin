// Tiny shared state with change listeners (AI mode badge, cross-view hints).
const listeners = new Set();

export const state = {
  aiOffline: false,
  assessSkill: null,
};

export function setState(patch) {
  Object.assign(state, patch);
  listeners.forEach((fn) => fn(state));
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
