import { HashRouter, Routes, Route } from 'react-router-dom';
import { useDashboardData } from './hooks/useDashboardData';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { TasksPage } from './pages/TasksPage';
import { ConversationsPage } from './pages/ConversationsPage';
import { AgentPage } from './pages/AgentPage';

export default function App() {
  const { data, connected, authRequired, loading } = useDashboardData();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted">
        Loading...
      </div>
    );
  }

  if (authRequired) {
    return <LoginPage onLogin={() => window.location.reload()} />;
  }

  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout connected={connected} data={data} />}>
          <Route index element={data ? <OverviewPage data={data} /> : null} />
          <Route path="tasks" element={data ? <TasksPage data={data} /> : null} />
          <Route path="conversations" element={<ConversationsPage />} />
          <Route path="agent" element={data ? <AgentPage data={data} /> : null} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
