// Extends expect() with @testing-library/jest-dom matchers (toBeInTheDocument, …).
import "@testing-library/jest-dom";
import { TextDecoder, TextEncoder } from "util";

// jsdom omits TextEncoder/TextDecoder, which @tanstack/react-router's core imports.
// Provide the Node implementations so router-aware tests can load.
if (typeof globalThis.TextEncoder === "undefined") {
  Object.assign(globalThis, { TextEncoder, TextDecoder });
}

// jsdom doesn't implement scrollTo; the router's scroll restoration calls it.
if (typeof window !== "undefined" && typeof window.scrollTo !== "function") {
  window.scrollTo = () => {};
}
