import { renderBodyPage } from "./body.js";
import { renderImageCover, renderTemplateCover } from "./cover.js";
export {
  COLOR_SCHEME_IDS,
  DEFAULT_COLOR_SCHEME_ID,
  normalizeColorScheme,
  resolveColorScheme,
} from "./colorSchemes.js";

export const legacyTemplate = {
  id: "legacy",
  name: "默认模板",
  defaults: null,
  supportedCoverVariants: ["primary"],
  resolve() {
    return null;
  },
  renderBodyPage(cfg, _theme, _meta = {}, pageHtml = "") {
    return renderBodyPage(cfg, pageHtml);
  },
  renderCover({ title, wordCount, cfg, coverBgSrc, fontOpts = {}, coverImageSrc = null, coverStyle = "template" }) {
    if (coverImageSrc && coverStyle !== "template") {
      return renderImageCover(title, wordCount, cfg, coverImageSrc, fontOpts);
    }
    return renderTemplateCover(title, cfg, coverBgSrc, fontOpts);
  },
};

export default legacyTemplate;
