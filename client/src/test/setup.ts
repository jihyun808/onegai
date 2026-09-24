import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)

window.HTMLMediaElement.prototype.pause = function pause(this: HTMLMediaElement) {
  Object.defineProperty(this, 'paused', { value: true, configurable: true })
}
