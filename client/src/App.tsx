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

  const [query, setQuery] = useState('')
  const [type, setType] = useState<SearchType>(settings.searchType)
  const [brand, setBrand] = useState<BrandFilter>(settings.brand)

  return (
    <div className="app">
      <WobbleFilter />

      <header className="app__header">
        <Logo />
      </header>

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
