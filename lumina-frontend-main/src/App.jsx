import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import ChatPage from "./pages/ChatPage";
import ClusterPage from "./pages/ClusterPage";
import HealthPage from "./pages/HealthPage";
import TracePage from "./pages/TracePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="cluster" element={<ClusterPage />} />
        <Route path="health" element={<HealthPage />} />
        <Route path="trace" element={<TracePage />} />
      </Route>
    </Routes>
  );
}