import React from 'react';
import {FlatList, StyleSheet, Text, View} from 'react-native';
import type {Mission} from '../services/behavioralService';

type Props = {
  items: Mission[];
};

export default function MissionsList({items}: Props): React.JSX.Element {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Missions</Text>
      <FlatList
        data={items}
        keyExtractor={item => String(item.id)}
        scrollEnabled={false}
        renderItem={({item}) => (
          <View style={styles.item}>
            <Text style={styles.mission}>{item.mission}</Text>
            <Text style={styles.meta}>
              Points: {item.points} | Type: {item.type} | Difficulty:{' '}
              {String(item.difficulty)}
            </Text>
            <Text style={styles.meta}>
              Status: {item.status} | Audience: {item.targetAudience}
            </Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.empty}>No missions.</Text>}
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
  mission: {
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
