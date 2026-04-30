import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {Subscore} from '../services/behavioralService';

type Props = {
  title: string;
  items: Subscore[];
};

function severityColor(value: number): string {
  if (value >= 0.7) {
    return '#b71c1c';
  }
  if (value >= 0.4) {
    return '#ef6c00';
  }
  return '#2e7d32';
}

export default function SubscoreList({title, items}: Props): React.JSX.Element {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {items.map(item => (
        <View key={item.name} style={styles.row}>
          <View style={styles.left}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.help}>{item.explanationFr}</Text>
          </View>
          <Text style={[styles.value, {color: severityColor(item.value)}]}>
            {Math.round(item.value * 100)}%
          </Text>
        </View>
      ))}
      {items.length === 0 ? (
        <Text style={styles.empty}>No subscores.</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 12,
  },
  title: {
    fontWeight: '700',
    marginBottom: 8,
    fontSize: 16,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#eeeeee',
    paddingVertical: 8,
    gap: 10,
  },
  left: {
    flex: 1,
  },
  name: {
    fontWeight: '600',
    color: '#263238',
    textTransform: 'capitalize',
  },
  help: {
    color: '#607d8b',
    marginTop: 2,
    fontSize: 12,
  },
  value: {
    fontWeight: '700',
    fontSize: 15,
  },
  empty: {
    color: '#607d8b',
  },
});
