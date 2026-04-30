import {getApiBaseUrl} from '../config/api';

export class BehavioralHttpError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(`HTTP ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

export type Subscore = {
  name: string;
  value: number;
  explanationFr: string;
  featureValues: Record<string, number | string | boolean>;
};

export type ScoreSnapshot = {
  addictionScore: number;
  wellbeingScore: number;
  subscoresJson: {
    addiction: Subscore[];
    wellbeing: Subscore[];
  };
  recommendationsJson?: unknown[];
};

export type Recommendation = {
  id: number;
  userId: number;
  scoreSnapshotId: number;
  type: string;
  severity: string;
  messageFr: string;
  actionPayload: unknown;
  targetAudience: string;
  triggeringSubscore: string;
  triggeringValue: number;
  status: string;
  createdAt: string;
};

export type Mission = {
  id: number;
  userId: number;
  scoreSnapshotId: number;
  mission: string;
  points: number;
  triggeringSubscore: string;
  triggeringValue: number;
  targetAudience: string;
  status: string;
  type: string;
  content: unknown;
  difficulty: string;
  createdAt: string;
};

export type AnalyzeRequest = {
  ageYears: number;
  windowDays?: number;
};

export type AnalyzeResponse = {
  score: ScoreSnapshot;
  recommendations: Recommendation[];
  missions: Mission[];
};

function assertValidUserId(userId: number): void {
  if (!Number.isInteger(userId) || userId <= 0) {
    throw new Error('userId must be a positive integer');
  }
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const bodyExcerpt = text.slice(0, 300);

  if (!response.ok) {
    console.log(
      `RN_BEHAVIOR fetch error status=${response.status} body=${bodyExcerpt}`,
    );
    throw new BehavioralHttpError(response.status, bodyExcerpt);
  }

  if (!text) {
    throw new Error(`HTTP ${response.status}: empty body`);
  }

  return JSON.parse(text) as T;
}

export async function analyze(
  userId: number,
  payload: AnalyzeRequest,
): Promise<AnalyzeResponse> {
  assertValidUserId(userId);
  console.log(`RN_BEHAVIOR analyze request_start userId=${userId}`);
  const apiBaseUrl = await getApiBaseUrl();
  const response = await fetch(
    `${apiBaseUrl}/api/user/${userId}/behavioral/analyze`,
    {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    },
  );

  console.log(`RN_BEHAVIOR analyze http_status=${response.status}`);
  const parsed = await parseJsonResponse<AnalyzeResponse>(response);
  console.log(
    `RN_BEHAVIOR analyze request_success status=${response.status} recs=${parsed.recommendations.length} missions=${parsed.missions.length}`,
  );
  return parsed;
}

export async function getCurrentRecommendations(
  userId: number,
): Promise<Recommendation[]> {
  assertValidUserId(userId);
  console.log(`RN_BEHAVIOR recommendations request_start userId=${userId}`);
  const apiBaseUrl = await getApiBaseUrl();
  const response = await fetch(
    `${apiBaseUrl}/api/user/${userId}/recommendations/current`,
  );
  console.log(`RN_BEHAVIOR recommendations http_status=${response.status}`);
  const parsed = await parseJsonResponse<Recommendation[]>(response);
  console.log(
    `RN_BEHAVIOR fetch recommendations success count=${parsed.length}`,
  );
  return parsed;
}

export async function getCurrentMissions(userId: number): Promise<Mission[]> {
  assertValidUserId(userId);
  console.log(`RN_BEHAVIOR missions request_start userId=${userId}`);
  const apiBaseUrl = await getApiBaseUrl();
  const response = await fetch(
    `${apiBaseUrl}/api/user/${userId}/missions/current`,
  );
  console.log(`RN_BEHAVIOR missions http_status=${response.status}`);
  const parsed = await parseJsonResponse<Mission[]>(response);
  console.log(`RN_BEHAVIOR fetch missions success count=${parsed.length}`);
  return parsed;
}
