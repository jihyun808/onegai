import { useState } from 'react'

import { BottomNav, type Tab } from './components/BottomNav'
import { Logo } from './components/Logo'
import { WobbleFilter } from './components/WobbleFilter'
import { HomePage } from './pages/HomePage'
import { MyPage } from './pages/MyPage'
import { SettingsPage } from './pages/SettingsPage'
import './App.css'

export default function App() {
  const [tab, setTab] = useState<Tab>('home')

  return (
    <div className="app">
      <WobbleFilter />

      <header className="app__header">
        <Logo />
      </header>

      {/* 탭을 바꿔도 검색어와 북마크가 유지되도록 페이지만 갈아끼운다 */}
      <main className="app__main">
        {tab === 'home' && <HomePage />}
        {tab === 'mypage' && <MyPage />}
        {tab === 'settings' && <SettingsPage />}
      </main>

      <BottomNav value={tab} onChange={setTab} />
    </div>
  )
}
