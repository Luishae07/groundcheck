import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { fetchReadings, Reading } from '../api';

export default function StationsScreen() {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReadings()
      .then((rs) => setReadings(rs.sort((a, b) => b.tsunix - a.tsunix)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#5fcf95" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Stations</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={readings}
        keyExtractor={(r) => r.id}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View>
              <Text style={styles.id}>{item.id}</Text>
              <Text style={styles.meta}>{Math.round(item.alt)} m</Text>
            </View>
            <Text style={styles.temp}>{item.temp.toFixed(1)}°</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center' },
  title: { color: '#fff', fontSize: 28, fontWeight: '800', margin: 20, marginTop: 60 },
  error: { color: '#ff6b6b', marginHorizontal: 20, marginBottom: 10 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    backgroundColor: '#141821', borderRadius: 12, marginHorizontal: 20, marginBottom: 8, padding: 14,
  },
  id: { color: '#fff', fontSize: 15, fontWeight: '600' },
  meta: { color: '#8b93a6', fontSize: 12, marginTop: 2 },
  temp: { color: '#fff', fontSize: 20, fontWeight: '700' },
});
