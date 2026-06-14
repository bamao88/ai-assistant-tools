#!/usr/bin/env node
/**
 * CLI wrapper for markdown-to-cards — bypasses MCP protocol.
 * Usage: node cli.js --input <file> [--output-dir <dir>] [options]
 *        node cli.js --stdin [same options]   # reads markdown from stdin
 * Output: JSON to stdout  { files: [...], total_pages: n, output_dir: "..." }
 */
import path from "path";
import fs from "fs/promises";
import { CARD_STYLE_IDS, COLOR_SCHEME_IDS, DEFAULT_COLOR_SCHEME_ID, renderMarkdownToCards } from "./lib/render.js";

const args = process.argv.slice(2);

function getArg(flag) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : undefined;
}

function hasArg(flag) {
  return args.includes(flag);
}

function printUsage() {
  process.stderr.write([
    "Usage: node cli.js --input <file.md> [--output-dir <dir>] [options]",
    "       node cli.js --stdin [same options]",
    "",
    "Options:",
  "  --base-dir <dir>       Resolve relative Markdown image paths from this directory",
  "  --account <name>       Load card defaults from ~/.xhs/accounts.json for this XHS account",
  "  --accent <color>       Manual accent color override",
  "  --background <color>   Manual body/template background color override",
  "  --text-color <color>   Manual text color override",
    "  --font-size <n>        Body font size in px, default 25",
  "  --cover-bg <path>      Custom template cover background image",
  "  --cover-image <path>   Use image cover style with this image path or URL",
  "  --cover-style <name>   template | image | both",
  "  --cover-template <name> style | default; default keeps the legacy cover while using a themed body",
  `  --style <name>         Template style: ${CARD_STYLE_IDS.join(" | ")}`,
    `  --color-scheme <name>  Legacy-only color scheme: ${COLOR_SCHEME_IDS.join(" | ")}; default ${DEFAULT_COLOR_SCHEME_ID}`,
    "  --chapter-label <text> Header/cover label for themed styles, default 精选长图文",
    "  --cover-variant <name> primary | alt | all for themed cover styles",
    "",
  ].join("\n"));
}

let markdown;
let inputFile;

if (hasArg("--stdin")) {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  markdown = Buffer.concat(chunks).toString("utf-8");
} else {
  inputFile = getArg("--input");
  if (!inputFile) {
    printUsage();
    process.exit(1);
  }
  markdown = await fs.readFile(inputFile, "utf-8");
}

const baseDir = getArg("--base-dir") ||
  (inputFile ? path.dirname(path.resolve(inputFile)) : process.cwd());

const options = {
  account: getArg("--account"),
  output_dir: getArg("--output-dir"),
  base_dir: baseDir,
  accent_color: getArg("--accent"),
  background_color: getArg("--background"),
  text_color: getArg("--text-color"),
  font_size: getArg("--font-size") ? Number(getArg("--font-size")) : undefined,
  cover_bg_path: getArg("--cover-bg"),
  cover_image_path: getArg("--cover-image"),
  cover_style: getArg("--cover-style"),
  cover_template: getArg("--cover-template"),
  style: getArg("--style"),
  color_scheme: getArg("--color-scheme"),
  chapter_label: getArg("--chapter-label"),
  cover_variant: getArg("--cover-variant"),
};

try {
  const result = await renderMarkdownToCards(markdown, options);
  process.stdout.write(JSON.stringify(result) + "\n");
} catch (err) {
  process.stderr.write(`Error: ${err.message}\n`);
  process.exit(1);
}
