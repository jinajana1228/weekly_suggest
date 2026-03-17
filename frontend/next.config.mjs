/** @type {import('next').NextConfig} */

// 배포 시 BACKEND_URL 환경변수로 백엔드 주소를 주입한다.
// 예: BACKEND_URL=https://weekly-suggest-api.railway.app
// 로컬 개발 시 기본값: http://localhost:8000
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
