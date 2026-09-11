import React, { useEffect, useState } from 'react';
import { View, Text, TextInput, StyleSheet, Button } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function AccountScreen() {
  const [nickname, setNickname] = useState('');
  const [token, setToken] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    AsyncStorage.multiGet(['gc_nickname', 'gc_token']).then((pairs) => {
      const map = Object.fromEntries(pairs);
      setNickname(map.gc_nickname || '');
      setToken(map.gc_token || genToken());
    });
  }, []);

  function genToken() {
    return Math.random().toString(36).slice(2, 10);
  }

  async function save() {
    await AsyncStorage.multiSet([['gc_nickname', nickname], ['gc_token', token]]);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Account</Text>
      <Text style={styles.sub}>Local nickname + token, stored only on this device — no server accounts.</Text>
      <Text style={styles.label}>Nickname</Text>
      <TextInput style={styles.input} value={nickname} onChangeText={setNickname} placeholder="Nickname" placeholderTextColor="#5c6479" />
      <Text style={styles.label}>Device token</Text>
      <Text style={styles.token}>{token}</Text>
      <View style={{ marginTop: 20 }}>
        <Button title={saved ? 'Saved' : 'Save'} onPress={save} color="#5fcf95" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000', padding: 20, paddingTop: 60 },
  title: { color: '#fff', fontSize: 28, fontWeight: '800', marginBottom: 8 },
  sub: { color: '#8b93a6', fontSize: 13, marginBottom: 24, lineHeight: 18 },
  label: { color: '#8b93a6', fontSize: 12, marginBottom: 6 },
  input: {
    backgroundColor: '#141821', borderRadius: 10, padding: 12, color: '#fff',
    fontSize: 15, marginBottom: 20,
  },
  token: { color: '#fff', fontSize: 15, fontFamily: 'Courier', marginBottom: 8 },
});
