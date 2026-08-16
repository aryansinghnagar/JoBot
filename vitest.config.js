import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Applies the React JSX automatic runtime to the GUI component tests while
// leaving the pure-JS contract tests in tests/npm untouched.
export default defineConfig({
  plugins: [react()],
  test: {
    include: ["tests/npm/**/*.test.js", "gui/tests/**/*.test.{js,jsx}"],
  },
});