import React from 'react';
import {StyleSheet, Text, View} from 'react-native';

type Props = {
  addictionScore: number;
  wellbeingScore: number;
};

function asPercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export default function ScoresPanel({
  addictionScore,
  wellbeingScore,
}: Props): React.JSX.Element {
  return (
    <View style={styles.row}>
      <View style={styles.card}>
        <Text style={styles.value}>{asPercent(addictionScore)}</Text>
        <Text style={styles.label}>Addiction Score</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.value}>{asPercent(wellbeingScore)}</Text>
        <Text style={styles.label}>Wellbeing Score</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  card: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  value: {
    fontSize: 30,
    fontWeight: '700',
    color: '#0d47a1',
  },
  label: {
    marginTop: 4,
    color: '#37474f',
    fontWeight: '600',
  },
});
