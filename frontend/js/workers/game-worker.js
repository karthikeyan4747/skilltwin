// Grid Game sandbox prelude. Loaded first inside a throwaway Blob worker that then runs the
// learner's JavaScript: no DOM exists in workers and network/script-loading APIs are removed.
"use strict";

const MAX_MOVES = 200;
const DIRECTIONS = new Set(["up", "down", "left", "right"]);
const recorded = [];

self.move = (direction) => {
  if (!DIRECTIONS.has(direction)) {
    throw new Error(`move() expects "up", "down", "left" or "right", not ${JSON.stringify(direction)}`);
  }
  if (recorded.length >= MAX_MOVES) throw new Error(`Too many moves (max ${MAX_MOVES}).`);
  recorded.push(direction);
};

const send = self.postMessage.bind(self);
self.__finish = () => send({ ok: true, moves: recorded });
self.__fail = (error) => send({ ok: false, error: String(error?.message || error), moves: recorded });

for (const name of ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "importScripts", "indexedDB", "caches", "BroadcastChannel", "Worker", "SharedWorker", "postMessage"]) {
  try {
    Object.defineProperty(self, name, { value: undefined, writable: false, configurable: false });
  } catch {
    // Some globals are non-configurable in some browsers; CSP connect-src still blocks network.
  }
}
