import React, {useEffect, useMemo, useState} from 'react';
import {
  Button,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {
  openUsageAccessSettings,
  startTracking,
  stopTracking,
} from '../services/usageTrackingService';
import {getApiBaseUrl, setApiBaseUrlOverride} from '../config/api';
import {syncUsageEvents} from '../services/usageSyncService';

const DEFAULT_USER_ID = 1;

export default function TrackingScreen(): React.JSX.Element {
  const [status, setStatus] = useState('Idle');
  const [lastSync, setLastSync] = useState<string>('Never');
  const [lastError, setLastError] = useState<string>('');
  const [resolvedApiUrl, setResolvedApiUrl] = useState<string>('Resolving...');

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
});
