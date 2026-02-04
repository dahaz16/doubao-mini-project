import axios from 'axios';

// 根据环境自动判断 API 基础路径
const baseURL = import.meta.env.PROD
    ? '/admin/api'  // 生产环境：部署到 FastAPI 时使用相对路径
    : 'http://localhost:8000/admin/api';  // 开发环境：直接访问后端

const api = axios.create({
    baseURL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器
api.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器
api.interceptors.response.use(
    (response) => {
        return response.data;
    },
    (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

// ============ 数据库查询相关 ============

export const getTables = () => api.get('/tables');

export const getTableData = (tableName, params) =>
    api.get(`/tables/${tableName}`, { params });

// ============ 系统配置相关 ============

export const getSysConfigs = () => api.get('/config/sys');

export const updateSysConfig = (configKey, configValue) =>
    api.put(`/config/sys/${configKey}`, { config_value: configValue });

// ============ 模型库相关 ============

export const getModels = () => api.get('/config/models');

export const createModel = (data) => api.post('/config/models', data);

export const updateModel = (modelId, data) =>
    api.put(`/config/models/${modelId}`, data);

export const deleteModel = (modelId) =>
    api.delete(`/config/models/${modelId}`);

// ============ 提示词配置相关 ============

export const getPrompts = () => api.get('/config/prompts');

export const createPrompt = (data) => api.post('/config/prompts', data);

export const togglePromptActive = (promptId) =>
    api.post(`/config/prompts/${promptId}/toggle`);

export default api;

// ============ 用户管理与采访库相关 ============

export const getUsersList = (params) => api.get('/users', { params });

export const deleteUserInterviewRecords = (userId) =>
    api.delete(`/users/${userId}/interview-records`);
