import AsyncStorage from '@react-native-async-storage/async-storage';

import {mirrorNativeApiBaseUrl} from '../services/usageTrackingService';

const STORAGE_KEY_OVERRIDE = 'api_base_url_override';
const STORAGE_KEY_LAST_GOOD = 'api_base_url_last_good';
const PROBE_TIMEOUT_MS = 1800;

const LAN_CANDIDATES = [
  'http://10.217.146.30:3000',
  'http://192.168.1.10:3000',
];

let resolvedApiBaseUrl: string | null = null;

async function probeUrl(
  url: string,
  timeoutMs: number = PROBE_TIMEOUT_MS,
): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const health = await fetch(`${url}/api/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    if (health.ok) {
      return true;
    }

    const root = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
    });
    return root.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

function uniqueCandidates(candidates: string[]): string[] {
  return [...new Set(candidates)];
}

async function resolveByCandidates(candidates: string[]): Promise<string> {
  for (const candidate of candidates) {
    console.log('RN_API_DETECT probing', candidate);
    const ok = await probeUrl(candidate);
    if (!ok) {
      continue;
    }
    console.log('RN_API_DETECT selected', candidate);
    await AsyncStorage.setItem(STORAGE_KEY_LAST_GOOD, candidate);
    resolvedApiBaseUrl = candidate;
    await mirrorNativeApiBaseUrl(candidate);
    return candidate;
  }
  throw new Error(
    'Unable to detect backend URL. Ensure backend is reachable or set a URL override.',
  );
}

export async function getApiBaseUrl(): Promise<string> {
  if (resolvedApiBaseUrl) {
    return resolvedApiBaseUrl;
  }

  const override = await AsyncStorage.getItem(STORAGE_KEY_OVERRIDE);
  const lastKnownGood = await AsyncStorage.getItem(STORAGE_KEY_LAST_GOOD);

  if (override) {
    console.log('RN_API_DETECT override found', override);
    const ok = await probeUrl(override);
    if (ok) {
      console.log('RN_API_DETECT selected override', override);
      resolvedApiBaseUrl = override;
      await AsyncStorage.setItem(STORAGE_KEY_LAST_GOOD, override);
      await mirrorNativeApiBaseUrl(override);
      return override;
    }
  }

  if (lastKnownGood) {
    console.log('RN_API_DETECT last-known-good found', lastKnownGood);
  }

  const candidates = uniqueCandidates([
    ...(lastKnownGood ? [lastKnownGood] : []),
    'http://localhost:3000',
    'http://10.0.2.2:3000',
    ...LAN_CANDIDATES,
  ]);

  return resolveByCandidates(candidates);
}

export async function setApiBaseUrlOverride(url: string | null): Promise<void> {
  if (url && url.trim()) {
    const normalized = url.trim().replace(/\/+$/, '');
    await AsyncStorage.setItem(STORAGE_KEY_OVERRIDE, normalized);
    resolvedApiBaseUrl = null;
    console.log('RN_API_DETECT override set', normalized);
    return;
  }

  await AsyncStorage.removeItem(STORAGE_KEY_OVERRIDE);
  await AsyncStorage.removeItem(STORAGE_KEY_LAST_GOOD);
  resolvedApiBaseUrl = null;
  console.log('RN_API_DETECT override cleared; forcing re-detect');
}
