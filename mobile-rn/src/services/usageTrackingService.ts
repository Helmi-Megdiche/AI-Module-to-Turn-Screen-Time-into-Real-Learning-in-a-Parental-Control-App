import {NativeModules, Platform} from 'react-native';

export type UsageEvent = {
  event_type: 'app_session';
  app_package: string;
  started_at: number;
  ended_at?: number;
  duration_sec: number;
};

export type UsageEventsResponse = {
  events: UsageEvent[];
  nextCursor: string;
};

export type ScheduledSyncStatus = {
  enabled: boolean;
  intervalMinutes: number;
  lastRunAtMs: number;
  lastResult: string;
  lastError: string;
};

type UsageTrackingNativeModule = {
  startTracking: () => Promise<boolean>;
  stopTracking: () => Promise<boolean>;
  getUsageEvents: () => Promise<UsageEventsResponse>;
  confirmSync: (cursor: string) => Promise<boolean>;
  openUsageAccessSettings: () => void;
  setApiBaseUrl: (url: string) => Promise<boolean>;
  enqueuePeriodicSync: (intervalMinutes: number) => Promise<boolean>;
  cancelPeriodicSync: () => Promise<boolean>;
  triggerOneShotSyncNow: () => Promise<boolean>;
  getScheduledSyncStatus: () => Promise<ScheduledSyncStatus>;
  setSyncUserId: (userId: number) => Promise<boolean>;
};

const UsageTracking =
  Platform.OS === 'android'
    ? (NativeModules as {UsageTracking?: UsageTrackingNativeModule})
        .UsageTracking
    : undefined;

function requireAndroidModule(): UsageTrackingNativeModule {
  if (!UsageTracking) {
    throw new Error(
      'UsageTracking native module is only available on Android builds with usage tracking.',
    );
  }
  return UsageTracking;
}

export function isUsageTrackingNativeAvailable(): boolean {
  return !!UsageTracking;
}

export async function startTracking(): Promise<boolean> {
  return requireAndroidModule().startTracking();
}

export async function stopTracking(): Promise<boolean> {
  return requireAndroidModule().stopTracking();
}

export async function getUsageEvents(): Promise<UsageEventsResponse> {
  return requireAndroidModule().getUsageEvents();
}

export async function confirmSync(cursor: string): Promise<boolean> {
  return requireAndroidModule().confirmSync(cursor);
}

export function openUsageAccessSettings(): void {
  requireAndroidModule().openUsageAccessSettings();
}

/** Mirrors resolved JS API URL into SharedPreferences for WorkManager uploads. */
export async function mirrorNativeApiBaseUrl(url: string): Promise<void> {
  if (
    Platform.OS !== 'android' ||
    !UsageTracking?.setApiBaseUrl ||
    !url?.trim()
  ) {
    return;
  }
  const normalized = url.trim().replace(/\/+$/, '');
  await UsageTracking.setApiBaseUrl(normalized);

  let hostForLog = normalized;
  try {
    const hasScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(normalized);
    const u = new URL(hasScheme ? normalized : `http://${normalized}`);
    hostForLog = u.host || normalized;
  } catch {
    // keep hostForLog as normalized
  }
  console.log('RN_USAGE_BG_JS', `url_mirror url=${hostForLog}`);
}

export async function enqueuePeriodicSync(
  intervalMinutes: number,
): Promise<boolean> {
  return requireAndroidModule().enqueuePeriodicSync(intervalMinutes);
}

export async function cancelPeriodicSync(): Promise<boolean> {
  return requireAndroidModule().cancelPeriodicSync();
}

export async function triggerOneShotSyncNow(): Promise<boolean> {
  return requireAndroidModule().triggerOneShotSyncNow();
}

export async function getScheduledSyncStatus(): Promise<ScheduledSyncStatus> {
  return requireAndroidModule().getScheduledSyncStatus();
}

export async function setSyncUserIdNative(userId: number): Promise<void> {
  if (Platform.OS !== 'android' || !UsageTracking?.setSyncUserId) {
    return;
  }
  await UsageTracking.setSyncUserId(userId);
}
