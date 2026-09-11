import React from 'react';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import TodayScreen from './screens/TodayScreen';
import MapScreen from './screens/MapScreen';
import StationsScreen from './screens/StationsScreen';
import AccountScreen from './screens/AccountScreen';

const Tab = createBottomTabNavigator();

const theme = {
  ...DarkTheme,
  colors: { ...DarkTheme.colors, background: '#000', card: '#0c1013', primary: '#5fcf95' },
};

export default function App() {
  return (
    <NavigationContainer theme={theme}>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: '#5fcf95',
          tabBarInactiveTintColor: '#5c6479',
          tabBarStyle: { backgroundColor: '#0c1013', borderTopColor: '#1c2129' },
        }}
      >
        <Tab.Screen name="Today" component={TodayScreen} />
        <Tab.Screen name="Map" component={MapScreen} />
        <Tab.Screen name="Stations" component={StationsScreen} />
        <Tab.Screen name="Account" component={AccountScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
