import {NativeModules} from 'react-native';

type UsageEvent = {
  event_type: 'app_session';
  app_package: string;
  started_at: number;
  ended_at?: number;
  duration_sec: number;
};

type UsageEventsResponse = {
  events: UsageEvent[];
  nextCursor: string;
};

type UsageTrackingNativeModule = {
  startTracking: () => Promise<boolean>;
  stopTracking: () => Promise<boolean>;
  getUsageEvents: () => Promise<UsageEventsResponse>;
  confirmSync: (cursor: string) => Promise<boolean>;
  openUsageAccessSettings: () => void;
};

const {UsageTracking} = NativeModules as {
  UsageTracking: UsageTrackingNativeModule;
};

export async function startTracking(): Promise<boolean> {
  return UsageTracking.startTracking();
}

export async function stopTracking(): Promise<boolean> {
  return UsageTracking.stopTracking();
}

export async function getUsageEvents(): Promise<UsageEventsResponse> {
  return UsageTracking.getUsageEvents();
}

export async function confirmSync(cursor: string): Promise<boolean> {
  return UsageTracking.confirmSync(cursor);
}

export function openUsageAccessSettings(): void {
  UsageTracking.openUsageAccessSettings();
}

export type {UsageEvent, UsageEventsResponse};
