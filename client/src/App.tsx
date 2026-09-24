import { useState } from 'react'

import { BottomNav, type Tab } from './components/BottomNav'
import { Logo } from './components/Logo'
import { WobbleFilter } from './components/WobbleFilter'
import { HomePage } from './pages/HomePage'
import { useSettings } from './hooks/useSettings'
import type { BrandFilter, SearchType } from './types/karaoke'
import { MyPage } from './pages/MyPage'
import { SettingsPage } from './pages/SettingsPage'
import './App.css'

export default function App() {
  const [tab, setTab] = useState<Tab>('home')
  const { settings } = useSettings()

  // 탭을 옮겨도 검색 상태가 유지되도록 여기서 들고 있는다
  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>(settings.searchType)
  const [brand, setBrand] = useState<BrandFilter>(settings.brand)

  return (
    <div className="app">
      <WobbleFilter />

      <header className="app__header">
        <Logo />
      </header>

      {/* 탭을 바꿔도 검색어와 북마크가 유지되도록 페이지만 갈아끼운다 */}
      <main className="app__main">
        {tab === 'home' && (
          <HomePage
            query={query}
            setQuery={setQuery}
            type={type}
            setType={setType}
            brand={brand}
            setBrand={setBrand}
          />
        )}
        {tab === 'mypage' && <MyPage />}
        {tab === 'settings' && <SettingsPage />}
      </main>

      <BottomNav value={tab} onChange={setTab} />
    </div>
  )
}
