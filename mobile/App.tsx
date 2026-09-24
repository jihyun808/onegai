import { useEffect, useState } from 'react'
import { StyleSheet, View } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context'
import * as SplashScreen from 'expo-splash-screen'
import { useFonts } from 'expo-font'
import { Gaegu_400Regular, Gaegu_700Bold } from '@expo-google-fonts/gaegu'
import {
  NotoSansKR_400Regular,
  NotoSansKR_600SemiBold,
  NotoSansKR_700Bold,
} from '@expo-google-fonts/noto-sans-kr'

import { BottomNav, type Tab } from './src/components/BottomNav'
import { Logo } from './src/components/Logo'
import { useSettings } from './src/hooks/useSettings'
import { HomeScreen } from './src/screens/HomeScreen'
import { MyScreen } from './src/screens/MyScreen'
import { SettingsScreen } from './src/screens/SettingsScreen'
import { colors } from './src/theme'
import type { BrandFilter, SearchType } from './src/types/karaoke'

void SplashScreen.preventAutoHideAsync()

export default function App() {
  const [fontsLoaded, fontError] = useFonts({
    Gaegu_400Regular,
    Gaegu_700Bold,
    NotoSansKR_400Regular,
    NotoSansKR_600SemiBold,
    NotoSansKR_700Bold,
    Jalnan: require('./assets/fonts/Jalnan.ttf'),
  })

  const [tab, setTab] = useState<Tab>('home')
  const { settings } = useSettings()

  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>(settings.searchType)
  const [brand, setBrand] = useState<BrandFilter>(settings.brand)

  const ready = fontsLoaded || Boolean(fontError)

  useEffect(() => {
    if (ready) void SplashScreen.hideAsync()
  }, [ready])

  if (!ready) return null

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <SafeAreaView style={styles.app} edges={['top']}>
        <View style={styles.header}>
          <Logo />
        </View>

        <View style={styles.main}>
          {tab === 'home' && (
            <HomeScreen
              query={query}
              setQuery={setQuery}
              type={type}
              setType={setType}
              brand={brand}
              setBrand={setBrand}
            />
          )}
          {tab === 'mypage' && <MyScreen />}
          {tab === 'settings' && <SettingsScreen />}
        </View>

        <BottomNav value={tab} onChange={setTab} />
      </SafeAreaView>
    </SafeAreaProvider>
  )
}

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: colors.ivory },
  header: { paddingTop: 26, paddingHorizontal: 16, paddingBottom: 6 },
  main: { flex: 1 },
})
