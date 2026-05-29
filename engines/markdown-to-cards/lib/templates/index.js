import classicTemplate from "./classic/index.js";
import coralTemplate from "./coral/index.js";
import editorialTemplate from "./editorial/index.js";
import legacyTemplate, {
  COLOR_SCHEME_IDS,
  DEFAULT_COLOR_SCHEME_ID,
  normalizeColorScheme,
  resolveColorScheme,
} from "./legacy/index.js";
import lavenderTemplate from "./lavender/index.js";
import monographTemplate from "./monograph/index.js";
import prologueTemplate from "./prologue/index.js";
import sageTemplate from "./sage/index.js";
import { normalizeCoverVariant } from "./shared/themed.js";

const TEMPLATES = [
  legacyTemplate,
  coralTemplate,
  lavenderTemplate,
  editorialTemplate,
  sageTemplate,
  prologueTemplate,
  classicTemplate,
  monographTemplate,
];

const TEMPLATE_MAP = new Map(TEMPLATES.map((template) => [template.id, template]));

export const STYLE_IDS = TEMPLATES.map((template) => template.id);
export const CARD_STYLE_IDS = STYLE_IDS;
export { COLOR_SCHEME_IDS, DEFAULT_COLOR_SCHEME_ID, normalizeColorScheme, normalizeCoverVariant, resolveColorScheme };

export function normalizeCardStyle(value) {
  const style = String(value || "legacy").trim().toLowerCase();
  if (TEMPLATE_MAP.has(style)) return style;
  throw new Error(`Unknown style: ${value}. Available styles: ${STYLE_IDS.join(", ")}`);
}

export function getCardTemplate(style) {
  const id = normalizeCardStyle(style);
  return TEMPLATE_MAP.get(id);
}

export function isThemedStyle(style) {
  return normalizeCardStyle(style) !== "legacy";
}

export function resolveCardTheme(style, cfg, options = {}) {
  const template = getCardTemplate(style);
  if (template.id === "legacy") return null;
  return template.resolve(cfg, options);
}

export function buildThemedBodyPageHtml(cfg, theme, meta = {}, pageHtml = "") {
  return theme.template.renderBodyPage(cfg, theme, meta, pageHtml);
}

export function buildThemedCoverHtml(title, wordCount, cfg, theme, coverImageSrc, fontOpts = {}, coverVariant = "primary") {
  return theme.template.renderCover({
    title,
    wordCount,
    cfg,
    theme,
    coverImageSrc,
    fontOpts,
    coverVariant,
  });
}
