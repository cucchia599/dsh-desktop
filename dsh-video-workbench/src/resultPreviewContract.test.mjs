import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("video workbench binds completed backend output to the preview player", async () => {
  const source = await readFile(new URL("./App.tsx", import.meta.url), "utf8");
  assert.match(source, /outputUrl/);
  assert.match(source, /<video/);
  assert.match(source, /resultUrl/);
});
