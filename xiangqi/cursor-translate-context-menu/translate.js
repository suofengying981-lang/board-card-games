'use strict';

const MAX_CHARS = 4000;

/** @typedef {{ translated: string; provider: string; detectedSource?: string }} TranslateResult */

/**
 * @param {string} text
 */
function clampText(text) {
  const t = text.trim();
  if (t.length > MAX_CHARS) {
    throw new Error(`选中文本过长（>${MAX_CHARS} 字符），请缩短后重试。`);
  }
  if (!t) {
    throw new Error('未选中有效文本。');
  }
  return t;
}

/**
 * 简易 CJK 占比，用于 MyMemory 回退时的 langpair。
 * @param {string} text
 */
function guessIsCjk(text) {
  let cjk = 0;
  for (const ch of text) {
    const code = ch.codePointAt(0) ?? 0;
    if (
      (code >= 0x4e00 && code <= 0x9fff) ||
      (code >= 0x3400 && code <= 0x4dbf) ||
      (code >= 0xf900 && code <= 0xfaff)
    ) {
      cjk++;
    }
  }
  return cjk / Math.max(text.length, 1) > 0.2;
}

/**
 * @param {string} baseUrl
 * @param {string} text
 * @param {string} target LibreTranslate target code (zh, en)
 * @param {string} [apiKey]
 * @returns {Promise<TranslateResult>}
 */
async function translateLibre(baseUrl, text, target, apiKey) {
  const root = baseUrl.replace(/\/$/, '');
  const body = {
    q: text,
    source: 'auto',
    target,
    format: 'text',
  };
  if (apiKey) {
    body.api_key = apiKey;
  }

  const res = await fetch(`${root}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`LibreTranslate HTTP ${res.status}${errText ? `: ${errText.slice(0, 200)}` : ''}`);
  }

  const data = await res.json();
  if (!data || typeof data.translatedText !== 'string') {
    throw new Error('LibreTranslate 返回格式异常');
  }
  return {
    translated: data.translatedText,
    provider: 'LibreTranslate',
    detectedSource: typeof data.detectedLanguage?.language === 'string' ? data.detectedLanguage.language : undefined,
  };
}

/**
 * @param {string} text
 * @param {string} targetLang 'zh-CN' | 'en'
 * @returns {Promise<TranslateResult>}
 */
async function translateMyMemory(text, targetLang) {
  const toZh = targetLang.startsWith('zh');
  const fromCjk = guessIsCjk(text);
  let langpair;
  if (toZh) {
    langpair = fromCjk ? 'zh-CN|zh-CN' : 'en|zh-CN';
    if (fromCjk) {
      return { translated: text, provider: 'MyMemory（已是中文）' };
    }
  } else {
    langpair = fromCjk ? 'zh-CN|en' : 'en|en';
    if (!fromCjk && /^[\x00-\x7F\s]+$/.test(text)) {
      return { translated: text, provider: 'MyMemory（已是英文）' };
    }
  }

  const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=${encodeURIComponent(langpair)}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`MyMemory HTTP ${res.status}`);
  }
  const data = await res.json();
  const translated = data?.responseData?.translatedText;
  if (typeof translated !== 'string') {
    throw new Error('MyMemory 返回格式异常');
  }
  if (data.responseStatus && data.responseStatus !== 200) {
    throw new Error(data.responseDetails || `MyMemory 错误 ${data.responseStatus}`);
  }
  return { translated, provider: 'MyMemory' };
}

/**
 * @param {import('vscode').WorkspaceConfiguration} config
 * @param {string} text
 * @param {'zh-CN' | 'en'} targetLang
 * @returns {Promise<TranslateResult>}
 */
async function translateText(config, text, targetLang) {
  const clamped = clampText(text);
  const ltTarget = targetLang.startsWith('zh') ? 'zh' : 'en';
  const baseUrl = config.get('libreTranslateUrl', 'https://libretranslate.de');
  const apiKey =
    config.get('apiKey', '') ||
    (typeof process.env.LIBRETRANSLATE_API_KEY === 'string' ? process.env.LIBRETRANSLATE_API_KEY : '');

  let lastError;
  try {
    return await translateLibre(baseUrl, clamped, ltTarget, apiKey || undefined);
  } catch (err) {
    lastError = err;
  }

  if (!config.get('fallbackToMyMemory', true)) {
    throw lastError instanceof Error ? lastError : new Error(String(lastError));
  }

  try {
    const fallback = await translateMyMemory(clamped, targetLang);
    fallback.provider += '（回退）';
    return fallback;
  } catch (err) {
    const msg = [
      lastError instanceof Error ? lastError.message : String(lastError),
      err instanceof Error ? err.message : String(err),
    ].join('；');
    throw new Error(msg);
  }
}

module.exports = { translateText, MAX_CHARS };