// Print the report HTML to PDF with headless Chrome.
// Usage: node print_pdf.mjs <input.html> <output.pdf> <cover|body>
// Requires puppeteer or puppeteer-core resolvable via NODE_PATH; CHROME_PATH overrides the browser.
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
let puppeteer;
try {
  puppeteer = require("puppeteer-core");
} catch {
  puppeteer = require("puppeteer");
}

const [input, output, mode] = process.argv.slice(2);
const chrome = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const footer = `
  <div style="width:100%; font-family:Helvetica,Arial,sans-serif; font-size:7.5pt; color:#5f6b77;
              padding:0 15mm; display:flex; justify-content:space-between;">
    <span>DDM501 · Individual Assignment 2 · ML Pipeline Design &amp; MLOps Analysis</span>
    <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
  </div>`;

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil: "networkidle0" });
  const hide = mode === "cover" ? "body > *:not(.cover) { display: none !important; }" : ".cover { display: none !important; } h1.unnumbered#executive-summary { break-before: auto; }";
  await page.addStyleTag({ content: hide });
  await page.pdf({
    path: output,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: mode !== "cover",
    headerTemplate: "<div></div>",
    footerTemplate: footer,
  });
} finally {
  await browser.close();
}
