// vitest 설정(test 키)까지 타입이 붙은 defineConfig다. 'vite'에서 가져오면
// `tsc -b`가 test 키를 모르는 속성이라고 막는다.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    // 테스트마다 spy를 원래대로 돌린다. 없으면 fetch 호출 횟수가 누적돼
    // "한 번만 불렀나" 같은 검사가 앞 테스트에 오염된다.
    restoreMocks: true,
    // 브라우저 전체를 띄우는 확인은 여기 넣지 않는다. 여기는 단위 테스트다.
    include: ['src/**/*.test.{ts,tsx}'],
  },
  server: {
    // 컨테이너 안에서 돌 때 외부에서 접근할 수 있게 한다
    host: true,
    // /api 요청을 Flask 서버로 넘긴다.
    // 같은 오리진에서 부르는 셈이라 개발 중 CORS를 신경 쓸 필요가 없다.
    proxy: {
      '/api': {
        // 호스트에서 실행하면 localhost, 도커에서는 server 컨테이너를 본다
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
})
