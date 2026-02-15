import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Input, message, Typography, Space, Popconfirm, Tag } from 'antd';
import { SearchOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import { getWritingUsers, deleteMemoirArticle } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;
const { Search } = Input;

const WRITING_STATE_MAP = {
    0: { text: '待写作', color: 'default' },
    1: { text: '写作中', color: 'processing' },
};

export default function WritingList() {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 20,
        total: 0,
    });
    const [searchText, setSearchText] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        loadUsers();
    }, [pagination.current, searchText]);

    const loadUsers = async () => {
        setLoading(true);
        try {
            const result = await getWritingUsers({
                page: pagination.current,
                page_size: pagination.pageSize,
                search: searchText || undefined,
            });

            setUsers(result.data || []);
            setPagination(prev => ({
                ...prev,
                total: result.total,
            }));
        } catch (error) {
            message.error('加载用户列表失败: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleTableChange = (newPagination) => {
        setPagination(prev => ({
            ...prev,
            current: newPagination.current,
        }));
    };

    const handleSearch = (value) => {
        setSearchText(value);
        setPagination(prev => ({
            ...prev,
            current: 1,
        }));
    };

    const handleViewWriting = (userId) => {
        navigate(`/writing/${userId}`);
    };

    const handleDeleteMemoir = async (userId) => {
        try {
            const result = await deleteMemoirArticle(userId);
            message.success(`删除成功!共删除 ${result.data.deleted_count} 篇文章`);
            // 刷新列表
            loadUsers();
        } catch (error) {
            message.error('删除失败: ' + (error.response?.data?.detail || error.message));
        }
    };

    const columns = [
        {
            title: 'User ID',
            dataIndex: 'user_id',
            key: 'user_id',
            width: 280,
            ellipsis: true,
        },
        {
            title: '用户名',
            dataIndex: 'user_name',
            key: 'user_name',
            width: 150,
        },
        {
            title: 'OpenID',
            dataIndex: 'wechat_openid',
            key: 'wechat_openid',
            width: 250,
            ellipsis: true,
        },
        {
            title: '注册时间',
            dataIndex: 'created_time',
            key: 'created_time',
            width: 180,
            render: (time) => time ? new Date(time).toLocaleString('zh-CN') : '-',
        },
        {
            title: '操作',
            key: 'action',
            width: 250,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    <Popconfirm
                        title="确定要删除该用户的所有回忆录吗?"
                        description="此操作将清空 memoir_article、writing_source_cachepool 表,并重置 writing_status 和 topic.topic_writing_state。"
                        onConfirm={() => handleDeleteMemoir(record.user_id)}
                        okText="确定"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                    >
                        <Button
                            danger
                            size="small"
                            icon={<DeleteOutlined />}
                        >
                            删除回忆录
                        </Button>
                    </Popconfirm>
                    <Button
                        type="primary"
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleViewWriting(record.user_id)}
                    >
                        查看写作内容
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <Title level={2}>写作详情</Title>
            <Card>
                <Space style={{ marginBottom: 16 }}>
                    <Search
                        placeholder="搜索用户名、OpenID..."
                        allowClear
                        enterButton={<SearchOutlined />}
                        onSearch={handleSearch}
                        style={{ width: 400 }}
                    />
                    <Button onClick={() => loadUsers()}>刷新</Button>
                </Space>

                <Table
                    columns={columns}
                    dataSource={users}
                    loading={loading}
                    pagination={{
                        ...pagination,
                        showSizeChanger: false,
                        showTotal: (total) => `共 ${total} 位用户`,
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 'max-content' }}
                    rowKey="user_id"
                />
            </Card>
        </div>
    );
}
