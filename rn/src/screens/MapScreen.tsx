import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ActivityIndicator, Text } from 'react-native';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';
import { fetchReadings, Reading } from '../api';

export default function MapScreen() {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReadings()
      .then(setReadings)
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

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  return (
    <MapView
      provider={PROVIDER_DEFAULT}
      style={styles.map}
      initialRegion={{
        latitude: readings[0]?.lat ?? 20,
        longitude: readings[0]?.lon ?? 0,
        latitudeDelta: 40,
        longitudeDelta: 40,
      }}
    >
      {readings.map((r) => (
        <Marker
          key={r.id}
          coordinate={{ latitude: r.lat, longitude: r.lon }}
          title={`${r.temp.toFixed(1)}°`}
          description={r.id}
        />
      ))}
    </MapView>
  );
}

const styles = StyleSheet.create({
  map: { flex: 1 },
  center: { flex: 1, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center' },
  error: { color: '#ff6b6b' },
});
