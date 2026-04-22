import "@testing-library/jest-dom";

import { setStoredSession } from "../app/sessionStore";

Object.defineProperty(window, "scrollTo", {
  value: () => {},
  writable: true,
});

afterEach(() => {
  window.localStorage.clear();
  setStoredSession(null);
});
