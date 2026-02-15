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
    Spin,
    Tabs,
    Popover
} from 'antd';
import { CopyOutlined, FileTextOutlined, ClockCircleOutlined, DownloadOutlined } from '@ant-design/icons';
import ReactJson from 'react-json-view';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Text, Title } = Typography;

// 数据方类型配置
const DATA_TYPE_CONFIG = {
    user: { label: '用户', color: '#373737' },
    intv_output: { label: '念念', color: '#373737' },
    stn_llm: { label: 'Stn LLM', color: '#A6A6A6' },
    dir_llm: { label: 'Dir LLM', color: '#373737' },
    feedback: { label: '用户反馈', color: '#6126FF' }
};

const ALL_DATA_TYPES = Object.keys(DATA_TYPE_CONFIG);

// 尝试解析 JSON 字符串
const tryParseJSON = (str) => {
    if (typeof str !== 'string') return str;
    try {
        const parsed = JSON.parse(str);
        if (parsed && typeof parsed === 'object') {
            return parsed;
        }
    } catch (e) {
        // ignore
    }
    return str;
};

// 隐藏 system role 的 content 字段
const maskSystemContent = (obj) => {
    if (!obj || typeof obj !== 'object') return obj;

    if (Array.isArray(obj)) {
        return obj.map(item => maskSystemContent(item));
    }

    const newObj = { ...obj };

    // 如果当前对象有 role === 'system',则将其 content 替换为 "-"
    if (newObj.role === 'system' && 'content' in newObj) {
        newObj.content = '-';
    }

    // 递归处理所有嵌套对象
    for (const key in newObj) {
        if (typeof newObj[key] === 'object' && newObj[key] !== null) {
            newObj[key] = maskSystemContent(newObj[key]);
        }
    }

    return newObj;
};

// 内容展示组件 - 使用 ReactJson 展示
const ContentSection = ({ title, content, color }) => {
    if (!content && content !== 0) return null;

    let displayContent = content;
    // 递归尝试解析:如果内容是字符串,尝试解析为 JSON
    displayContent = tryParseJSON(content);

    // 隐藏 system role 的 content
    displayContent = maskSystemContent(displayContent);

    // 判断是否为对象/数组(可以用 ReactJson 展示)
    const isJsonObject = typeof displayContent === 'object' && displayContent !== null;

    return (
        <div style={{ marginBottom: '16px' }}>
            <Tag color={color} style={{ marginBottom: '8px', fontSize: '14px', padding: '4px 10px' }}>
                {title}
            </Tag>
            <div style={{
                backgroundColor: '#f5f5f5',
                padding: '12px',
                borderRadius: '6px',
                border: '1px solid #e8e8e8',
                maxHeight: '60vh',
                overflow: 'auto'
            }}>
                {isJsonObject ? (
                    <ReactJson
                        src={displayContent}
                        theme="rjv-default"
                        collapsed={false}
                        displayDataTypes={false}
                        enableClipboard={true}
                        name={false}
                        style={{ fontSize: '13px', fontFamily: 'Menlo, Monaco, "Courier New", monospace' }}
                    />
                ) : (
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'Menlo, Monaco, "Courier New", monospace', fontSize: '13px' }}>
                        {String(displayContent)}
                    </pre>
                )}
            </div>
        </div>
    );
};

// === 解析逻辑辅助函数 ===

// 寻找 user role 的 content
const findUserContent = (input) => {
    if (!input) return '';

    // 如果 input 是字符串，先尝试解析
    let actualInput = input;
    if (typeof input === 'string') {
        actualInput = tryParseJSON(input);
    }

    // 如果解析后是数组 (messages list)
    if (Array.isArray(actualInput)) {
        const userMsg = actualInput.find(msg => msg.role === 'user');
        return userMsg ? userMsg.content : '';
    }
    // 如果解析后是对象且有 messages 字段
    if (typeof actualInput === 'object' && actualInput !== null && Array.isArray(actualInput.messages)) {
        const userMsg = actualInput.messages.find(msg => msg.role === 'user');
        return userMsg ? userMsg.content : '';
    }

    return '';
};

// 解析 Stn LLM Input
const parseStnInput = (content) => {
    let text = typeof content === 'string' ? content : JSON.stringify(content);
    if (!text) return { storyboard: '', cachePool: '' };

    const sbMarker = 'sb:';
    const cpMarker = 'cp:';
    const sbIndex = text.indexOf(sbMarker);
    const cpIndex = text.indexOf(cpMarker);

    let storyboard = '';
    let cachePool = '';

    if (sbIndex !== -1 && cpIndex !== -1 && cpIndex > sbIndex) {
        storyboard = text.substring(sbIndex + sbMarker.length, cpIndex).trim();
        cachePool = text.substring(cpIndex + cpMarker.length).trim();
    } else {
        // 兜底：如果找不到标记，还是尽量展示
        storyboard = text;
    }

    // 处理 Cache Pool 中的 U: 和 I: 换行
    if (cachePool) {
        // 使用正则全局替换，确保每次出现都换行
        cachePool = cachePool.replace(/([UI]:)/g, '\n$1').trim();
    }

    return { storyboard, cachePool };
};

// 解析 Niannian Input
const parseIntvInput = (content) => {
    let text = typeof content === 'string' ? content : JSON.stringify(content);
    if (!text) return { originalText: '', hintContent: '' };

    const otMarker = 'ot:';
    const hcMarker = 'hc:';

    // 注意：顺序因 prompt 而异，通常是 ot 在前 hc 在后，但也可能反过来，或者混合
    const otIndex = text.indexOf(otMarker);
    const hcIndex = text.indexOf(hcMarker);

    let originalText = '';
    let hintContent = '';

    if (otIndex !== -1 && hcIndex !== -1) {
        if (otIndex < hcIndex) {
            originalText = text.substring(otIndex + otMarker.length, hcIndex).trim();
            // 去除末尾可能存在的分号
            if (originalText.endsWith(';')) {
                originalText = originalText.slice(0, -1).trim();
            }
            hintContent = text.substring(hcIndex + hcMarker.length).trim();
        } else {
            hintContent = text.substring(hcIndex + hcMarker.length, otIndex).trim();
            // 去除末尾可能存在的分号(虽然通常 hc 在后不会有这个，但保持健壮性)
            if (hintContent.endsWith(';')) {
                hintContent = hintContent.slice(0, -1).trim();
            }
            originalText = text.substring(otIndex + otMarker.length).trim();
        }
    } else {
        originalText = text;
    }

    return { originalText, hintContent };
};

// 解析 Stn Output 表格数据
const parseStnOutputTable = (memoryContent) => {
    if (!memoryContent || typeof memoryContent !== 'object') return [];

    const rows = [];
    const types = ['S', 'T', 'O', 'C'];

    types.forEach(typeKey => {
        const items = memoryContent[typeKey];
        if (!items) return;

        const itemList = Array.isArray(items) ? items : [items];

        itemList.forEach(item => {
            if (!item) return;

            // 映射字段
            const typeMap = { 'S': 'stage', 'T': 'topic', 'O': 'shot', 'C': 'character' };
            const ptMap = { 'n': '新增', 'u': '更新', 'k': '保持' };

            rows.push({
                key: `${typeKey}-${item.id || item.tid || Math.random()}`,
                memType: typeMap[typeKey] || typeKey,
                procType: ptMap[item.pt] || item.pt || '-',
                id: item.id || item.tid || '-',
                title: typeKey === 'C' ? `${item.name}, ${item.relation}` : item.title || '-',
                summary: typeKey === 'C' ? item.evaluation : item.summary || '-',
                original: typeKey === 'C' ? '-' : item.content || '-',
            });
        });
    });

    return rows;
};


// === 新增解析面板组件 ===
const AnalysisPanel = ({ input, output, type }) => {
    const headerStyle = { fontSize: '16px', fontWeight: 'bold', marginTop: '16px', marginBottom: '8px', color: '#333' };
    const subHeaderStyle = { fontSize: '14px', fontWeight: 'bold', marginTop: '12px', marginBottom: '4px', color: '#666' };
    const contentStyle = {
        whiteSpace: 'pre-wrap',
        fontFamily: 'Menlo, Monaco, monospace',
        backgroundColor: '#f9f9f9',
        padding: '12px',
        borderRadius: '6px',
        border: '1px solid #eee',
        fontSize: '13px'
    };

    // 1. Dir LLM
    if (type === 'dir_llm') {
        const userContent = findUserContent(input);
        return (
            <div style={{ overflow: 'auto', maxHeight: '70vh', padding: '0 8px' }}>
                <div style={headerStyle}>Input</div>
                <div style={contentStyle}>
                    {userContent || '(Empty)'}
                </div>

                <div style={headerStyle}>Output</div>
                <div style={contentStyle}>
                    {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
                </div>
            </div>
        );
    }

    // 2. Stn LLM
    if (type === 'stn_llm') {
        const userContent = findUserContent(input);
        const { storyboard, cachePool } = parseStnInput(userContent);

        let memoryContent = null;
        if (output && typeof output === 'object') {
            memoryContent = output.memory_content;
        } else if (typeof output === 'string') {
            const parsed = tryParseJSON(output);
            if (parsed && typeof parsed === 'object') {
                memoryContent = parsed.memory_content;
            }
        }

        const tableData = parseStnOutputTable(memoryContent);

        const stnColumns = [
            { title: '回忆类型', dataIndex: 'memType', width: 80 },
            { title: '处理类型', dataIndex: 'procType', width: 80 },
            { title: 'ID', dataIndex: 'id', width: 100, ellipsis: true },
            { title: '标题', dataIndex: 'title', width: 150 },
            { title: '总结', dataIndex: 'summary', width: 200, ellipsis: true },
            { title: '原文 (整理后)', dataIndex: 'original', width: 250, ellipsis: true },
        ];

        return (
            <div style={{ overflow: 'auto', maxHeight: '70vh', padding: '0 8px' }}>
                <div style={headerStyle}>Input</div>

                <div style={subHeaderStyle}>Storyboard</div>
                <div style={contentStyle}>
                    {storyboard || '(Empty)'}
                </div>

                <div style={subHeaderStyle}>Cache Pool</div>
                <div style={contentStyle}>
                    {cachePool || '(Empty)'}
                </div>

                <div style={headerStyle}>Output</div>
                {memoryContent ? (
                    <Table
                        dataSource={tableData}
                        columns={stnColumns}
                        pagination={false}
                        size="small"
                        bordered
                        scroll={{ x: 1000 }}
                    />
                ) : (
                    <div style={contentStyle}>
                        {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
                    </div>
                )}
            </div>
        );
    }

    // 3. Niannian (intv_output)
    if (type === 'intv_output') {
        const userContent = findUserContent(input);
        const { originalText, hintContent } = parseIntvInput(userContent);

        return (
            <div style={{ overflow: 'auto', maxHeight: '70vh', padding: '0 8px' }}>
                <div style={headerStyle}>Input</div>

                <div style={subHeaderStyle}>Original Text</div>
                <div style={contentStyle}>
                    {originalText || '(Empty)'}
                </div>

                <div style={subHeaderStyle}>Hint Content</div>
                <div style={contentStyle}>
                    {hintContent || '(Empty)'}
                </div>

                <div style={headerStyle}>Output</div>
                <div style={contentStyle}>
                    {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
                </div>
            </div>
        );
    }

    // 4. Fallback (User or others) -> Show Original like view
    return (
        <div>
            <ContentSection title="All Content" content={{ input, output }} color="default" />
        </div>
    );
};

export default function InterviewDetail() {
    const { userId } = useParams();
    const navigate = useNavigate();

    // 状态管理
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState([]);
    const [userName, setUserName] = useState('');
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(50);

    // 默认选中所有
    const [selectedTypes, setSelectedTypes] = useState(['user', 'intv_output', 'stn_llm', 'dir_llm', 'feedback']);
    const [timeRange, setTimeRange] = useState([
        dayjs().startOf('day'),
        dayjs().endOf('day')
    ]);

    // 弹窗状态
    const [modalVisible, setModalVisible] = useState(false);
    const [modalContent, setModalContent] = useState(null);
    const [modalDataType, setModalDataType] = useState(null);

    // Debug 日志状态
    const [debugLogsVisible, setDebugLogsVisible] = useState(false);
    const [debugLogsData, setDebugLogsData] = useState(null);
    const [debugLogsLoading, setDebugLogsLoading] = useState(false);

    // 缓存池状态
    const [cachePoolInfo, setCachePoolInfo] = useState({ content: '', length: 0 });
    const [cachePoolModalVisible, setCachePoolModalVisible] = useState(false);
    // 额外信息状态
    const [extraInfo, setExtraInfo] = useState({ intv: {}, director: {} });

    const [activeIntvPrompt, setActiveIntvPrompt] = useState('');
    const [activeDirPrompt, setActiveDirPrompt] = useState('');

    // 导出状态
    // 导出状态
    const [exportModalVisible, setExportModalVisible] = useState(false);
    const [exportFeelings, setExportFeelings] = useState('');
    const [exportIncludeDialogue, setExportIncludeDialogue] = useState(true);
    const [exportIncludeFeelings, setExportIncludeFeelings] = useState(false);
    const [exportIncludePrompt, setExportIncludePrompt] = useState(false);
    const [exportIncludeDirPrompt, setExportIncludeDirPrompt] = useState(false);
    const [exportIncludeDirLLM, setExportIncludeDirLLM] = useState(false);

    // 音频播放状态
    const [playingAudio, setPlayingAudio] = useState(null); // 存储当前播放的 Audio 对象
    const [playingRecordId, setPlayingRecordId] = useState(null); // 存储当前播放的记录ID

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
                if (result.data.user_name) {
                    setUserName(result.data.user_name);
                }
                if (result.data.cache_pool_info) {
                    setCachePoolInfo(result.data.cache_pool_info);
                }
                setExtraInfo({
                    intv: result.data.intv_info,
                    director: result.data.director_info
                });
                if (result.data.active_intv_prompt) {
                    setActiveIntvPrompt(result.data.active_intv_prompt);
                }
                if (result.data.active_dir_prompt) {
                    setActiveDirPrompt(result.data.active_dir_prompt);
                }

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
    const handleViewDetail = (content, dataType) => {
        setModalContent(content);
        setModalDataType(dataType);
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

    // 导出记录
    const handleExport = () => {
        // 1. 筛选数据: 仅保留"用户"和"念念"
        const exportData = data.filter(item => {
            if (item.data_type === 'user' || item.data_type === 'intv_output') {
                return true;
            }
            if (item.data_type === 'dir_llm' && exportIncludeDirLLM) {
                return true;
            }
            return false;
        });

        // 2. 按时间升序排列
        exportData.sort((a, b) => new Date(a.created_time) - new Date(b.created_time));

        // 3. 拼接 Markdown 内容
        let mdContent = '';

        if (exportIncludeDialogue) {
            mdContent += `采访对话内容\n\n`; // 去掉标题前的 # 和编号

            exportData.forEach(item => {
                const role = item.data_type === 'intv_output' ? 'Intv LLM' : userName;
                let contentText = '';

                if (item.data_type === 'user') {
                    contentText = item.full_content && typeof item.full_content === 'string'
                        ? item.full_content
                        : (item.content || item.content_preview);
                } else if (item.data_type === 'dir_llm') {
                    contentText = item.content || item.content_preview;
                } else {
                    contentText = item.content || item.content_preview;
                }

                // 处理一下换行符
                let roleDisplay = role;
                if (item.data_type === 'dir_llm') {
                    roleDisplay = 'Dir LLM';
                }
                mdContent += `${roleDisplay}：${contentText}\n\n`; // 双换行分隔气泡
            });
        }

        if (exportIncludeFeelings) {
            if (mdContent) mdContent += `\n---\n\n`;
            mdContent += `我的本次采访的感受\n\n${exportFeelings}\n\n`; // 去掉标题前的 # 和编号
        }

        if (exportIncludePrompt) {
            if (mdContent) mdContent += `\n---\n\n`;
            mdContent += `Intv LLM 提示词\n\n${activeIntvPrompt || '（未找到激活的提示词）'}`;
        }

        if (exportIncludeDirPrompt) {
            if (mdContent) mdContent += `\n---\n\n`;
            mdContent += `Dir LLM 提示词\n\n${activeDirPrompt || '（未找到激活的提示词）'}`;
        }

        // 4. 触发下载
        const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `${userName}_采访记录_${dayjs().format('YYYYMMDD')}.md`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // 5. 关闭弹窗并清空 (保留选项状态以便下次继续使用，或者重置也可以，这里仅清空感受内容)
        setExportModalVisible(false);
        setExportFeelings('');
        message.success('导出成功');
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
                return <Text style={{ color }}>{record.time}</Text>;
            }
        },
        {
            title: '音频',
            dataIndex: 'audio_url',
            key: 'audio_url',
            width: 60,
            render: (url, record) => {
                if (!record.has_audio || !url) {
                    return <Text type="secondary" style={{ color: '#373737' }}>-</Text>;
                }

                // 尝试解析 url 是否为数组 (多段录音)
                let urls = [];
                try {
                    const parsed = JSON.parse(url);
                    if (Array.isArray(parsed)) urls = parsed;
                    else urls = [url];
                } catch (e) {
                    urls = [url];
                }

                const handlePlay = (audioUrl, uniqueId) => {
                    if (playingRecordId === uniqueId) {
                        // 停止播放
                        if (playingAudio) {
                            playingAudio.pause();
                            playingAudio.currentTime = 0;
                        }
                        setPlayingAudio(null);
                        setPlayingRecordId(null);
                    } else {
                        // 停止之前的音频
                        if (playingAudio) {
                            playingAudio.pause();
                            playingAudio.currentTime = 0;
                        }

                        // 播放新音频
                        const audio = new Audio(audioUrl);
                        audio.play().catch(e => {
                            message.error('播放失败: ' + e.message);
                            setPlayingAudio(null);
                            setPlayingRecordId(null);
                        });

                        // 监听播放结束事件
                        audio.onended = () => {
                            setPlayingAudio(null);
                            setPlayingRecordId(null);
                        };

                        setPlayingAudio(audio);
                        setPlayingRecordId(uniqueId);
                    }
                };

                // 多段录音：显示 Popover
                if (urls.length > 1) {
                    const content = (
                        <div style={{ display: 'flex', gap: '8px' }}>
                            {urls.map((audioUrl, index) => {
                                const uniqueId = `${record.record_id}_${index}`;
                                const isPlaying = playingRecordId === uniqueId;
                                return (
                                    <Button
                                        key={index}
                                        type={isPlaying ? 'primary' : 'default'}
                                        danger={isPlaying}
                                        size="small"
                                        onClick={() => handlePlay(audioUrl, uniqueId)}
                                    >
                                        {isPlaying ? '停止' : `录音${index + 1}`}
                                    </Button>
                                );
                            })}
                        </div>
                    );

                    const isAnyPlaying = urls.some((_, index) => playingRecordId === `${record.record_id}_${index}`);

                    return (
                        <Popover content={content} title="选择录音播放" trigger="click" placement="right">
                            <Button type="link" size="small" style={{ padding: 0 }}>
                                {isAnyPlaying ? '播放中...' : `播放 (${urls.length})`}
                            </Button>
                        </Popover>
                    );
                }

                // 单段录音：直接显示播放按钮
                const uniqueId = record.record_id;
                const isPlaying = playingRecordId === uniqueId;

                return (
                    <Button
                        type="link"
                        size="small"
                        style={{
                            color: isPlaying ? '#ff4d4f' : '#1890FF',
                            padding: 0
                        }}
                        onClick={() => handlePlay(urls[0], uniqueId)}
                    >
                        {isPlaying ? '停止' : '播放'}
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
                const contentColor = record.data_type === 'dir_llm' ? '#FF5200' : config?.color || '#373737';

                // 用户：直接展全部内容
                if (record.data_type === 'user') {
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

                // 反馈
                if (record.data_type === 'feedback') {
                    return (
                        <div style={{ color: '#6126FF' }}>
                            {record.content}
                        </div>
                    );
                }

                // Stn LLM: 格式化展示为 {回忆类型} {处理类型}：{标题}
                if (record.data_type === 'stn_llm') {
                    let displayStn = record.content_preview || record.content;

                    try {
                        let memoryContent = null;

                        // 尝试从 full_content 中深度解析
                        const parsedFull = tryParseJSON(record.full_content);
                        if (parsedFull && parsedFull.output) {
                            const parsedOutput = tryParseJSON(parsedFull.output);
                            if (parsedOutput && parsedOutput.memory_content) {
                                memoryContent = parsedOutput.memory_content;
                            }
                        }

                        // 如果没找到，尝试直接解析 content (虽然 content 通常是 string)
                        if (!memoryContent) {
                            const parsedContent = tryParseJSON(record.content);
                            if (parsedContent && parsedContent.memory_content) {
                                memoryContent = parsedContent.memory_content;
                            }
                        }

                        if (memoryContent) {
                            const items = parseStnOutputTable(memoryContent);
                            if (items && items.length > 0) {
                                displayStn = items.map(item => `${item.memType} ${item.procType}：${item.title}`).join('; ');
                            }
                        }
                    } catch (e) {
                        console.error("Stn content parse error:", e);
                    }

                    return (
                        <div
                            style={{
                                color: contentColor,
                                cursor: 'pointer', // 增加手型暗示可点击
                                textDecoration: 'underline dotted', // 加个虚线下划线提示
                                textUnderlineOffset: '4px'
                            }}
                            onClick={() => handleViewDetail(record.full_content, record.data_type)}
                        >
                            {displayStn}
                        </div>
                    );
                }

                // 其他类型（念念、Dir LLM）：点击内容区域弹出详情
                const displayText = record.content_preview || record.content;
                return (
                    <div
                        style={{
                            color: contentColor,
                            cursor: 'pointer', // 增加手型暗示可点击
                            textDecoration: 'underline dotted', // 加个虚线下划线提示
                            textUnderlineOffset: '4px'
                        }}
                        onClick={() => handleViewDetail(record.full_content, record.data_type)}
                    >
                        {displayText}
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
            <Card style={{ marginBottom: '8px', position: 'relative' }}>
                {/* 查看日志按钮 - 绝对定位在右上角 */}
                <Button
                    type="primary"
                    icon={<FileTextOutlined />}
                    onClick={fetchDebugLogs}
                    style={{ position: 'absolute', top: '24px', right: '24px' }}
                >
                    查看日志
                </Button>

                {/* 导出记录按钮 - 在查看日志左边 */}
                <Button
                    icon={<DownloadOutlined />}
                    onClick={() => setExportModalVisible(true)}
                    style={{ position: 'absolute', top: '24px', right: '150px' }}
                >
                    导出记录
                </Button>

                {/* 标题和信息垂直排列 */}
                <div>
                    <Title level={4} style={{ margin: 0, marginBottom: '12px' }}>
                        用户采访详情 - {userName || userId}
                    </Title>

                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {/* 缓存池信息 - 纯文字,左对齐,点击查看 */}
                        <div
                            style={{ fontSize: '13px', color: '#1890ff', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                            onClick={() => setCachePoolModalVisible(true)}
                        >
                            <span style={{ textDecoration: 'underline' }}>
                                当前缓存池字数: {cachePoolInfo?.length || 0}
                            </span>
                        </div>

                        {/* Intv Session 信息 */}
                        <div style={{ fontSize: '13px', color: '#595959' }}>
                            Intv session：{extraInfo?.intv?.session_id || '-'}，字数：{extraInfo?.intv?.word_count || 0}
                        </div>

                        {/* 最新导演提示 */}
                        <div style={{ fontSize: '13px', color: '#fa8c16' }}>
                            最新导演提示：{extraInfo?.director?.latest_hint || '无'} <span style={{ color: '#8c8c8c', marginLeft: '8px' }}>{extraInfo?.director?.time_str}</span>
                        </div>

                    </Space>
                </div>
            </Card>



            {/* 数据表格 */}
            <Card>
                {/* 筛选器 - 移动到表格卡片顶部 */}
                <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <Text strong style={{ marginRight: '8px' }}>数据方类型：</Text>
                        <Checkbox.Group
                            options={dataTypeOptions}
                            value={selectedTypes}
                            onChange={(values) => {
                                setSelectedTypes(values);
                                setPage(1);
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <Text strong style={{ marginRight: '8px' }}>时间范围：</Text>
                        <RangePicker
                            showTime
                            format="YYYY-MM-DD HH:mm:ss"
                            value={timeRange}
                            onChange={(dates) => {
                                setTimeRange(dates);
                                setPage(1);
                            }}
                            variant="borderless"
                            style={{ padding: 0 }}
                        />
                    </div>
                </div>
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
                destroyOnClose={true} // 确保每次打开都重置状态，保证 activeKey 正确
                footer={[
                    <Button key="copy" onClick={() => handleCopy(modalContent)}>
                        复制全部
                    </Button>,
                    <Button key="close" type="primary" onClick={() => setModalVisible(false)}>
                        关闭
                    </Button>
                ]}
                width={1690}
                centered
                styles={{ body: { height: '80vh', overflowY: 'auto' } }}
            >
                {(() => {
                    let input = null;
                    let output = null;

                    // 确保先解析为对象
                    const parsedContent = tryParseJSON(modalContent);

                    if (parsedContent && typeof parsedContent === 'object') {
                        if ('input' in parsedContent) input = parsedContent.input;
                        if ('output' in parsedContent) output = parsedContent.output;
                    }

                    const hasAnalysis = ['dir_llm', 'stn_llm', 'intv_output'].includes(modalDataType);

                    const items = [];

                    if (hasAnalysis) {
                        items.push({
                            key: 'analysis',
                            label: <span style={{ fontWeight: 'bold' }}>解析</span>,
                            children: <AnalysisPanel input={input} output={output} type={modalDataType} />,
                        });
                    }

                    items.push({
                        key: 'original',
                        label: <span style={{ fontWeight: 'bold' }}>原文</span>,
                        children: (
                            <div>
                                {input && <ContentSection title="📥 Input (输入)" content={input} color="blue" />}
                                {output && <ContentSection title="📤 Output (输出)" content={output} color="green" />}
                                {!input && !output && <ContentSection title="详细内容" content={modalContent} color="default" />}
                            </div>
                        ),
                    });

                    // 使用 key 强制重新渲染 Tabs，或者依赖 destroyOnClose
                    return <Tabs defaultActiveKey={hasAnalysis ? 'analysis' : 'original'} items={items} />;
                })()}
            </Modal>

            {/* 缓存池内容详情弹窗 */}
            <Modal
                title={`Chat Cache Pool (当前字数: ${cachePoolInfo?.length || 0})`}
                open={cachePoolModalVisible}
                onCancel={() => setCachePoolModalVisible(false)}
                footer={[
                    <Button key="close" type="primary" onClick={() => setCachePoolModalVisible(false)}>
                        关闭
                    </Button>
                ]}
                width={1000}
                style={{ top: '5vh' }}
                styles={{ body: { height: '85vh', overflowY: 'auto' } }}
            >
                <div style={{
                    backgroundColor: '#f5f5f5',
                    padding: '16px',
                    borderRadius: '6px',
                    border: '1px solid #e8e8e8',
                    minHeight: '100%',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                    fontSize: '13px'
                }}>
                    {cachePoolInfo?.content || "（空）"}
                </div>
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
        .data-type-stn_llm { color: #13c2c2; }
        .data-type-dir_llm { color: #f5222d; }
      `}</style>

            {/* 导出记录弹窗 */}
            <Modal
                title="导出采访记录"
                open={exportModalVisible}
                onOk={handleExport}
                onCancel={() => setExportModalVisible(false)}
                okText="确认导出"
                cancelText="取消"
                width={600}
            >
                <div style={{ marginBottom: '16px' }}>
                    <Text strong>本次采访的感受：</Text>
                    <div style={{ marginBottom: '16px' }}>
                        <div style={{ marginBottom: '16px' }}>
                            <Checkbox checked={exportIncludeDialogue} disabled>对话原文</Checkbox>
                            <Checkbox
                                checked={exportIncludeFeelings}
                                onChange={(e) => setExportIncludeFeelings(e.target.checked)}
                            >
                                采访感受
                            </Checkbox>
                            <Checkbox
                                checked={exportIncludePrompt}
                                onChange={(e) => setExportIncludePrompt(e.target.checked)}
                            >
                                Intv LLM 提示词
                            </Checkbox>
                            <Checkbox
                                checked={exportIncludeDirPrompt}
                                onChange={(e) => setExportIncludeDirPrompt(e.target.checked)}
                            >
                                Dir LLM 提示词
                            </Checkbox>
                            <Checkbox
                                checked={exportIncludeDirLLM}
                                onChange={(e) => setExportIncludeDirLLM(e.target.checked)}
                            >
                                Dir LLM
                            </Checkbox>
                        </div>

                        <div style={{ marginTop: '8px' }}>
                            <textarea
                                style={{
                                    width: '100%',
                                    minHeight: '150px',
                                    padding: '8px',
                                    borderRadius: '4px',
                                    border: '1px solid #d9d9d9',
                                    resize: 'vertical',
                                    backgroundColor: exportIncludeFeelings ? 'white' : '#f5f5f5',
                                    cursor: exportIncludeFeelings ? 'text' : 'not-allowed'
                                }}
                                placeholder={exportIncludeFeelings ? "请输入您对本次采访的感受..." : "请先勾选“采访感受”"}
                                value={exportFeelings}
                                onChange={(e) => setExportFeelings(e.target.value)}
                                disabled={!exportIncludeFeelings}
                            />
                        </div>
                    </div>
                </div>
                <div style={{ color: '#888', fontSize: '12px' }}>
                    * 导出内容包含：当前激活的 Prompt、按时间排序的对话记录以及您填写的感受。
                </div>
            </Modal>
        </div>
    );
}
