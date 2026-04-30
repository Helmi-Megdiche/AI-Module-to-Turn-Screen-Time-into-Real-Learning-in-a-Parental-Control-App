import React from 'react';
import {FlatList, StyleSheet, Text, View} from 'react-native';
import type {Recommendation} from '../services/behavioralService';

type Props = {
  items: Recommendation[];
};

export default function RecommendationsList({items}: Props): React.JSX.Element {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Recommendations</Text>
      <FlatList
        data={items}
        keyExtractor={item => String(item.id)}
        scrollEnabled={false}
        renderItem={({item}) => (
          <View style={styles.item}>
            <Text style={styles.message}>{item.messageFr}</Text>
            <Text style={styles.meta}>
              Severity: {item.severity} | Audience: {item.targetAudience}
            </Text>
            <Text style={styles.meta}>Trigger: {item.triggeringSubscore}</Text>
          </View>
        )}
        ListEmptyComponent={
          <Text style={styles.empty}>No recommendations.</Text>
        }
      />
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
  item: {
    borderBottomWidth: 1,
    borderBottomColor: '#eeeeee',
    paddingVertical: 8,
    gap: 4,
  },
  message: {
    color: '#263238',
  },
  meta: {
    color: '#607d8b',
    fontSize: 12,
  },
  empty: {
    color: '#607d8b',
  },
});
