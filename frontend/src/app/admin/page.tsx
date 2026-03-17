import { AdminDashboard } from "@/components/admin/AdminDashboard";

// Admin 페이지는 전체 CSR — API 키를 브라우저에서 관리하기 때문에
// SSR fetch 없이 AdminDashboard가 직접 key 입력 + 데이터 로드를 처리한다.
export default function AdminPage() {
  return <AdminDashboard />;
}
