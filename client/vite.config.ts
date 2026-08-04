import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
