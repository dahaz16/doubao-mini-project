import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Input, Button, Space, message, Typography, Tag } from 'antd';
import { ArrowLeftOutlined, SearchOutlined } from '@ant-design/icons';
import { getTableData } from '../services/api';

const { Title } = Typography;
const { Search } = Input;

export default function TableDetail() {
    const { tableName } = useParams();
    const navigate = useNavigate();
    const [data, setData] = useState([]);
    const [columns, setColumns] = useState([]);
    const [loading, setLoading] = useState(false);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 20,
        total: 0,
    });
    const [searchText, setSearchText] = useState('');

    useEffect(() => {
        loadData();
    }, [tableName, pagination.current, searchText]);

    const loadData = async () => {
        setLoading(true);
        try {
            const result = await getTableData(tableName, {
                page: pagination.current,
                page_size: pagination.pageSize,
                search: searchText || undefined,
            });

            // 动态生成列
            const cols = result.columns.map(col => ({
                title: col.name,
                dataIndex: col.name,
                key: col.name,
                ellipsis: true,
                width: 150,
                render: (text) => {
                    if (text === null) return <Tag color="default">NULL</Tag>;
                    if (typeof text === 'boolean') return <Tag color={text ? 'green' : 'red'}>{text.toString()}</Tag>;
                    if (typeof text === 'string' && text.length > 100) {
                        return <span title={text}>{text.substring(0, 100)}...</span>;
                    }
                    return text;
                }
            }));

            setColumns(cols);
            setData(result.data);
            setPagination(prev => ({
                ...prev,
                total: result.total,
            }));
        } catch (error) {
            message.error('加载数据失败: ' + error.message);
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
            current: 1, // 搜索时重置到第一页
        }));
    };

    return (
        <div>
            <Space style={{ marginBottom: 16 }}>
                <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
                    返回
                </Button>
                <Title level={2} style={{ margin: 0 }}>
                    {tableName}
                </Title>
            </Space>

            <Card>
                <Space style={{ marginBottom: 16 }}>
                    <Search
                        placeholder="搜索..."
                        allowClear
                        enterButton={<SearchOutlined />}
                        onSearch={handleSearch}
                        style={{ width: 300 }}
                    />
                    <Button onClick={() => loadData()}>刷新</Button>
                </Space>

                <Table
                    columns={columns}
                    dataSource={data}
                    loading={loading}
                    pagination={{
                        ...pagination,
                        showSizeChanger: false,
                        showTotal: (total) => `共 ${total} 条记录`,
                    }}
                    onChange={handleTableChange}
                    scroll={{ x: 'max-content' }}
                    size="small"
                    rowKey={(record, index) => index}
                />
            </Card>
        </div>
    );
}
