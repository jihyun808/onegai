import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// 테스트마다 DOM을 비운다. 안 그러면 앞 테스트가 남긴 카드가 같이 잡힌다.
afterEach(cleanup)

// jsdom에는 오디오 재생 구현이 없어 pause()가 "Not implemented" 경고를 낸다.
// 미리듣기를 건드리는 테스트마다 시끄러워지므로 여기서 막아 둔다.
window.HTMLMediaElement.prototype.pause = function pause(this: HTMLMediaElement) {
  Object.defineProperty(this, 'paused', { value: true, configurable: true })
}
