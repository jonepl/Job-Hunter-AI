/** Jest + React Testing Library (ui-spec §9). CJS config, jsdom environment. */
module.exports = {
  testEnvironment: "jsdom",
  roots: ["<rootDir>/src", "<rootDir>/tests"],
  setupFilesAfterEnv: ["<rootDir>/tests/setup.ts"],
  moduleNameMapper: {
    // CSS imports carry no behavior in unit tests — stub them.
    "\\.(css)$": "identity-obj-proxy",
  },
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      { tsconfig: { jsx: "react-jsx", esModuleInterop: true } },
    ],
  },
  testMatch: ["**/*.test.ts", "**/*.test.tsx"],
};
