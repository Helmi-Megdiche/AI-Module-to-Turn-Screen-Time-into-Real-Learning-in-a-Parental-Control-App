import {getApiBaseUrl} from '../config/api';
import {confirmSync, getUsageEvents} from './usageTrackingService';

function assertValidUserId(userId: number): void {
  if (!Number.isInteger(userId) || userId <= 0) {
    throw new Error('userId must be a positive integer.');
  }
}

export async function syncUsageEvents(userId: number): Promise<{
  uploaded: number;
  skipped: boolean;
  apiBaseUrl: string;
}> {
  assertValidUserId(userId);

  const {events, nextCursor} = await getUsageEvents();
  const apiBaseUrl = await getApiBaseUrl();
  if (!events || events.length === 0) {
    return {uploaded: 0, skipped: true, apiBaseUrl};
  }

  const boundedEvents = events.slice(0, 500);
  const response = await fetch(`${apiBaseUrl}/api/usage/events`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      userId,
      events: boundedEvents,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Upload failed (${response.status}): ${body}`);
  }

  await confirmSync(nextCursor);
  return {uploaded: boundedEvents.length, skipped: false, apiBaseUrl};
}
