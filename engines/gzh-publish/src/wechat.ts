import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const BASE_URL = 'https://api.weixin.qq.com';
const TOKEN_CACHE_DIR = path.join(os.homedir(), '.gzh-publish');

interface TokenCache {
  access_token: string;
  expires_at: number; // Unix timestamp in ms
}

function tokenCacheFile(appId: string): string {
  return path.join(TOKEN_CACHE_DIR, `token_${appId}.json`);
}

interface AccessTokenResponse {
  access_token?: string;
  expires_in?: number;
  errcode?: number;
  errmsg?: string;
}

interface UploadImageResponse {
  url?: string;
  media_id?: string;
  errcode?: number;
  errmsg?: string;
}

interface CreateDraftResponse {
  media_id?: string;
  errcode?: number;
  errmsg?: string;
}

interface PublishResponse {
  publish_id?: string;
  errcode?: number;
  errmsg?: string;
}

function loadTokenCache(appId: string): TokenCache | null {
  try {
    const file = tokenCacheFile(appId);
    if (!fs.existsSync(file)) return null;
    const data = fs.readFileSync(file, 'utf-8');
    return JSON.parse(data) as TokenCache;
  } catch {
    return null;
  }
}

function saveTokenCache(appId: string, cache: TokenCache): void {
  try {
    if (!fs.existsSync(TOKEN_CACHE_DIR)) {
      fs.mkdirSync(TOKEN_CACHE_DIR, { recursive: true });
    }
    fs.writeFileSync(tokenCacheFile(appId), JSON.stringify(cache, null, 2), 'utf-8');
  } catch {
    // Ignore cache write errors
  }
}

/**
 * Get WeChat access token, using local cache when valid.
 */
export async function getAccessToken(appId: string, appSecret: string, forceRefresh = false): Promise<string> {
  // Check cache first
  if (!forceRefresh) {
    const cached = loadTokenCache(appId);
    if (cached && cached.expires_at > Date.now() + 60_000) {
      return cached.access_token;
    }
  }

  const url = `${BASE_URL}/cgi-bin/token?grant_type=client_credential&appid=${appId}&secret=${appSecret}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP error fetching token: ${response.status}`);
  }

  const data = await response.json() as AccessTokenResponse;

  if (data.errcode) {
    throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  }

  if (!data.access_token) {
    throw new Error('No access_token in response');
  }

  const expiresIn = data.expires_in || 7200;
  const cache: TokenCache = {
    access_token: data.access_token,
    expires_at: Date.now() + expiresIn * 1000,
  };
  saveTokenCache(appId, cache);

  return data.access_token;
}

/**
 * Upload a permanent image to WeChat media storage.
 * Returns the media_id for use as article cover.
 */
export async function uploadImage(imagePath: string, token: string): Promise<string> {
  const imageData = fs.readFileSync(imagePath);
  const filename = path.basename(imagePath);
  const ext = path.extname(imagePath).toLowerCase();

  const mimeType = ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg'
    : ext === '.png' ? 'image/png'
    : ext === '.gif' ? 'image/gif'
    : 'image/jpeg';

  const formData = new FormData();
  const blob = new Blob([imageData], { type: mimeType });
  formData.append('media', blob, filename);
  formData.append('type', 'image');

  const url = `${BASE_URL}/cgi-bin/material/add_material?access_token=${token}&type=image`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`HTTP error uploading image: ${response.status}`);
  }

  const data = await response.json() as UploadImageResponse;

  if (data.errcode) {
    throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  }

  if (!data.media_id) {
    throw new Error('No media_id in upload response');
  }

  return data.media_id;
}

/**
 * Upload an image to the permanent material library for use inside article content.
 * Uses /cgi-bin/material/add_material which returns a permanent URL visible in the backend.
 */
export async function uploadContentImage(imagePath: string, token: string): Promise<string> {
  const imageData = fs.readFileSync(imagePath);
  const filename = path.basename(imagePath);
  const ext = path.extname(imagePath).toLowerCase();

  const mimeType = ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg'
    : ext === '.png' ? 'image/png'
    : ext === '.gif' ? 'image/gif'
    : 'image/jpeg';

  const formData = new FormData();
  const blob = new Blob([imageData], { type: mimeType });
  formData.append('media', blob, filename);

  const url = `${BASE_URL}/cgi-bin/material/add_material?access_token=${token}&type=image`;
  const response = await fetch(url, { method: 'POST', body: formData });

  if (!response.ok) throw new Error(`HTTP error uploading content image: ${response.status}`);

  const data = await response.json() as { url?: string; media_id?: string; errcode?: number; errmsg?: string };
  if (data.errcode) throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  if (!data.url) throw new Error('No url in add_material response');

  return data.url;
}

export interface ArticleParams {
  title: string;
  content: string;         // WeChat-compatible HTML
  thumbMediaId: string;    // Cover image media_id
  author?: string;
  digest?: string;         // Article summary (max 120 chars)
  showCoverPic?: number;   // 1 = show cover, 0 = hide
}

/**
 * Create a draft article in WeChat public account.
 * Returns the media_id of the created draft.
 */
export async function createDraft(article: ArticleParams, token: string): Promise<string> {
  const url = `${BASE_URL}/cgi-bin/draft/add?access_token=${token}`;

  const body = {
    articles: [
      {
        title: article.title,
        content: article.content,
        thumb_media_id: article.thumbMediaId,
        author: article.author || '',
        digest: article.digest || '',
        show_cover_pic: article.showCoverPic ?? 1,
        need_open_comment: 0,
        only_fans_can_comment: 0,
      }
    ]
  };

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error creating draft: ${response.status}`);
  }

  const data = await response.json() as CreateDraftResponse;

  if (data.errcode) {
    throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  }

  if (!data.media_id) {
    throw new Error('No media_id in draft creation response');
  }

  return data.media_id;
}

/**
 * Publish a draft article (send to all followers).
 * Returns the publish_id.
 */
export async function publishDraft(mediaId: string, token: string): Promise<string> {
  const url = `${BASE_URL}/cgi-bin/freepublish/submit?access_token=${token}`;

  const body = { media_id: mediaId };

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`HTTP error publishing draft: ${response.status}`);
  }

  const data = await response.json() as PublishResponse;

  if (data.errcode) {
    throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  }

  return data.publish_id || mediaId;
}

/**
 * Check if credentials are valid by fetching a token.
 */
export async function checkAuth(appId: string, appSecret: string): Promise<boolean> {
  try {
    await getAccessToken(appId, appSecret, true);
    return true;
  } catch {
    return false;
  }
}
