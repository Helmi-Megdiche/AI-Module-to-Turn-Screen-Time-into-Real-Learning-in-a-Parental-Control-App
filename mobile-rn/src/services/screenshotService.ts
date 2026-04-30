import {
  DeviceEventEmitter,
  NativeModules,
  Platform,
  type EmitterSubscription,
} from 'react-native';

const LOG = 'RN_SCREENSHOT';

type ConsentResult = {
  granted: boolean;
  reason?: string;
};

type CaptureFrameResult = {
  bytesBase64?: string;
  filePath?: string;
  width: number;
  height: number;
  format: 'png' | 'jpeg';
  byteSize?: number;
};

type ScreenshotStatus = {
  enabled: boolean;
  consentGranted: boolean;
  capturing: boolean;
  lastError?: string;
  lastCaptureAt?: number;
  pausedInBackground?: boolean;
  maxCaptureRetries?: number;
  retryDelayMs?: number;
};

type ScreenshotNativeModule = {
  requestProjectionConsent: () => Promise<ConsentResult>;
  startCapture: () => Promise<boolean>;
  captureFrame: () => Promise<CaptureFrameResult>;
  stopCapture: () => Promise<boolean>;
  getStatus: () => Promise<ScreenshotStatus>;
};

const ScreenshotModule =
  Platform.OS === 'android'
    ? (NativeModules as {ScreenshotModule?: ScreenshotNativeModule})
        .ScreenshotModule
    : undefined;

function requireAndroidModule(): ScreenshotNativeModule {
  if (!ScreenshotModule) {
    throw new Error('Screenshot capture is Android-only.');
  }
  return ScreenshotModule;
}

export function isScreenshotNativeAvailable(): boolean {
  return !!ScreenshotModule;
}

export async function requestProjectionConsent(): Promise<ConsentResult> {
  const result = await requireAndroidModule().requestProjectionConsent();
  console.log(
    LOG,
    `consent_result granted=${result.granted} reason=${result.reason}`,
  );
  return result;
}

export async function startScreenshotCapture(): Promise<boolean> {
  const ok = await requireAndroidModule().startCapture();
  console.log(LOG, 'capture_started');
  return ok;
}

export async function captureScreenshotFrame(): Promise<CaptureFrameResult> {
  const frame = await requireAndroidModule().captureFrame();
  const size = frame.byteSize ?? frame.bytesBase64?.length ?? 0;
  console.log(LOG, `frame_captured bytes=${size}`);
  return frame;
}

export async function stopScreenshotCapture(): Promise<boolean> {
  const ok = await requireAndroidModule().stopCapture();
  console.log(LOG, 'capture_stopped');
  return ok;
}

export async function getScreenshotStatus(): Promise<ScreenshotStatus> {
  const status = await requireAndroidModule().getStatus();
  console.log(LOG, `status ${JSON.stringify(status)}`);
  return status;
}

export function onProjectionStopped(listener: () => void): EmitterSubscription {
  return DeviceEventEmitter.addListener(
    'RN_SCREENSHOT_PROJECTION_STOPPED',
    listener,
  );
}

export type {CaptureFrameResult, ConsentResult, ScreenshotStatus};
