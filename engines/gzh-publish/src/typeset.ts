import { renderMarkdown, applyTheme } from './lib/markdown';
import { applyWechatCompat } from './lib/wechatCompat';

export interface TypesetOptions {
  theme?: string;
  baseDir?: string;
  convertImages?: boolean;
  accessToken?: string;
}

/**
 * Convert Markdown content to WeChat-compatible HTML with the given theme.
 */
export async function typeset(markdownContent: string, options: TypesetOptions = {}): Promise<string> {
  const themeId = options.theme || 'claude';

  // Step 1: Render Markdown to HTML
  const rawHtml = renderMarkdown(markdownContent);

  // Step 2: Apply theme styles
  const themedHtml = applyTheme(rawHtml, themeId);

  // Step 3: Apply WeChat compatibility fixes (async: image upload/base64)
  const wechatHtml = await applyWechatCompat(themedHtml, {
    themeId,
    baseDir: options.baseDir,
    convertImages: options.convertImages,
    accessToken: options.accessToken,
  });

  return wechatHtml;
}
