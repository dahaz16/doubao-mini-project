import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/AppLayout';
import TableDetail from './pages/TableDetail';
import SysConfig from './pages/SysConfig';
import ModelConfig from './pages/ModelConfig';
import PromptConfig from './pages/PromptConfig';
import InterviewList from './pages/InterviewList';
import InterviewDetail from './pages/InterviewDetail';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router basename="/admin">
        <AppLayout>
          <Routes>
            <Route path="/" element={<InterviewList />} />
            <Route path="/interview" element={<InterviewList />} />
            <Route path="/interview/:userId" element={<InterviewDetail />} />
            <Route path="/table/:tableName" element={<TableDetail />} />
            <Route path="/config/sys" element={<SysConfig />} />
            <Route path="/config/models" element={<ModelConfig />} />
            <Route path="/config/prompts" element={<PromptConfig />} />
          </Routes>
        </AppLayout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
