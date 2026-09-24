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

// 글꼴이 준비되기 전에 기본 글꼴로 한 번 그려졌다가 바뀌면 화면이 튄다
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

  // 탭을 옮겨도 검색 상태가 유지되도록 여기서 들고 있는다
  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>(settings.searchType)
  const [brand, setBrand] = useState<BrandFilter>(settings.brand)

  const ready = fontsLoaded || Boolean(fontError)

  useEffect(() => {
    // 글꼴을 못 받아도 앱은 떠야 한다 — 기본 글꼴로 그린다
    if (ready) void SplashScreen.hideAsync()
  }, [ready])

  if (!ready) return null

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      <SafeAreaView style={styles.app} edges={['top']}>
        {/* 웹 .app__header — 왼쪽 정렬 */}
        <View style={styles.header}>
          <Logo />
        </View>

        {/* 탭을 바꿔도 검색어와 북마크가 유지되도록 화면만 갈아끼운다 */}
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
  // 웹 .app 좌우 여백 12px + 헤더 4px
  header: { paddingTop: 26, paddingHorizontal: 16, paddingBottom: 6 },
  main: { flex: 1 },
})
