import React, { useState, useEffect } from 'react';
import { Layout, Menu } from 'antd';
import {
    DatabaseOutlined,
    SettingOutlined,
    FileTextOutlined,
    ApiOutlined,
    TeamOutlined,
    EyeOutlined,
    ControlOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider, Content } = Layout;

// 所有数据库表名（按用户指定顺序）
const DB_TABLES = [
    'users', 'stage', 'topic', 'shot', 'character', 'hintboard', 'storyboard',
    'narration_status', 'llm_processed', 'tts_processed', 'asr_processed',
    'interview_original_text', 'interview_original_voice', 'prompt_config',
    'records', 'sys_config', 'base_models'
];

export default function AppLayout({ children }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [selectedKey, setSelectedKey] = useState('interview');
    const [openKeys, setOpenKeys] = useState(['interview', 'config', 'database']);

    useEffect(() => {
        // 根据当前路径设置选中的菜单项
        const path = location.pathname;

        if (path.startsWith('/interview')) {
            setSelectedKey('interview');
        } else if (path.includes('/config/sys')) {
            setSelectedKey('sys-config');
        } else if (path.includes('/config/models')) {
            setSelectedKey('models');
        } else if (path.includes('/config/prompts')) {
            setSelectedKey('prompts');
        } else if (path.startsWith('/table/')) {
            const tableName = path.split('/table/')[1];
            setSelectedKey(`table-${tableName}`);
        } else {
            setSelectedKey('interview');
        }
    }, [location]);

    // 构建菜单项
    const menuItems = [
        {
            key: 'interview',
            icon: <TeamOutlined />,
            label: '采访库',
            children: [
                {
                    key: 'interview-detail',
                    icon: <EyeOutlined />,
                    label: '采访详情',
                    onClick: () => navigate('/interview'),
                },
            ],
        },
        {
            key: 'config',
            icon: <SettingOutlined />,
            label: '配置管理',
            children: [
                {
                    key: 'sys-config',
                    icon: <ControlOutlined />,
                    label: '系统配置',
                    onClick: () => navigate('/config/sys'),
                },
                {
                    key: 'models',
                    icon: <ApiOutlined />,
                    label: '模型库',
                    onClick: () => navigate('/config/models'),
                },
                {
                    key: 'prompts',
                    icon: <FileTextOutlined />,
                    label: '提示词',
                    onClick: () => navigate('/config/prompts'),
                },
            ],
        },
        {
            key: 'database',
            icon: <DatabaseOutlined />,
            label: '数据库概览',
            children: DB_TABLES.map(tableName => ({
                key: `table-${tableName}`,
                label: tableName,
                onClick: () => navigate(`/table/${tableName}`),
            })),
        },
    ];

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider theme="dark" width={240}>
                <div style={{
                    color: 'white',
                    padding: '24px 16px',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    borderBottom: '1px solid rgba(255,255,255,0.1)'
                }}>
                    回忆录管理后台
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[selectedKey]}
                    openKeys={openKeys}
                    onOpenChange={setOpenKeys}
                    items={menuItems}
                    style={{ marginTop: 16 }}
                />
            </Sider>
            <Layout>
                <Content style={{ padding: 24, background: '#f0f2f5', minHeight: 280 }}>
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
