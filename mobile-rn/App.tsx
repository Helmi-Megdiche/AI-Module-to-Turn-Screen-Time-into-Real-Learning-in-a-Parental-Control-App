import React, {useState} from 'react';
import {
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import TrackingScreen from './src/screens/TrackingScreen';
import WellbeingScreen from './src/screens/WellbeingScreen';

function App(): React.JSX.Element {
  const [activeScreen, setActiveScreen] = useState<'tracking' | 'wellbeing'>(
    'tracking',
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.navBar}>
        <TouchableOpacity
          style={[
            styles.navButton,
            activeScreen === 'tracking' && styles.navButtonActive,
          ]}
          onPress={() => setActiveScreen('tracking')}>
          <Text
            style={[
              styles.navButtonText,
              activeScreen === 'tracking' && styles.navButtonTextActive,
            ]}>
            Tracking
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.navButton,
            activeScreen === 'wellbeing' && styles.navButtonActive,
          ]}
          onPress={() => setActiveScreen('wellbeing')}>
          <Text
            style={[
              styles.navButtonText,
              activeScreen === 'wellbeing' && styles.navButtonTextActive,
            ]}>
            Wellbeing
          </Text>
        </TouchableOpacity>
      </View>
      <View style={styles.screen}>
        {activeScreen === 'tracking' ? <TrackingScreen /> : <WellbeingScreen />}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  navBar: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 6,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  navButton: {
    flex: 1,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: '#eceff1',
  },
  navButtonActive: {
    backgroundColor: '#1565c0',
  },
  navButtonText: {
    color: '#263238',
    fontWeight: '600',
  },
  navButtonTextActive: {
    color: '#ffffff',
  },
  screen: {
    flex: 1,
  },
});

export default App;
