import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

/**
 * The harness is not part of the application, which is Python and tested with
 * pytest. The orchestrator's own tests get their own run: `npm run test` from
 * this directory.
 */
export default defineConfig({
  test: {
    root: fileURLToPath(new URL(".", import.meta.url)),
    include: ["**/*.test.mts"],
  },
});
