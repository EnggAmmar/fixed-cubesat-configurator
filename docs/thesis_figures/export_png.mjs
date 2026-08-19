import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const svgs = fs.readdirSync(dir).filter((f) => f.endsWith(".svg"));
const browser = await chromium.launch({ headless: true });
for (const svg of svgs) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 2 });
  const source = fs.readFileSync(path.join(dir, svg), "utf8");
  await page.setContent(`<style>html,body{margin:0;width:1600px;height:900px;overflow:hidden}</style>${source}`);
  // Chromium can rasterize feDropShadow very slowly at 2× on some Windows GPUs.
  // The SVG remains the authoritative vector version; PNG export uses clean flat boxes.
  await page.locator('[filter="url(#shadow)"]').evaluateAll((nodes) =>
    nodes.forEach((node) => node.removeAttribute("filter")),
  );
  await page.locator("svg").screenshot({
    path: path.join(dir, svg.replace(/\.svg$/, ".png")),
    timeout: 30_000,
  });
  await page.close();
}
await browser.close();
console.log(`Exported ${svgs.length} PNG files at 3200 × 1800 px`);
