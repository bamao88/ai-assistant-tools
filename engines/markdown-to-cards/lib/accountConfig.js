import fs from "fs";
import os from "os";
import path from "path";

const CARD_CONFIG_KEYS = [
  "style",
  "color_scheme",
  "chapter_label",
  "cover_template",
  "cover_style",
  "cover_bg_path",
  "cover_image_path",
  "cover_variant",
  "accent_color",
  "background_color",
  "text_color",
  "font_size",
];

function hasValue(value) {
  return value !== undefined && value !== null && String(value).trim() !== "";
}

function defaultAccountsPath() {
  return path.join(os.homedir(), ".xhs", "accounts.json");
}

function normalizeCardConfig(rawConfig = {}) {
  const normalized = {};
  for (const key of CARD_CONFIG_KEYS) {
    if (hasValue(rawConfig[key])) normalized[key] = rawConfig[key];
  }
  return normalized;
}

export function loadAccountCardConfig(accountName, accountsPath = defaultAccountsPath()) {
  if (!hasValue(accountName)) return {};
  if (!fs.existsSync(accountsPath)) {
    throw new Error(`XHS account config not found: ${accountsPath}`);
  }

  const config = JSON.parse(fs.readFileSync(accountsPath, "utf8"));
  const account = config.accounts?.[accountName];
  if (!account) {
    const available = Object.keys(config.accounts || {});
    throw new Error(`Unknown XHS account: ${accountName}. Available accounts: ${available.join(", ")}`);
  }

  return normalizeCardConfig(account.card_config || {});
}

export function resolveAccountCardOptions(options = {}) {
  const accountName = options.account;
  const accountConfig = loadAccountCardConfig(accountName);
  if (!Object.keys(accountConfig).length) return { ...options };

  const merged = { ...options };
  for (const key of CARD_CONFIG_KEYS) {
    if (!hasValue(merged[key]) && hasValue(accountConfig[key])) merged[key] = accountConfig[key];
  }
  return merged;
}
