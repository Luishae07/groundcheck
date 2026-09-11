import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, RefreshControl, ScrollView } from 'react-native';
import Geolocation from '@react-native-community/geolocation';
import { PermissionsAndroid, Platform } from 'react-native';
import { fetchReadings, nearestReading, Reading } from '../api';

export default function TodayScreen() {
  const [reading, setReading] = useState<Reading | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLocation = useCallback((): Promise<{ lat: number; lon: number }> => {
    return new Promise((resolve) => {
      const done = (lat: number, lon: number) => resolve({ lat, lon });
      const askAndGet = () => {
        Geolocation.getCurrentPosition(
          (pos) => done(pos.coords.latitude, pos.coords.longitude),
          () => done(0, 0),
          { enableHighAccuracy: false, timeout: 8000 }
        );
      };
      if (Platform.OS === 'android') {
        PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION)
          .then((granted) => {
            if (granted === PermissionsAndroid.RESULTS.GRANTED) askAndGet();
            else done(0, 0);
          })
          .catch(() => done(0, 0));
      } else {
        Geolocation.requestAuthorization('whenInUse');
        askAndGet();
      }
    });
  }, []);

  const load = useCallback(async () => {
    try {
      setError(null);
      const readings = await fetchReadings();
      const { lat, lon } = await getLocation();
      setReading(nearestReading(readings, lat, lon));
    } catch (e: any) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [getLocation]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#5fcf95" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor="#5fcf95" />}
    >
      <Text style={styles.title}>Groundcheck</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      {reading && (
        <View style={styles.card}>
          <Text style={styles.stationId}>Station {reading.id}</Text>
          <Text style={styles.temp}>{reading.temp.toFixed(1)}°</Text>
          <View style={styles.statsRow}>
            <Stat label="Humidity" value={reading.humidity != null ? `${reading.humidity}%` : '—'} />
            <Stat label="Pressure" value={reading.pressure != null ? `${reading.pressure} hPa` : '—'} />
            <Stat label="Altitude" value={`${Math.round(reading.alt)} m`} />
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center' },
  title: { color: '#fff', fontSize: 34, fontWeight: '800', margin: 20, marginTop: 60 },
  error: { color: '#ff6b6b', marginHorizontal: 20, marginBottom: 10 },
  card: { backgroundColor: '#141821', borderRadius: 18, marginHorizontal: 20, padding: 24, alignItems: 'center' },
  stationId: { color: '#8b93a6', fontSize: 14, marginBottom: 10 },
  temp: { color: '#fff', fontSize: 64, fontWeight: '700' },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginTop: 20 },
  stat: { alignItems: 'center', flex: 1 },
  statLabel: { color: '#8b93a6', fontSize: 12 },
  statValue: { color: '#fff', fontSize: 15, fontWeight: '600', marginTop: 4 },
});
