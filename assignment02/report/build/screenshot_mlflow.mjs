// Capture the MLflow UI evidence for Figure 3 as two cropped, print-legible screenshots:
//   mlflow_run_tags.png      champion run: lineage tags + link to the registered version
//   mlflow_registry_v2.png   registry: versions with aliases, and the version-2 tags
// Usage: node screenshot_mlflow.mjs <base_url> <out_dir> <experiment_id> <run_id>
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");
const [base, outDir, expId, runId] = process.argv.slice(2);
const chrome = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const debug = process.env.DEBUG_SHOTS === "1";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function hideAssistant(page) {
  await page.evaluate(() => {
    const close = document.querySelector('button[aria-label="Close"]');
    if (close) close.click();
  });
}

// Bounding box (page coordinates) of the top-most visible leaf element whose text equals `text`
// and that starts below `minY`.
async function boxOf(page, text, minY = 0) {
  return page.evaluate(
    (t, min) => {
      const boxes = [...document.querySelectorAll("*")]
        .filter((n) => n.children.length === 0 && n.textContent.trim() === t && n.offsetParent !== null)
        .map((n) => n.getBoundingClientRect())
        .map((r) => ({ x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height }))
        .filter((b) => b.y > min && b.w > 0)
        .sort((p, q) => p.y - q.y);
      return boxes[0] ?? null;
    },
    text,
    minY,
  );
}

async function open(page, url, width, height) {
  await page.setViewport({ width, height, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: "networkidle0", timeout: 60000 });
  await sleep(3000);
  await hideAssistant(page);
  await sleep(1000);
}

async function clipBetween(page, name, startText, endText, { pad = 12, x = 0, width, extra = 0 } = {}) {
  const a = await boxOf(page, startText);
  const b = a && (await boxOf(page, endText, a.y));
  if (debug) console.log(name, startText, a, endText, b);
  if (!a || !b) throw new Error(`anchor not found for ${name}: ${startText} / ${endText}`);
  const top = Math.max(0, a.y - pad);
  const bottom = b.y + b.h + pad + extra;
  await page.screenshot({
    path: path.join(outDir, name),
    clip: { x, y: top, width: width ?? page.viewport().width - x, height: bottom - top },
  });
  console.log("saved", name);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage();
  await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);

  await open(page, `${base}/#/experiments/${expId}/runs/${runId}`, 1100, 1400);
  if (debug) await page.screenshot({ path: path.join(outDir, "debug_run.png"), fullPage: true });
  await clipBetween(page, "mlflow_run_tags.png", "Tags", "Registered models", { extra: 34, x: 200, width: 890 });

  await open(page, `${base}/#/models/churnguard-classifier`, 1800, 1400);
  // The versions table clips each column (Tags to ~100 px). Re-size the columns we show and hide
  // the ones we do not, so the stored values are readable. Display-only: no data is edited.
  await page.evaluate((layout) => {
    const versionsY = [...document.querySelectorAll("*")].find(
      (n) => n.children.length === 0 && n.textContent.trim() === "Versions",
    ).getBoundingClientRect().y;
    const columnCells = (title) => {
      const leaf = [...document.querySelectorAll("*")].find(
        (n) => n.children.length === 0 && n.textContent.trim() === title && n.getBoundingClientRect().y > versionsY,
      );
      let head = leaf;
      while (head.parentElement && head.parentElement.getBoundingClientRect().width < 3 * head.getBoundingClientRect().width + 200) {
        head = head.parentElement;
      }
      const { x, width } = head.getBoundingClientRect();
      return [...document.querySelectorAll("div")].filter((el) => {
        const r = el.getBoundingClientRect();
        return Math.abs(r.x - x) < 2 && Math.abs(r.width - width) < 2 && el.parentElement.getBoundingClientRect().width > 2 * width;
      });
    };
    const cells = Object.fromEntries(Object.keys(layout).map((t) => [t, columnCells(t)]));
    for (const [title, width] of Object.entries(layout)) {
      for (const el of cells[title]) {
        if (width === 0) {
          el.style.display = "none";
          continue;
        }
        Object.assign(el.style, { flex: `0 0 ${width}px`, width: `${width}px`, maxWidth: `${width}px`, overflow: "visible" });
        for (const s of el.querySelectorAll("span")) Object.assign(s.style, { maxWidth: "none", overflow: "visible" });
      }
    }
    // Tag cells are wrapped differently from their header, so locate them from a tag chip.
    let cell = [...document.querySelectorAll("*")].find(
      (n) => n.children.length === 0 && n.textContent.includes("val_business_cost_per_cust"),
    );
    while (cell.tagName === "SPAN" || getComputedStyle(cell).overflow !== "hidden") cell = cell.parentElement;
    const tagX = cell.getBoundingClientRect().x;
    const cls = cell.className.toString().split(" ").pop();
    const tagHead = columnCells("Tags")[0];
    const tagCells = [...document.getElementsByClassName(cls)].filter(
      (el) => Math.abs(el.getBoundingClientRect().x - tagX) < 2,
    );
    for (const el of [tagHead, ...tagCells].filter(Boolean)) {
      Object.assign(el.style, { flex: "0 0 600px", width: "600px", maxWidth: "600px" });
      for (const s of el.querySelectorAll("span")) Object.assign(s.style, { maxWidth: "none", overflow: "visible" });
    }
  }, { Version: 110, "Registered at": 0, "Created by": 0, Aliases: 240, Description: 0 });
  await sleep(800);
  if (debug) await page.screenshot({ path: path.join(outDir, "debug_registry.png"), fullPage: true });
  // Crop to the version-2 row plus the first line of version 1 (its alias). The header row is
  // not re-laid out, so it is left out.
  const v2 = await boxOf(page, "Version 2", 300);
  const chip = await page.evaluate(() => {
    const leaves = [...document.querySelectorAll("*")].filter(
      (n) => n.children.length === 0 && /^@?\s*(previous_champion|champion|challenger)$/.test(n.textContent.trim()),
    );
    return { right: Math.max(...leaves.map((n) => n.getBoundingClientRect().right)) + window.scrollX };
  });
  const v1 = await boxOf(page, "Version 1", v2.y);
  if (debug) console.log({ v2, v1, chip });
  const left = v2.x - 40;
  await page.screenshot({
    path: path.join(outDir, "mlflow_registry.png"),
    clip: { x: left, y: v2.y - 14, width: chip.right + 36 - left, height: v1.y + v1.h + 5 - (v2.y - 14) },
  });
  console.log("saved mlflow_registry.png");
} finally {
  await browser.close();
}
