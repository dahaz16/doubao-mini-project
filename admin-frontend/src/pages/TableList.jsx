import React, { useState, useEffect } from 'react';
import { Card, List, Spin, message, Typography } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';
import { getTables } from '../services/api';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

export default function TableList() {
    const [tables, setTables] = useState([]);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        loadTables();
    }, []);

    const loadTables = async () => {
        setLoading(true);
        try {
            const data = await getTables();
            setTables(data.tables || []);
        } catch (error) {
            message.error('加载表列表失败: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <Title level={2}>数据库表列表</Title>
            <Card>
                <Spin spinning={loading}>
                    <List
                        grid={{ gutter: 16, column: 3 }}
                        dataSource={tables}
                        renderItem={(table) => (
                            <List.Item>
                                <Card
                                    hoverable
                                    onClick={() => navigate(`/table/${table}`)}
                                    style={{ textAlign: 'center' }}
                                >
                                    <DatabaseOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                                    <div style={{ marginTop: 12, fontSize: 16 }}>{table}</div>
                                </Card>
                            </List.Item>
                        )}
                    />
                </Spin>
            </Card>
        </div>
    );
}
