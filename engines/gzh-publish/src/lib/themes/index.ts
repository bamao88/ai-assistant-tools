import type { Theme } from './types';
import { classicThemes } from './classic';
import { modernThemes } from './modern';
import { extraThemes } from './extra';
import { unifiedThemes } from './unified';

export type { Theme };

export const THEMES: Theme[] = [...classicThemes, ...modernThemes, ...extraThemes, ...unifiedThemes];

export interface ThemeGroup {
  label: string;
  themes: Theme[];
}

export const THEME_GROUPS: ThemeGroup[] = [
  { label: '经典', themes: classicThemes },
  { label: '潮流', themes: modernThemes },
  { label: '更多风格', themes: extraThemes },
  { label: '张和 AI 产品实战派', themes: unifiedThemes },
];
