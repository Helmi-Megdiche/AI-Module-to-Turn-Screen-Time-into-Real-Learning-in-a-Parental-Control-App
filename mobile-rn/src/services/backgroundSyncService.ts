import {Platform} from 'react-native';
import {
  cancelPeriodicSync,
  enqueuePeriodicSync,
  getScheduledSyncStatus,
  triggerOneShotSyncNow,
  type ScheduledSyncStatus,
} from './usageTrackingService';

const LOG = 'RN_USAGE_BG_JS';

function ensureAndroid(): void {
  if (Platform.OS !== 'android') {
    throw new Error('Background sync is Android-only.');
  }
}

export async function enableBackgroundSync(
  intervalMinutes: number,
): Promise<void> {
  ensureAndroid();
  const safe = Math.max(15, Math.floor(intervalMinutes));
  console.log(LOG, `enable interval=${safe}`);
  await enqueuePeriodicSync(safe);
}

export async function disableBackgroundSync(): Promise<void> {
  ensureAndroid();
  console.log(LOG, 'disableBackgroundSync');
  await cancelPeriodicSync();
}

export async function requestImmediateBackgroundSync(): Promise<void> {
  ensureAndroid();
  console.log(LOG, 'trigger_now');
  await triggerOneShotSyncNow();
}

export async function refreshScheduledSyncStatus(): Promise<ScheduledSyncStatus> {
  ensureAndroid();
  const status = await getScheduledSyncStatus();
  console.log(LOG, 'refreshScheduledSyncStatus', JSON.stringify(status));
  return status;
}

export type {ScheduledSyncStatus};
