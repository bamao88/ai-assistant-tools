import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import type { Theme } from './types';

interface UnifiedThemeSpec {
  id: string;
  name: string;
  description: string;
  mode: string;
  font: 'serif' | 'sans';
  colors: {
    paper: string;
    ink: string;
    muted: string;
    accent: string;
    accentDeep: string;
    accentSoft: string;
    rule: string;
    codeBg: string;
    codeText: string;
  };
  typography: {
    wechatBody: number;
    wechatLine: number;
    h1: number;
    h2: number;
    h3: number;
  };
}

interface UnifiedThemeFile {
  prefix: string;
  themes: UnifiedThemeSpec[];
}

const specPath = fileURLToPath(new URL('../../../../../shared/unified-publish-themes/spec.json', import.meta.url));
const sharedThemeFile = JSON.parse(readFileSync(specPath, 'utf8')) as UnifiedThemeFile;

const FONT_STACKS = {
  serif: '"Noto Serif SC", "Songti SC", "STSongti-SC", "SimSun", Georgia, serif',
  sans: '"Noto Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
  mono: '"SF Mono", Consolas, monospace',
};

function px(value: number): string {
  return `${value}px`;
}

function withNoIndent(extra = ''): string {
  return `${extra} text-indent: 0 !important; text-align: left !important; text-align-last: left !important; -webkit-text-align-last: left !important; text-justify: none !important;`;
}

function h1Style(spec: UnifiedThemeSpec): string {
  const { colors, typography, mode } = spec;
  const center = mode === 'coral' || mode === 'monograph';
  const weight = mode === 'openai' || mode === 'monograph' ? 500 : 700;
  const border = mode === 'coral'
    ? ` padding: 10px 0; border-top: 1px solid ${colors.accent}; border-bottom: 1px solid ${colors.accent};`
    : '';
  return `font-size: ${px(typography.h1)}; font-weight: ${weight}; color: ${mode === 'medium' ? colors.ink : colors.accent} !important; line-height: 1.32 !important; margin: 36px 0 16px; text-align: ${center ? 'center' : 'left'} !important;${border}`;
}

function h2Style(spec: UnifiedThemeSpec): string {
  const { colors, typography, mode } = spec;
  const center = mode === 'coral';
  const weight = mode === 'openai' || mode === 'monograph' ? 500 : 700;
  const rule = mode === 'cards-claude'
    ? ` border-left: 4px solid ${colors.accent}; padding-left: 12px;`
    : mode === 'coral'
      ? ` padding-bottom: 8px; border-bottom: 1px solid ${colors.rule};`
      : '';
  return `font-size: ${px(typography.h2)}; font-weight: ${weight}; color: ${mode === 'openai' || mode === 'medium' || mode === 'minimal' || mode === 'monograph' ? colors.ink : colors.accent} !important; line-height: 1.38 !important; margin: 32px 0 16px; text-align: ${center ? 'center' : 'left'} !important;${rule}`;
}

function blockquoteStyle(spec: UnifiedThemeSpec): string {
  const { colors, mode } = spec;
  if (mode === 'openai') {
    return `margin: 24px 0; padding: 12px 20px; background-color: transparent !important; border-left: 2px solid ${colors.rule}; color: ${colors.ink} !important; border-radius: 0; font-style: italic; ${withNoIndent()}`;
  }
  if (mode === 'minimal') {
    return `margin: 22px 0; padding: 12px 16px; background-color: transparent !important; border-left: 3px solid #cccccc; color: ${colors.muted} !important; border-radius: 0; ${withNoIndent()}`;
  }
  if (mode === 'coral') {
    return `margin: 26px 0; padding: 16px 20px; background-color: ${colors.codeBg} !important; border-top: 1px solid ${colors.accent}; border-bottom: 1px solid ${colors.accent}; border-left: none; color: ${colors.accentDeep} !important; border-radius: 0; font-style: italic; text-align: center !important;`;
  }
  if (mode === 'monograph') {
    return `margin: 28px 0; padding: 0 22px; background-color: transparent !important; border: none; color: ${colors.muted} !important; border-radius: 0; font-style: italic; ${withNoIndent()}`;
  }
  return `margin: 24px 0; padding: 14px 18px; background-color: ${colors.accentSoft} !important; border-left: 3px solid ${colors.accent}; color: ${colors.muted} !important; border-radius: 8px; ${withNoIndent()}`;
}

function imageStyle(spec: UnifiedThemeSpec): string {
  const { colors, mode } = spec;
  if (mode === 'openai') {
    return 'max-width: 100%; height: auto; display: block; margin: 24px auto; border-radius: 0; padding: 0; box-shadow: none;';
  }
  if (mode === 'monograph') {
    return 'max-width: 100%; height: auto; display: block; margin: 26px auto; border-radius: 0; padding: 0; box-shadow: none; filter: grayscale(1);';
  }
  return `max-width: 100%; height: auto; display: block; margin: 24px auto; border-radius: ${mode === 'medium' ? 6 : 10}px; padding: ${mode === 'coral' ? 0 : 6}px; box-sizing: border-box; background-color: ${mode === 'cards-claude' ? '#f8f6f1' : 'transparent'} !important; border: ${mode === 'coral' ? 'none' : `1px solid ${colors.rule}`}; box-shadow: ${mode === 'coral' || mode === 'minimal' ? 'none' : '0 8px 20px rgba(15,23,42,0.12)'};`;
}

function buildStyles(spec: UnifiedThemeSpec): Record<string, string> {
  const { colors, typography, font, mode } = spec;
  const fontStack = FONT_STACKS[font];
  const headingFont = mode === 'medium' || mode === 'monograph' ? FONT_STACKS.serif : FONT_STACKS.sans;
  const paragraph = withNoIndent(`margin: ${mode === 'openai' ? 24 : 18}px 0 !important; line-height: ${typography.wechatLine} !important; color: ${colors.ink} !important;`);
  const tableRule = mode === 'openai' || mode === 'minimal' ? `1px solid ${colors.rule}` : `1px dashed ${colors.rule}`;

  return {
    container: `max-width: 100%; margin: 0 auto; padding: 2px 20px; box-sizing: border-box; font-family: ${fontStack}; font-size: ${px(typography.wechatBody)}; line-height: ${typography.wechatLine} !important; color: ${colors.ink} !important; background-color: ${colors.paper} !important; word-wrap: break-word;`,
    h1: `font-family: ${headingFont}; ${h1Style(spec)}`,
    h2: `font-family: ${headingFont}; ${h2Style(spec)}`,
    h3: `font-family: ${headingFont}; font-size: ${px(typography.h3)}; font-weight: 600; color: ${colors.ink} !important; line-height: 1.45 !important; margin: 28px 0 12px;`,
    h4: `font-family: ${headingFont}; font-size: ${px(Math.max(16, typography.h3 - 2))}; font-weight: 600; color: ${colors.ink} !important; line-height: 1.45 !important; margin: 24px 0 10px;`,
    p: paragraph,
    strong: mode === 'openai' || mode === 'minimal' || mode === 'medium' || mode === 'monograph'
      ? `font-weight: 700; color: ${colors.ink} !important; background-color: transparent !important;`
      : `font-weight: 700; color: ${colors.accent} !important; background-color: ${colors.accentSoft}; padding: 0 4px; border-radius: 4px;`,
    em: `font-style: italic; color: ${colors.muted} !important;`,
    a: `color: ${colors.accentDeep} !important; text-decoration: ${mode === 'openai' || mode === 'medium' || mode === 'minimal' ? 'underline' : 'none'}; text-underline-offset: 3px; border-bottom: ${mode === 'openai' || mode === 'medium' || mode === 'minimal' ? 'none' : `1px solid ${colors.accentDeep}`}; padding-bottom: 1px;`,
    ul: 'margin: 16px 0; padding-left: 0 !important; padding-inline-start: 0 !important; margin-left: 0 !important; -webkit-padding-start: 0 !important;',
    ol: 'margin: 16px 0; padding-left: 0 !important; padding-inline-start: 0 !important; margin-left: 0 !important; -webkit-padding-start: 0 !important;',
    li: withNoIndent(`margin: 8px 0; line-height: ${typography.wechatLine} !important; color: ${colors.ink} !important;`),
    ulMarker: `color: ${colors.accent} !important; font-weight: 700;`,
    olMarker: `color: ${colors.accent} !important; font-weight: 700;`,
    blockquote: blockquoteStyle(spec),
    code: `font-family: ${FONT_STACKS.mono}; padding: 2px 6px; background-color: ${colors.accentSoft} !important; color: ${colors.accentDeep} !important; border-radius: 4px; font-size: 13px !important; line-height: 1.5 !important;`,
    pre: `margin: 24px 0; padding: 18px 20px; background-color: ${colors.codeBg} !important; color: ${colors.codeText} !important; border-radius: ${mode === 'coral' || mode === 'monograph' ? 0 : 8}px; overflow-x: auto; font-size: 13px !important; line-height: 1.6 !important; ${mode === 'coral' || mode === 'monograph' ? `border-top: 1px solid ${colors.rule}; border-bottom: 1px solid ${colors.rule};` : ''}`,
    hr: `margin: 36px auto; border: none; height: 1px; background-color: ${colors.rule} !important; width: 100%;`,
    img: imageStyle(spec),
    table: `width: 100%; margin: 24px 0; border-collapse: collapse; font-size: 14px; line-height: 1.55; border-top: ${tableRule}; border-bottom: ${tableRule};`,
    th: `background-color: ${mode === 'openai' || mode === 'medium' || mode === 'minimal' || mode === 'monograph' ? 'transparent' : colors.accentSoft} !important; padding: 10px 12px; text-align: left; font-weight: 700; color: ${mode === 'openai' || mode === 'medium' || mode === 'minimal' || mode === 'monograph' ? colors.ink : colors.accent} !important; border-bottom: ${tableRule}; border-top: none; border-left: none; border-right: none;`,
    td: `padding: 10px 12px; border-bottom: ${tableRule}; border-top: none; border-left: none; border-right: none; color: ${colors.ink} !important;`,
    tr: 'border: none;',
    codeDots: 'none',
    codeHighlight: mode === 'medium' ? 'github' : 'mono',
  };
}

export const unifiedThemes: Theme[] = sharedThemeFile.themes.map((spec) => ({
  id: `${sharedThemeFile.prefix}-${spec.id}`,
  name: `共用 ${spec.name}`,
  description: spec.description,
  styles: buildStyles(spec),
}));
