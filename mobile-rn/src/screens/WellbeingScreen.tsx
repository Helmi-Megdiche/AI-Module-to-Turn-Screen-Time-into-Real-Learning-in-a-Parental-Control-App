import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {useEffect, useMemo, useState} from 'react';
import {
  ActivityIndicator,
  Button,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import {getApiBaseUrl} from '../config/api';
import MissionsList from '../components/MissionsList';
import RecommendationsList from '../components/RecommendationsList';
import ScoresPanel from '../components/ScoresPanel';
import SubscoreList from '../components/SubscoreList';
import {
  analyze,
  BehavioralHttpError,
  getCurrentMissions,
  getCurrentRecommendations,
  type AnalyzeResponse,
  type Mission,
  type Recommendation,
} from '../services/behavioralService';

const STORAGE_KEY_USER_ID = 'wellbeing_user_id';
const DEFAULT_AGE_YEARS = '10';
const DEFAULT_WINDOW_DAYS = '14';

function parseHttpStatus(errorMessage: string): string {
  const match = errorMessage.match(/HTTP\s+(\d+)/i);
  return match ? match[1] : 'unknown';
}

export default function WellbeingScreen(): React.JSX.Element {
  const [resolvedApiUrl, setResolvedApiUrl] = useState<string>('Resolving...');
  const [userIdInput, setUserIdInput] = useState<string>('1');
  const [ageYearsInput, setAgeYearsInput] = useState<string>(DEFAULT_AGE_YEARS);
  const [windowDaysInput, setWindowDaysInput] =
    useState<string>(DEFAULT_WINDOW_DAYS);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [shapeWarning, setShapeWarning] = useState<string>('');

  useEffect(() => {
    (async () => {
      try {
        const storedUserId = await AsyncStorage.getItem(STORAGE_KEY_USER_ID);
        if (storedUserId) {
          setUserIdInput(storedUserId);
        }
        const baseUrl = await getApiBaseUrl();
        setResolvedApiUrl(baseUrl);
      } catch (e: any) {
        setResolvedApiUrl('Not resolved');
        setError(e?.message ?? 'Failed to initialize wellbeing screen');
      }
    })();
  }, []);

  const parsedUserId = Number(userIdInput);
  const parsedAgeYears = Number(ageYearsInput);
  const parsedWindowDays = Number(windowDaysInput);
  const isUserIdValid = Number.isInteger(parsedUserId) && parsedUserId > 0;
  const isAgeValid =
    Number.isInteger(parsedAgeYears) &&
    parsedAgeYears >= 2 &&
    parsedAgeYears <= 25;
  const isWindowValid =
    windowDaysInput.trim().length === 0 ||
    (Number.isInteger(parsedWindowDays) &&
      parsedWindowDays >= 7 &&
      parsedWindowDays <= 30);

  const refreshDisabled = useMemo(() => {
    return !isUserIdValid || isRefreshing;
  }, [isRefreshing, isUserIdValid]);
  const ageInlineError =
    !ageYearsInput.trim() || !isAgeValid ? 'Age required (2-25).' : '';
  const canAnalyzeNow =
    isUserIdValid && isAgeValid && isWindowValid && !isAnalyzing;

  function validateBeforeAnalyze(): string | null {
    if (!ageYearsInput.trim()) {
      console.log(
        'RN_BEHAVIOR analyze validation_blocked reason=ageYears_missing',
      );
      return 'Age is required (2..25).';
    }
    if (!isAgeValid) {
      console.log('RN_BEHAVIOR analyze validation_blocked reason=out_of_range');
      return 'Age must be an integer between 2 and 25.';
    }
    if (!isUserIdValid) {
      return 'User ID must be a positive integer.';
    }
    if (!isWindowValid) {
      return 'Window days must be empty or an integer between 7 and 30.';
    }
    return null;
  }

  function inspectShape(nextAnalysis: AnalyzeResponse): void {
    const addictionCount = nextAnalysis.score.subscoresJson.addiction.length;
    const wellbeingCount = nextAnalysis.score.subscoresJson.wellbeing.length;
    if (addictionCount !== 5 || wellbeingCount !== 5) {
      console.log(
        `RN_BEHAVIOR shape_warning addiction=${addictionCount} wellbeing=${wellbeingCount}`,
      );
      setShapeWarning(
        `Unexpected subscore shape (addiction=${addictionCount}, wellbeing=${wellbeingCount}).`,
      );
    } else {
      setShapeWarning('');
    }
  }

  function reportMissingKeys(
    nextRecommendations: Recommendation[],
    nextMissions: Mission[],
  ) {
    const missingRecommendationsId = nextRecommendations.some(
      item => !item?.id,
    );
    const missingMissionsId = nextMissions.some(item => !item?.id);

    if (missingRecommendationsId) {
      console.log('RN_BEHAVIOR list_keys missing=recommendations');
    }
    if (missingMissionsId) {
      console.log('RN_BEHAVIOR list_keys missing=missions');
    }
  }

  const runAnalyze = async () => {
    if (isAnalyzing) {
      return;
    }
    const validationError = validateBeforeAnalyze();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsAnalyzing(true);
    setError('');
    try {
      const payload = {
        ageYears: parsedAgeYears,
        ...(windowDaysInput.trim().length > 0
          ? {windowDays: parsedWindowDays}
          : {}),
      };
      console.log(`RN_BEHAVIOR analyze pressed userId=${parsedUserId}`);
      const result = await analyze(parsedUserId, payload);
      setAnalysis(result);
      setRecommendations(result.recommendations);
      setMissions(result.missions);
      inspectShape(result);
      reportMissingKeys(result.recommendations, result.missions);
      await AsyncStorage.setItem(STORAGE_KEY_USER_ID, String(parsedUserId));
      const baseUrl = await getApiBaseUrl();
      setResolvedApiUrl(baseUrl);
      console.log(
        `RN_BEHAVIOR analyze success addiction=${result.score.addictionScore} wellbeing=${result.score.wellbeingScore} recs=${result.recommendations.length} missions=${result.missions.length}`,
      );
    } catch (e: any) {
      const message = e?.message ?? 'Analyze failed';
      const statusCode = parseHttpStatus(message);
      console.log(`RN_BEHAVIOR analyze error ${statusCode} ${message}`);
      setError(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const refreshSnapshot = async () => {
    if (!isUserIdValid) {
      setError('User ID must be a positive integer.');
      return;
    }

    setIsRefreshing(true);
    setError('');
    try {
      const [recommendationsResult, missionsResult] = await Promise.allSettled([
        getCurrentRecommendations(parsedUserId),
        getCurrentMissions(parsedUserId),
      ]);

      let nextRecommendations: Recommendation[] = recommendations;
      let nextMissions: Mission[] = missions;

      if (recommendationsResult.status === 'fulfilled') {
        nextRecommendations = recommendationsResult.value;
      } else if (
        recommendationsResult.reason instanceof BehavioralHttpError &&
        recommendationsResult.reason.status === 404
      ) {
        console.log(
          'RN_BEHAVIOR fetch recommendations error 404 user_not_found',
        );
        nextRecommendations = [];
      } else {
        throw recommendationsResult.reason;
      }

      if (missionsResult.status === 'fulfilled') {
        nextMissions = missionsResult.value;
      } else if (
        missionsResult.reason instanceof BehavioralHttpError &&
        missionsResult.reason.status === 404
      ) {
        console.log('RN_BEHAVIOR fetch missions error 404 user_not_found');
        nextMissions = [];
      } else {
        throw missionsResult.reason;
      }

      setRecommendations(nextRecommendations);
      setMissions(nextMissions);
      reportMissingKeys(nextRecommendations, nextMissions);
      const baseUrl = await getApiBaseUrl();
      setResolvedApiUrl(baseUrl);
      if (
        recommendationsResult.status === 'rejected' ||
        missionsResult.status === 'rejected'
      ) {
        setError('User not found');
      }
    } catch (e: any) {
      const message = e?.message ?? 'Refresh failed';
      console.log(`RN_BEHAVIOR fetch error endpoint=current ${message}`);
      setError(message);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Behavioral Wellbeing</Text>
        <Text style={styles.meta}>API URL: {resolvedApiUrl}</Text>

        <View style={styles.panel}>
          <Text style={styles.fieldLabel}>User ID</Text>
          <TextInput
            style={styles.input}
            value={userIdInput}
            onChangeText={setUserIdInput}
            keyboardType="number-pad"
            placeholder="1"
          />
          <Text style={styles.fieldLabel}>Age Years (required, 2..25)</Text>
          <TextInput
            style={styles.input}
            value={ageYearsInput}
            onChangeText={setAgeYearsInput}
            keyboardType="number-pad"
            placeholder="10"
          />
          {ageInlineError ? (
            <Text style={styles.inputError}>{ageInlineError}</Text>
          ) : null}
          <Text style={styles.fieldLabel}>Window Days (optional, 7..30)</Text>
          <TextInput
            style={styles.input}
            value={windowDaysInput}
            onChangeText={setWindowDaysInput}
            keyboardType="number-pad"
            placeholder="14"
          />
          <View style={styles.spacer} />
          <View style={!canAnalyzeNow ? styles.dimmedButton : undefined}>
            <Button
              title={isAnalyzing ? 'Running Analyze...' : 'Run Analyze'}
              onPress={runAnalyze}
            />
          </View>
          <View style={styles.spacer} />
          <Button
            title={isRefreshing ? 'Refreshing...' : 'Refresh Current Snapshot'}
            onPress={refreshSnapshot}
            disabled={refreshDisabled}
          />
        </View>

        {isAnalyzing || isRefreshing ? (
          <View style={styles.loading}>
            <ActivityIndicator />
            <Text style={styles.loadingText}>Loading...</Text>
          </View>
        ) : null}

        {error ? <Text style={styles.errorBanner}>Error: {error}</Text> : null}
        {shapeWarning ? (
          <Text style={styles.warnBanner}>{shapeWarning}</Text>
        ) : null}

        {analysis ? (
          <>
            <ScoresPanel
              addictionScore={analysis.score.addictionScore}
              wellbeingScore={analysis.score.wellbeingScore}
            />
            <View style={styles.sectionSpacer} />
            <SubscoreList
              title="Addiction Subscores"
              items={analysis.score.subscoresJson.addiction}
            />
            <View style={styles.sectionSpacer} />
            <SubscoreList
              title="Wellbeing Subscores"
              items={analysis.score.subscoresJson.wellbeing}
            />
          </>
        ) : (
          <Text style={styles.emptyBanner}>
            No behavioral snapshot yet. Run Analyze first.
          </Text>
        )}

        <View style={styles.sectionSpacer} />
        <RecommendationsList items={recommendations} />
        <View style={styles.sectionSpacer} />
        <MissionsList items={missions} />
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
    marginBottom: 6,
  },
  meta: {
    color: '#455a64',
    marginBottom: 12,
  },
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 12,
  },
  fieldLabel: {
    fontWeight: '600',
    marginBottom: 4,
    marginTop: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: '#cfd8dc',
    borderRadius: 8,
    backgroundColor: '#ffffff',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  inputError: {
    marginTop: 4,
    color: '#b00020',
    fontSize: 12,
  },
  spacer: {
    height: 10,
  },
  dimmedButton: {
    opacity: 0.5,
  },
  sectionSpacer: {
    height: 12,
  },
  loading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginVertical: 10,
  },
  loadingText: {
    color: '#455a64',
  },
  errorBanner: {
    marginTop: 10,
    marginBottom: 8,
    padding: 10,
    borderRadius: 8,
    backgroundColor: '#ffebee',
    color: '#b00020',
  },
  warnBanner: {
    marginBottom: 8,
    padding: 10,
    borderRadius: 8,
    backgroundColor: '#fff8e1',
    color: '#ef6c00',
  },
  emptyBanner: {
    marginTop: 10,
    padding: 10,
    borderRadius: 8,
    backgroundColor: '#eceff1',
    color: '#455a64',
  },
});
