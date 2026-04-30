import React, {useEffect, useMemo, useState} from 'react';
import {
  Button,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import {
  openUsageAccessSettings,
  setSyncUserIdNative,
  startTracking,
  stopTracking,
  type ScheduledSyncStatus,
} from '../services/usageTrackingService';
import {getApiBaseUrl, setApiBaseUrlOverride} from '../config/api';
import {syncUsageEvents} from '../services/usageSyncService';
import {
  disableBackgroundSync,
  enableBackgroundSync,
  refreshScheduledSyncStatus,
  requestImmediateBackgroundSync,
} from '../services/backgroundSyncService';

const DEFAULT_USER_ID = 1;

export default function TrackingScreen(): React.JSX.Element {
  const [status, setStatus] = useState('Idle');
  const [lastSync, setLastSync] = useState<string>('Never');
  const [lastError, setLastError] = useState<string>('');
  const [resolvedApiUrl, setResolvedApiUrl] = useState<string>('Resolving...');
  const [bgIntervalInput, setBgIntervalInput] = useState<string>('30');
  const [bgSchedule, setBgSchedule] = useState<ScheduledSyncStatus | null>(
    null,
  );
  const [bgUiError, setBgUiError] = useState<string>('');

  const statusColor = useMemo(() => {
    if (lastError) {
      return '#b00020';
    }
    return '#1b5e20';
  }, [lastError]);

  const refreshApiUrl = async () => {
    try {
      const url = await getApiBaseUrl();
      setResolvedApiUrl(url);
    } catch (error: any) {
      setResolvedApiUrl('Not resolved');
      setLastError(error?.message ?? 'API URL detection failed');
    }
  };

  useEffect(() => {
    refreshApiUrl();
  }, []);

  const refreshBgSchedule = async () => {
    if (Platform.OS !== 'android') {
      return;
    }
    try {
      setBgUiError('');
      const s = await refreshScheduledSyncStatus();
      setBgSchedule(s);
    } catch (error: any) {
      setBgUiError(error?.message ?? 'Background sync status failed');
    }
  };

  useEffect(() => {
    if (Platform.OS !== 'android') {
      return;
    }
    setSyncUserIdNative(DEFAULT_USER_ID).catch(() => undefined);
    refreshBgSchedule().catch(() => undefined);
  }, []);

  const runStartTracking = async () => {
    try {
      console.log('RN_USAGE_TEST startTracking pressed');
      setLastError('');
      setStatus('Starting tracking...');
      await startTracking();
      console.log('RN_USAGE_TEST startTracking success');
      setStatus('Tracking started');
    } catch (error: any) {
      console.log(
        'RN_USAGE_TEST startTracking error',
        error?.code,
        error?.message,
      );
      if (error?.code === 'USAGE_PERMISSION_NOT_GRANTED') {
        openUsageAccessSettings();
      }
      setLastError(error?.message ?? 'Failed to start tracking');
      setStatus('Tracking start failed');
    }
  };

  const runStopTracking = async () => {
    try {
      console.log('RN_USAGE_TEST stopTracking pressed');
      setLastError('');
      setStatus('Stopping tracking...');
      await stopTracking();
      console.log('RN_USAGE_TEST stopTracking success');
      setStatus('Tracking stopped');
    } catch (error: any) {
      setLastError(error?.message ?? 'Failed to stop tracking');
      setStatus('Tracking stop failed');
    }
  };

  const runSync = async () => {
    try {
      console.log('RN_USAGE_TEST sync pressed');
      setLastError('');
      setStatus('Syncing usage events...');
      const result = await syncUsageEvents(DEFAULT_USER_ID);
      setResolvedApiUrl(result.apiBaseUrl);
      console.log('RN_USAGE_TEST sync result', JSON.stringify(result));
      if (result.skipped) {
        setStatus('No events to sync');
      } else {
        setStatus(`Synced ${result.uploaded} events`);
      }
      setLastSync(new Date().toISOString());
      await refreshBgSchedule();
    } catch (error: any) {
      console.log('RN_USAGE_TEST sync error', error?.message);
      setLastError(error?.message ?? 'Sync failed');
      setStatus('Sync failed');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Usage Tracking</Text>

        <View style={styles.actions}>
          <Button title="Start Tracking" onPress={runStartTracking} />
          <View style={styles.spacer} />
          <Button title="Stop Tracking" onPress={runStopTracking} />
          <View style={styles.spacer} />
          <Button title="Sync Now" onPress={runSync} />
          <View style={styles.spacer} />
          <Button
            title="Open Usage Settings"
            onPress={() => {
              console.log('RN_USAGE_TEST openSettings pressed');
              openUsageAccessSettings();
            }}
          />
          <View style={styles.spacer} />
          <Button
            title="Re-detect URL"
            onPress={async () => {
              console.log('RN_API_DETECT manual re-detect requested');
              await setApiBaseUrlOverride(null);
              await refreshApiUrl();
            }}
          />
        </View>

        {Platform.OS === 'android' ? (
          <View style={styles.actions}>
            <Text style={styles.panelTitle}>Background sync (WorkManager)</Text>
            <Text style={styles.meta}>
              Uses tag behavioral-sync; logs RN_USAGE_BG / RN_USAGE_BG_JS.
            </Text>
            <View style={styles.row}>
              <Text style={styles.meta}>Scheduled</Text>
              <Switch
                value={!!bgSchedule?.enabled}
                onValueChange={async next => {
                  try {
                    setBgUiError('');
                    if (next) {
                      const n = parseInt(bgIntervalInput, 10);
                      const interval = Number.isFinite(n) ? n : 30;
                      await enableBackgroundSync(interval);
                    } else {
                      await disableBackgroundSync();
                    }
                    await refreshBgSchedule();
                  } catch (error: any) {
                    setBgUiError(
                      error?.message ?? 'Background sync toggle failed',
                    );
                  }
                }}
              />
            </View>
            <Text style={styles.meta}>Interval (minutes, min 15)</Text>
            <TextInput
              style={styles.input}
              keyboardType="number-pad"
              value={bgIntervalInput}
              onChangeText={setBgIntervalInput}
            />
            <View style={styles.spacer} />
            <Button
              title="Trigger one-shot worker now"
              onPress={async () => {
                try {
                  setBgUiError('');
                  await requestImmediateBackgroundSync();
                  await refreshBgSchedule();
                } catch (error: any) {
                  setBgUiError(error?.message ?? 'One-shot enqueue failed');
                }
              }}
            />
            <View style={styles.spacer} />
            <Button title="Refresh worker status" onPress={refreshBgSchedule} />
            {bgSchedule ? (
              <View style={styles.spacer}>
                <Text style={styles.meta}>
                  lastRunAtMs: {bgSchedule.lastRunAtMs || '—'}
                </Text>
                <Text style={styles.meta}>
                  lastResult: {bgSchedule.lastResult}
                </Text>
                <Text style={styles.meta}>
                  lastError: {bgSchedule.lastError || '—'}
                </Text>
              </View>
            ) : null}
            {bgUiError ? <Text style={styles.error}>{bgUiError}</Text> : null}
          </View>
        ) : null}

        <View style={styles.panel}>
          <Text style={styles.panelTitle}>Status</Text>
          <Text style={[styles.status, {color: statusColor}]}>{status}</Text>
          <Text style={styles.meta}>API URL: {resolvedApiUrl}</Text>
          <Text style={styles.meta}>Last sync: {lastSync}</Text>
          <Text style={styles.error}>Last error: {lastError || 'None'}</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 16,
  },
  actions: {
    backgroundColor: '#ffffff',
    padding: 12,
    borderRadius: 10,
    marginBottom: 16,
  },
  spacer: {
    height: 10,
  },
  panel: {
    backgroundColor: '#ffffff',
    padding: 12,
    borderRadius: 10,
  },
  panelTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  status: {
    fontSize: 16,
    marginBottom: 8,
  },
  meta: {
    fontSize: 14,
    marginBottom: 8,
  },
  error: {
    fontSize: 14,
    color: '#b00020',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginVertical: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 16,
    backgroundColor: '#fafafa',
  },
});
