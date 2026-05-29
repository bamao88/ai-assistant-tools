import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";
import { CARD_STYLE_IDS, COLOR_SCHEME_IDS, CONFIG, DEFAULT_COLOR_SCHEME_ID, renderMarkdownToCards } from "../lib/render.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(__dirname, "..");
const fixturePath = path.join(projectDir, "test/fixtures/full_coverage.md");
const baseDir = path.dirname(fixturePath);
const outputRoot = path.join(projectDir, "tmp", `theme_regression_${Date.now()}`);

function pngSize(buf) {
  if (buf.toString("ascii", 1, 4) !== "PNG") {
    throw new Error("Not a PNG file");
  }
  return {
    width: buf.readUInt32BE(16),
    height: buf.readUInt32BE(20),
  };
}

async function assertPngSet(result, label) {
  if (!result.files?.length) {
    throw new Error(`${label}: no PNG files generated`);
  }

  const expectedWidth = CONFIG.cssWidth * CONFIG.deviceScaleFactor;
  const expectedHeight = CONFIG.cssHeight * CONFIG.deviceScaleFactor;

  for (const file of result.files) {
    const buf = await fs.readFile(file);
    const size = pngSize(buf);
    if (size.width !== expectedWidth || size.height !== expectedHeight) {
      throw new Error(`${label}: unexpected PNG size for ${file}: ${size.width}x${size.height}`);
    }
  }
}

function assertCoverCount(result, label, expected) {
  const coverCount = result.files.filter((file) => path.basename(file).includes("_cover")).length;
  if (coverCount !== expected) {
    throw new Error(`${label}: expected ${expected} cover files, got ${coverCount}`);
  }
}

const markdown = await fs.readFile(fixturePath, "utf-8");
await fs.mkdir(outputRoot, { recursive: true });

const themedStyles = CARD_STYLE_IDS.filter((style) => style !== "legacy");
const cases = [
  ...COLOR_SCHEME_IDS.map((color_scheme) => ({ style: "legacy", color_scheme, cover_variant: "primary" })),
  ...themedStyles.map((style) => ({ style, cover_variant: "all", cover_style: "both" })),
];

for (const c of cases) {
  const label = c.style === "legacy" ? `legacy_${c.color_scheme}` : `${c.style}_${c.cover_variant}_${c.cover_style}`;
  const outputDir = path.join(outputRoot, label);
  const result = await renderMarkdownToCards(markdown, {
    base_dir: baseDir,
    output_dir: outputDir,
    style: c.style,
    color_scheme: c.color_scheme,
    cover_variant: c.cover_variant,
    chapter_label: "主题回归",
    cover_style: c.cover_style || "image",
  });
  await assertPngSet(result, label);
  if (c.style === "legacy" && result.color_scheme !== c.color_scheme) {
    throw new Error(`${label}: expected color_scheme ${c.color_scheme}, got ${result.color_scheme}`);
  }
  if (c.style !== "legacy" && result.color_scheme !== null) {
    throw new Error(`${label}: expected null color_scheme for non-legacy style, got ${result.color_scheme}`);
  }
  if (c.cover_style === "both" && c.cover_variant === "all") assertCoverCount(result, label, 4);
  console.log(`${label}: ${result.files.length} files`);
}

const defaultResult = await renderMarkdownToCards(markdown, {
  base_dir: baseDir,
  output_dir: path.join(outputRoot, "default"),
});
await assertPngSet(defaultResult, "default");
if (defaultResult.style !== "legacy" || defaultResult.color_scheme !== DEFAULT_COLOR_SCHEME_ID) {
  throw new Error(`default: expected legacy/${DEFAULT_COLOR_SCHEME_ID}, got ${defaultResult.style}/${defaultResult.color_scheme}`);
}

const overrideResult = await renderMarkdownToCards(markdown, {
  base_dir: baseDir,
  output_dir: path.join(outputRoot, "coral_manual_overrides"),
  style: "coral",
  accent_color: "#0057ff",
  background_color: "#ffffff",
  text_color: "#111111",
  font_size: 24,
});
await assertPngSet(overrideResult, "coral_manual_overrides");

try {
  await renderMarkdownToCards(markdown, {
    base_dir: baseDir,
    output_dir: path.join(outputRoot, "invalid_nonlegacy_color_scheme"),
    style: "coral",
    color_scheme: DEFAULT_COLOR_SCHEME_ID,
  });
  throw new Error("non-legacy color_scheme did not throw");
} catch (err) {
  if (!/color_scheme is only supported when style=legacy/.test(err.message)) {
    throw err;
  }
}

console.log(JSON.stringify({ output_dir: outputRoot, cases: cases.length }) + "\n");
