import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Card,
    Table,
    Checkbox,
    DatePicker,
    Button,
    Modal,
    message,
    Tag,
    Space,
    Typography,
    Timeline,
    Collapse,
    Descriptions,
    Spin
} from 'antd';
import { CopyOutlined, ArrowLeftOutlined, FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Text } = Typography;

// 数据方类型配置
const DATA_TYPE_CONFIG = {
    user: { label: '用户', color: '#373737' },
    intv_output: { label: '念念', color: '#373737' },
    intv_input: { label: 'Intv输入', color: '#A6A6A6' },
    stn_input: { label: 'Stn输入', color: '#A6A6A6' },
    stn_output: { label: 'Stn输出', color: '#A6A6A6' },
    dir_input: { label: 'Dir输入', color: '#A6A6A6' },
    dir_output: { label: '导演提示', color: '#373737' }
};

const ALL_DATA_TYPES = Object.keys(DATA_TYPE_CONFIG);

export default function InterviewDetail() {
    const { userId } = useParams();
    const navigate = useNavigate();

    // 状态管理
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(50);

    // 默认仅选中 用户、念念 和 导演提示
    const [selectedTypes, setSelectedTypes] = useState(['user', 'intv_output', 'dir_output']);
    const [timeRange, setTimeRange] = useState([
        dayjs().startOf('day'),
        dayjs().endOf('day')
    ]);

    // 弹窗状态
    const [modalVisible, setModalVisible] = useState(false);
    const [modalContent, setModalContent] = useState(null);

    // Debug 日志状态
    const [debugLogsVisible, setDebugLogsVisible] = useState(false);
    const [debugLogsData, setDebugLogsData] = useState(null);
    const [debugLogsLoading, setDebugLogsLoading] = useState(false);

    // 获取数据
    const fetchData = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                page_size: pageSize.toString()
            });

            if (selectedTypes.length > 0) {
                params.append('data_types', selectedTypes.join(','));
            }

            if (timeRange && timeRange[0] && timeRange[1]) {
                params.append('start_time', timeRange[0].toISOString());
                params.append('end_time', timeRange[1].toISOString());
            }

            const response = await fetch(
                `/admin/api/users/${userId}/interview-details?${params.toString()}`
            );

            if (!response.ok) {
                throw new Error('获取数据失败');
            }

            const result = await response.json();

            if (result.code === 0) {
                setData(result.data.records);
                setTotal(result.data.total);
            } else {
                message.error('获取数据失败');
            }
        } catch (error) {
            console.error('获取数据失败:', error);
            message.error('获取数据失败');
        } finally {
            setLoading(false);
        }
    };

    // 初始加载和筛选条件变化时重新加载
    useEffect(() => {
        fetchData();
    }, [page, selectedTypes, timeRange]);

    // 复制内容
    const handleCopy = (content) => {
        const text = typeof content === 'string'
            ? content
            : JSON.stringify(content, null, 2);

        navigator.clipboard.writeText(text).then(() => {
            message.success('已复制到剪贴板');
        }).catch(() => {
            message.error('复制失败');
        });
    };

    // 查看详细内容
    const handleViewDetail = (content) => {
        setModalContent(content);
        setModalVisible(true);
    };

    // 获取 Debug 日志
    const fetchDebugLogs = async () => {
        setDebugLogsLoading(true);
        setDebugLogsVisible(true);
        try {
            const params = new URLSearchParams();

            if (timeRange && timeRange[0] && timeRange[1]) {
                params.append('start_time', timeRange[0].toISOString());
                params.append('end_time', timeRange[1].toISOString());
            }

            const response = await fetch(
                `/admin/api/users/${userId}/debug-logs?${params.toString()}`
            );

            if (!response.ok) {
                throw new Error('获取日志失败');
            }

            const result = await response.json();

            if (result.code === 0) {
                setDebugLogsData(result.data);
            } else {
                message.error('获取日志失败');
            }
        } catch (error) {
            console.error('获取日志失败:', error);
            message.error('获取日志失败');
        } finally {
            setDebugLogsLoading(false);
        }
    };

    // 表格列配置
    const columns = [
        {
            title: '数据方',
            dataIndex: 'data_type',
            key: 'data_type',
            width: 100,
            render: (type, record) => {
                const config = DATA_TYPE_CONFIG[type];
                const color = config?.color || '#373737';

                // 如果是用户类型，显示真实用户名
                let displayText = config?.label || type;
                if (type === 'user' && record.user_name) {
                    displayText = record.user_name;
                }

                return <Text style={{ color }}>{displayText}</Text>;
            }
        },
        {
            title: '日期',
            dataIndex: 'date',
            key: 'date',
            width: 80,
            render: (text, record) => {
                const config = DATA_TYPE_CONFIG[record.data_type];
                const color = config?.color || '#373737';
                return <Text style={{ color }}>{dayjs(record.created_time).format("YYYY-MM-DD")}</Text>;
            }
        },
        {
            title: '时间',
            dataIndex: 'time',
            key: 'time',
            width: 70,
            render: (text, record) => {
                const config = DATA_TYPE_CONFIG[record.data_type];
                const color = config?.color || '#373737';
                return <Text style={{ color }}>{dayjs(record.created_time).format("HH:mm:ss")}</Text>;
            }
        },
        {
            title: '音频',
            dataIndex: 'audio_url',
            key: 'audio_url',
            width: 40,
            render: (url, record) => {
                if (!record.has_audio || !url) {
                    return <Text type="secondary" style={{ color: '#373737' }}>-</Text>;
                }
                return (
                    <Button
                        type="link"
                        size="small"
                        style={{ color: '#1890FF', padding: 0 }}
                        onClick={() => {
                            const audio = new Audio(url);
                            audio.play().catch(e => message.error('播放失败: ' + e.message));
                        }}
                    >
                        播放
                    </Button>
                );
            }
        },
        {
            title: '内容',
            dataIndex: 'content',
            key: 'content',
            width: 760,
            render: (text, record) => {
                const config = DATA_TYPE_CONFIG[record.data_type];
                // 导演提示的内容用橙色
                const contentColor = record.data_type === 'dir_output' ? '#FF5200' : config?.color || '#373737';

                // 用户、念念、导演提示：直接展示全部内容
                if (['user', 'intv_output', 'dir_output'].includes(record.data_type)) {
                    // 确保取到最完整的内容，不再仅限于 string 判断
                    const displayContent = record.full_content && typeof record.full_content === 'string'
                        ? record.full_content
                        : (record.content || record.content_preview);

                    return (
                        <div style={{
                            color: contentColor,
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            width: '100%'
                        }}>
                            {displayContent}
                        </div>
                    );
                }

                // 其他类型：点击内容区域弹出详情
                return (
                    <div
                        style={{
                            color: contentColor,
                            cursor: 'pointer', // 增加手型暗示可点击
                            textDecoration: 'underline dotted', // 加个虚线下划线提示
                            textUnderlineOffset: '4px'
                        }}
                        onClick={() => handleViewDetail(record.full_content)}
                    >
                        {record.content_preview}
                    </div>
                );
            }
        },
        {
            title: 'Session ID',
            dataIndex: 'session_id',
            key: 'session_id',
            width: 70,
            ellipsis: true,
            render: (text) => <Text style={{ color: '#373737' }}>{text}</Text>
        },
        {
            title: 'Model',
            dataIndex: 'model_name',
            key: 'model_name',
            width: 110,
            render: (text) => <Text style={{ color: '#373737' }}>{text}</Text>
        },
        {
            title: 'Tokens',
            dataIndex: 'tokens',
            key: 'tokens',
            width: 170,
            render: (text) => <Text style={{ color: '#373737' }}>{text}</Text>
        },
        {
            title: 'Prompt',
            dataIndex: 'prompt',
            key: 'prompt',
            width: 60,
            render: (text) => <Text style={{ color: '#373737' }}>{text}</Text>
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            fixed: 'right',
            render: (_, record) => (
                <Button
                    type="link"
                    style={{
                        color: '#1890FF',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '2px' // 缩小图标与文字距离
                    }}
                    onClick={() => handleCopy(record.full_content)}
                >
                    <CopyOutlined />
                    <span>复制内容</span>
                </Button>
            )
        }
    ];

    // 数据方类型选项
    const dataTypeOptions = ALL_DATA_TYPES.map(type => ({
        label: DATA_TYPE_CONFIG[type].label,
        value: type
    }));

    return (
        <div style={{ padding: '24px' }}>
            {/* 头部 */}
            <Card style={{ marginBottom: '16px' }}>
                <Space>
                    <Button
                        icon={<ArrowLeftOutlined />}
                        onClick={() => navigate('/admin/interview-list')}
                    >
                        返回
                    </Button>
                    <Text strong style={{ fontSize: '16px' }}>
                        用户采访详情 - {userId}
                    </Text>
                    <Button
                        type="primary"
                        icon={<FileTextOutlined />}
                        onClick={fetchDebugLogs}
                        style={{ marginLeft: '16px' }}
                    >
                        查看日志
                    </Button>
                </Space>
            </Card>

            {/* 筛选区域 */}
            <Card style={{ marginBottom: '16px' }}>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <div>
                        <Text strong style={{ marginRight: '8px' }}>数据方类型：</Text>
                        <Checkbox.Group
                            options={dataTypeOptions}
                            value={selectedTypes}
                            onChange={(values) => {
                                setSelectedTypes(values);
                                setPage(1); // 重置到第一页
                            }}
                        />
                    </div>

                    <div>
                        <Text strong style={{ marginRight: '8px' }}>时间范围：</Text>
                        <RangePicker
                            showTime
                            format="YYYY-MM-DD HH:mm:ss"
                            value={timeRange}
                            onChange={(dates) => {
                                setTimeRange(dates);
                                setPage(1); // 重置到第一页
                            }}
                        />
                    </div>
                </Space>
            </Card>

            {/* 数据表格 */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={data}
                    rowKey="record_id"
                    loading={loading}
                    size="small"
                    scroll={{ x: 1560 }}
                    pagination={{
                        current: page,
                        pageSize: pageSize,
                        total: total,
                        showSizeChanger: false,
                        showTotal: (total) => `共 ${total} 条记录`,
                        onChange: (newPage) => setPage(newPage)
                    }}
                />
            </Card>

            {/* 内容详情弹窗 */}
            <Modal
                title="查看详细内容"
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                footer={[
                    <Button key="copy" onClick={() => handleCopy(modalContent)}>
                        复制
                    </Button>,
                    <Button key="close" type="primary" onClick={() => setModalVisible(false)}>
                        关闭
                    </Button>
                ]}
                width={800}
            >
                <pre style={{
                    maxHeight: '500px',
                    overflow: 'auto',
                    backgroundColor: '#f5f5f5',
                    padding: '16px',
                    borderRadius: '4px'
                }}>
                    {typeof modalContent === 'string'
                        ? modalContent
                        : JSON.stringify(modalContent, null, 2)}
                </pre>
            </Modal>

            {/* Debug 日志弹窗 */}
            <Modal
                title="Debug 日志查看器"
                open={debugLogsVisible}
                onCancel={() => setDebugLogsVisible(false)}
                footer={[
                    <Button key="close" onClick={() => setDebugLogsVisible(false)}>
                        关闭
                    </Button>
                ]}
                width={1800}
                centered
            >
                {debugLogsLoading ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Spin size="large" />
                    </div>
                ) : debugLogsData ? (
                    <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
                        {/* Narration Status */}
                        <Collapse defaultActiveKey={['1']} style={{ marginBottom: '16px' }}>
                            <Collapse.Panel header="📊 Narration Status (Session 状态)" key="1">
                                {debugLogsData.narration_status ? (
                                    <Descriptions bordered size="small" column={2}>
                                        <Descriptions.Item label="Intv Session ID" span={2}>
                                            {debugLogsData.narration_status.intv_llm_session_id || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Intv Word Count">
                                            {debugLogsData.narration_status.intv_llm_session_word_count}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Intv Expire At">
                                            {debugLogsData.narration_status.intv_llm_session_expire_at || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Intv Previous Response ID" span={2}>
                                            {debugLogsData.narration_status.intv_llm_session_previous_response_id || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Intv Hint ID">
                                            {debugLogsData.narration_status.intv_llm_hint_id || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Stn Session ID" span={2}>
                                            {debugLogsData.narration_status.stn_llm_session_id || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Stn Word Count">
                                            {debugLogsData.narration_status.stn_llm_session_word_count}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Dir Session ID" span={2}>
                                            {debugLogsData.narration_status.dir_llm_session_id || '-'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Cachepool Content" span={2}>
                                            <pre style={{ maxHeight: '100px', overflow: 'auto', margin: 0 }}>
                                                {debugLogsData.narration_status.chat_cachepool_content || '-'}
                                            </pre>
                                        </Descriptions.Item>
                                    </Descriptions>
                                ) : (
                                    <Text type="secondary">无数据</Text>
                                )}
                            </Collapse.Panel>
                        </Collapse>

                        {/* Active Prompts */}
                        <Collapse style={{ marginBottom: '16px' }}>
                            <Collapse.Panel header="💡 Active Prompts (当前激活的提示词)" key="2">
                                {Object.entries(debugLogsData.active_prompts).map(([agent, prompt]) => (
                                    <div key={agent} style={{ marginBottom: '16px' }}>
                                        <Text strong>{agent.toUpperCase()} Agent:</Text>
                                        {prompt ? (
                                            <div>
                                                <Tag color="blue">Prompt ID: {prompt.prompt_id}</Tag>
                                                {prompt.remark && <Tag>{prompt.remark}</Tag>}
                                                <pre style={{
                                                    marginTop: '8px',
                                                    padding: '8px',
                                                    backgroundColor: '#f5f5f5',
                                                    maxHeight: '150px',
                                                    overflow: 'auto'
                                                }}>
                                                    {prompt.content}
                                                </pre>
                                            </div>
                                        ) : (
                                            <Text type="secondary"> 无激活提示词</Text>
                                        )}
                                    </div>
                                ))}
                            </Collapse.Panel>
                        </Collapse>

                        {/* Timeline Logs */}
                        <div>
                            <Text strong style={{ fontSize: '16px' }}>🕒 时间线日志</Text>
                            <Timeline
                                style={{ marginTop: '16px' }}
                                items={debugLogsData.logs.map((log, index) => {
                                    const date = new Date(log.timestamp);
                                    const timeStr = `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;
                                    let color = 'blue';

                                    if (log.log_type === 'user_input') {
                                        color = 'green';
                                    } else if (log.log_type === 'ai_output') {
                                        color = 'cyan';
                                    } else if (log.log_type === 'llm_call') {
                                        color = 'purple';
                                    } else if (log.log_type === 'asr_call') {
                                        color = 'orange';
                                    } else if (log.log_type === 'tts_call') {
                                        color = 'blue';
                                    }

                                    return {
                                        color: color,
                                        children: (
                                            <div key={index}>
                                                <div style={{ marginBottom: '8px' }}>
                                                    {log.log_type === 'user_input' ? (
                                                        <>
                                                            <Tag color={color}>
                                                                <strong>{log.user_name || '用户'}</strong>
                                                            </Tag>
                                                            <span style={{ color: '#A6A6A6', fontSize: '12px' }}>
                                                                {log.has_audio ? '(语音)' : '(打字)'}
                                                            </span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Tag color={color}>
                                                                {log.log_type === 'ai_output' ? 'AI 输出' :
                                                                    log.log_type === 'llm_call' ? `LLM 调用 (${log.agent})` :
                                                                        log.log_type === 'asr_call' ? 'ASR 调用' :
                                                                            log.log_type === 'tts_call' ? 'TTS 调用' : log.log_type}
                                                            </Tag>
                                                            {log.model_name && <Tag>{log.model_name}</Tag>}
                                                            {log.has_audio && log.log_type !== 'user_input' && <Tag color="orange">有音频</Tag>}
                                                        </>
                                                    )}
                                                </div>
                                                <div style={{ fontSize: '12px', color: '#999', marginBottom: '8px' }}>
                                                    {timeStr}
                                                </div>

                                                {log.log_type === 'llm_call' ? (
                                                    <Collapse size="small">
                                                        <Collapse.Panel header="查看详情" key="1">
                                                            <Descriptions
                                                                bordered
                                                                size="small"
                                                                column={1}
                                                                labelStyle={{ width: '150px' }}
                                                            >
                                                                <Descriptions.Item label="Tokens">
                                                                    Total: {log.tokens.total},
                                                                    Prompt: {log.tokens.prompt},
                                                                    Completion: {log.tokens.completion},
                                                                    Cached: {log.tokens.cached}
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="Duration">
                                                                    {log.duration_ms} ms
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="Cost">
                                                                    ¥{log.cost.toFixed(4)}
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="LLM Input">
                                                                    <pre style={{
                                                                        maxHeight: '200px',
                                                                        overflow: 'auto',
                                                                        margin: 0,
                                                                        padding: '8px',
                                                                        backgroundColor: '#f5f5f5',
                                                                        whiteSpace: 'pre-wrap',
                                                                        wordBreak: 'break-word'
                                                                    }}>
                                                                        {typeof log.llm_input === 'string'
                                                                            ? log.llm_input
                                                                            : JSON.stringify(log.llm_input, null, 2)}
                                                                    </pre>
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="LLM Output">
                                                                    <pre style={{
                                                                        maxHeight: '200px',
                                                                        overflow: 'auto',
                                                                        margin: 0,
                                                                        padding: '8px',
                                                                        backgroundColor: '#f5f5f5',
                                                                        whiteSpace: 'pre-wrap',
                                                                        wordBreak: 'break-word'
                                                                    }}>
                                                                        {log.llm_output}
                                                                    </pre>
                                                                </Descriptions.Item>
                                                            </Descriptions>
                                                        </Collapse.Panel>
                                                    </Collapse>
                                                ) : (log.log_type === 'asr_call' || log.log_type === 'tts_call') ? (
                                                    <Collapse size="small">
                                                        <Collapse.Panel header="查看详情" key="1">
                                                            <Descriptions
                                                                bordered
                                                                size="small"
                                                                column={1}
                                                                labelStyle={{ width: '150px' }}
                                                            >
                                                                <Descriptions.Item label="模型名称">
                                                                    {log.model_name}
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="Duration">
                                                                    {log.duration_ms} ms
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="Cost">
                                                                    ¥{log.cost.toFixed(6)}
                                                                </Descriptions.Item>
                                                                <Descriptions.Item label="关联文本 ID">
                                                                    {log.related_text_id}
                                                                </Descriptions.Item>
                                                            </Descriptions>
                                                        </Collapse.Panel>
                                                    </Collapse>
                                                ) : (
                                                    <div style={{
                                                        padding: '8px',
                                                        backgroundColor: '#f9f9f9',
                                                        borderRadius: '4px',
                                                        maxHeight: '150px',
                                                        overflow: 'auto'
                                                    }}>
                                                        {log.content}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    };
                                })}
                            />
                        </div>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px' }}>
                        <Text type="secondary">暂无日志数据</Text>
                    </div>
                )}
            </Modal>

            {/* 自定义样式 */}
            <style jsx>{`
        .data-type-user { color: #1890ff; }
        .data-type-intv_output { color: #52c41a; }
        .data-type-intv_input { color: #fa8c16; }
        .data-type-stn_input { color: #722ed1; }
        .data-type-stn_output { color: #13c2c2; }
        .data-type-dir_input { color: #eb2f96; }
        .data-type-dir_output { color: #f5222d; }
      `}</style>
        </div>
    );
}
