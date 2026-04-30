import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
  Button,
  PermissionsAndroid,
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
import {
  captureScreenshotFrame,
  getScreenshotStatus,
  isScreenshotNativeAvailable,
  onProjectionStopped,
  requestProjectionConsent,
  startScreenshotCapture,
  stopScreenshotCapture,
  type ScreenshotStatus,
} from '../services/screenshotService';

const DEFAULT_USER_ID = 1;

export default function TrackingScreen(): React.JSX.Element {
  const screenshotAvailable =
    Platform.OS === 'android' && isScreenshotNativeAvailable();
  const [status, setStatus] = useState('Idle');
  const [lastSync, setLastSync] = useState<string>('Never');
  const [lastError, setLastError] = useState<string>('');
  const [resolvedApiUrl, setResolvedApiUrl] = useState<string>('Resolving...');
  const [bgIntervalInput, setBgIntervalInput] = useState<string>('30');
  const [bgSchedule, setBgSchedule] = useState<ScheduledSyncStatus | null>(
    null,
  );
  const [bgUiError, setBgUiError] = useState<string>('');
  const [screenshotStatus, setScreenshotStatus] =
    useState<ScreenshotStatus | null>(null);
  const [screenshotError, setScreenshotError] = useState<string>('');
  const [lastFrameInfo, setLastFrameInfo] = useState<string>('None');

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
    if (isScreenshotNativeAvailable()) {
      getScreenshotStatus()
        .then(setScreenshotStatus)
        .catch(() => undefined);
    }
  }, []);

  const refreshScreenshotStatus = useCallback(async () => {
    if (!screenshotAvailable) {
      return;
    }
    try {
      const statusRes = await getScreenshotStatus();
      setScreenshotStatus(statusRes);
    } catch (error: any) {
      setScreenshotError(error?.message ?? 'Screenshot status failed');
    }
  }, [screenshotAvailable]);

  useEffect(() => {
    if (!screenshotAvailable) {
      return;
    }
    const sub = onProjectionStopped(() => {
      setStatus('Projection stopped by system');
      refreshScreenshotStatus().catch(() => undefined);
    });
    return () => {
      sub.remove();
    };
  }, [refreshScreenshotStatus, screenshotAvailable]);

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

        {Platform.OS === 'android' ? (
          <View style={styles.actions}>
            <Text style={styles.panelTitle}>
              Screenshot capture (MediaProjection)
            </Text>
            {!screenshotAvailable ? (
              <Text style={styles.error}>
                Native screenshot module unavailable in this installed build.
                Reinstall the app after native changes.
              </Text>
            ) : null}
            <Text style={styles.meta}>
              Logs: RN_SCREENSHOT consent_granted / frame_captured /
              frame_failed
            </Text>
            <Text style={styles.meta}>
              G5 lock: capture is paused while app is in background.
            </Text>
            <Text style={styles.meta}>
              Retry policy: max {screenshotStatus?.maxCaptureRetries ?? 3}{' '}
              attempts, {screenshotStatus?.retryDelayMs ?? 200}ms backoff.
            </Text>
            <Button
              title="Request projection consent"
              disabled={!screenshotAvailable}
              onPress={async () => {
                try {
                  setScreenshotError('');
                  const result = await requestProjectionConsent();
                  setStatus(
                    result.granted
                      ? 'Projection consent granted'
                      : `Projection consent denied (${result.reason})`,
                  );
                  await refreshScreenshotStatus();
                } catch (error: any) {
                  setScreenshotError(
                    error?.message ?? 'Projection consent request failed',
                  );
                }
              }}
            />
            <View style={styles.spacer} />
            <Button
              title="Start screenshot capture"
              disabled={!screenshotAvailable}
              onPress={async () => {
                try {
                  setScreenshotError('');
                  if (Platform.OS === 'android' && Platform.Version >= 33) {
                    await PermissionsAndroid.request(
                      PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
                    );
                  }
                  await startScreenshotCapture();
                  setStatus('Screenshot capture started');
                  await refreshScreenshotStatus();
                } catch (error: any) {
                  setScreenshotError(
                    error?.message ?? 'Failed to start capture',
                  );
                }
              }}
            />
            <View style={styles.spacer} />
            <Button
              title="Capture frame now"
              disabled={!screenshotAvailable}
              onPress={async () => {
                try {
                  setScreenshotError('');
                  const frame = await captureScreenshotFrame();
                  const size = frame.byteSize ?? frame.bytesBase64?.length ?? 0;
                  setLastFrameInfo(
                    `${frame.format} ${frame.width}x${frame.height} bytes=${size}`,
                  );
                  setStatus('Screenshot frame captured');
                  await refreshScreenshotStatus();
                } catch (error: any) {
                  setScreenshotError(error?.message ?? 'Frame capture failed');
                }
              }}
            />
            <View style={styles.spacer} />
            <Button
              title="Stop screenshot capture"
              disabled={!screenshotAvailable}
              onPress={async () => {
                try {
                  setScreenshotError('');
                  await stopScreenshotCapture();
                  setStatus('Screenshot capture stopped');
                  await refreshScreenshotStatus();
                } catch (error: any) {
                  setScreenshotError(
                    error?.message ?? 'Failed to stop capture',
                  );
                }
              }}
            />
            <View style={styles.spacer} />
            <Button
              title="Refresh screenshot status"
              disabled={!screenshotAvailable}
              onPress={refreshScreenshotStatus}
            />
            {screenshotStatus ? (
              <View style={styles.spacer}>
                <Text style={styles.meta}>
                  consentGranted: {String(!!screenshotStatus.consentGranted)}
                </Text>
                <Text style={styles.meta}>
                  enabled: {String(!!screenshotStatus.enabled)}
                </Text>
                <Text style={styles.meta}>
                  capturing: {String(!!screenshotStatus.capturing)}
                </Text>
                <Text style={styles.meta}>
                  pausedInBackground:{' '}
                  {String(!!screenshotStatus.pausedInBackground)}
                </Text>
                <Text style={styles.meta}>
                  lastCaptureAt: {screenshotStatus.lastCaptureAt || '—'}
                </Text>
                <Text style={styles.meta}>
                  lastError: {screenshotStatus.lastError || '—'}
                </Text>
              </View>
            ) : null}
            <Text style={styles.meta}>Last frame: {lastFrameInfo}</Text>
            {screenshotError ? (
              <Text style={styles.error}>{screenshotError}</Text>
            ) : null}
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
