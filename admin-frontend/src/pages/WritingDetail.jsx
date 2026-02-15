import React, { useState, useEffect } from 'react';
import { Card, Descriptions, Table, message, Typography, Spin, Tag, Button, Space } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { getWritingStatus, getWritingCachepool, getMemoirArticles } from '../services/api';

const { Title, Paragraph } = Typography;

const WRITING_STATE_MAP = {
    0: { text: '待写作', color: 'default' },
    1: { text: '写作中', color: 'processing' },
};

export default function WritingDetail() {
    const { userId } = useParams();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [writingStatus, setWritingStatus] = useState(null);
    const [cachepool, setCachepool] = useState([]);
    const [totalWords, setTotalWords] = useState(0);
    const [articles, setArticles] = useState([]);

    useEffect(() => {
        loadAllData();
    }, [userId]);

    const loadAllData = async () => {
        setLoading(true);
        try {
            // 并行加载所有数据
            const [statusResult, cachepoolResult, articlesResult] = await Promise.all([
                getWritingStatus(userId),
                getWritingCachepool(userId),
                getMemoirArticles(userId),
            ]);

            console.log('API 响应数据:', {
                statusResult,
                cachepoolResult,
                articlesResult
            });

            // 处理 writing status
            setWritingStatus(statusResult?.data || statusResult);

            // 处理 cachepool - 兼容不同的响应格式
            const cachepoolData = cachepoolResult?.data || cachepoolResult;
            setCachepool(cachepoolData?.cachepool || []);
            setTotalWords(cachepoolData?.total_words || 0);

            // 处理 articles
            const articlesData = articlesResult?.data || articlesResult;
            setArticles(articlesData?.articles || []);
        } catch (error) {
            console.error('加载数据详细错误:', error);
            message.error('加载数据失败: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    const cachepoolColumns = [
        {
            title: 'Topic ID',
            dataIndex: 'topic_id',
            key: 'topic_id',
            width: 100,
        },
        {
            title: 'Topic 标题',
            dataIndex: 'topic_title',
            key: 'topic_title',
            width: 200,
        },
        {
            title: 'Topic 内容',
            dataIndex: 'topic_content',
            key: 'topic_content',
            ellipsis: true,
            render: (text) => (
                <Paragraph
                    ellipsis={{ rows: 2, expandable: true, symbol: '展开' }}
                    style={{ margin: 0 }}
                >
                    {text}
                </Paragraph>
            ),
        },
        {
            title: '字数',
            dataIndex: 'word_count',
            key: 'word_count',
            width: 80,
        },
        {
            title: '创建时间',
            dataIndex: 'created_time',
            key: 'created_time',
            width: 180,
            render: (time) => time ? new Date(time).toLocaleString('zh-CN') : '-',
        },
    ];

    const articlesColumns = [
        {
            title: 'Section ID',
            dataIndex: 'section_id',
            key: 'section_id',
            width: 100,
        },
        {
            title: '章节名',
            dataIndex: 'chapter_name',
            key: 'chapter_name',
            width: 150,
        },
        {
            title: '小节名',
            dataIndex: 'section_name',
            key: 'section_name',
            width: 200,
        },
        {
            title: '小节内容',
            dataIndex: 'section_content',
            key: 'section_content',
            ellipsis: true,
            render: (text) => (
                <Paragraph
                    ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                    style={{ margin: 0 }}
                >
                    {text}
                </Paragraph>
            ),
        },
        {
            title: '排序号',
            dataIndex: 'section_sort_num',
            key: 'section_sort_num',
            width: 80,
        },
        {
            title: '创建时间',
            dataIndex: 'created_time',
            key: 'created_time',
            width: 180,
            render: (time) => time ? new Date(time).toLocaleString('zh-CN') : '-',
        },
    ];

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '100px 0' }}>
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div>
            <Space style={{ marginBottom: 16 }}>
                <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/writing')}
                >
                    返回列表
                </Button>
            </Space>

            <Title level={2}>写作详情 - {userId}</Title>

            {/* 写作状态卡片 */}
            <Card title="写作状态" style={{ marginBottom: 16 }}>
                <Descriptions column={2}>
                    <Descriptions.Item label="写作状态">
                        {writingStatus && (
                            <Tag color={WRITING_STATE_MAP[writingStatus.writing_state]?.color}>
                                {WRITING_STATE_MAP[writingStatus.writing_state]?.text || '未知'}
                            </Tag>
                        )}
                    </Descriptions.Item>
                    <Descriptions.Item label="是否可写作">
                        {writingStatus?.ready ? (
                            <Tag color="success">是</Tag>
                        ) : (
                            <Tag color="default">否</Tag>
                        )}
                    </Descriptions.Item>
                    <Descriptions.Item label="缓存池字数">
                        {writingStatus?.words_count || 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="触发阈值">
                        {writingStatus?.threshold || 0}
                    </Descriptions.Item>
                    <Descriptions.Item label="是否首次写作">
                        {writingStatus?.is_first_time ? (
                            <Tag color="blue">是</Tag>
                        ) : (
                            <Tag color="default">否</Tag>
                        )}
                    </Descriptions.Item>
                </Descriptions>
            </Card>

            {/* 写作缓存池卡片 */}
            <Card
                title={`写作缓存池 (总字数: ${totalWords})`}
                style={{ marginBottom: 16 }}
            >
                <Table
                    columns={cachepoolColumns}
                    dataSource={cachepool}
                    rowKey="topic_id"
                    pagination={false}
                    scroll={{ x: 'max-content' }}
                />
            </Card>

            {/* 回忆录文章卡片 */}
            <Card title={`回忆录文章 (共 ${articles.length} 篇)`}>
                <Table
                    columns={articlesColumns}
                    dataSource={articles}
                    rowKey="section_id"
                    pagination={{ pageSize: 10 }}
                    scroll={{ x: 'max-content' }}
                />
            </Card>
        </div>
    );
}
