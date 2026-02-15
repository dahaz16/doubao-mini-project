import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Switch, message, Typography, Space, Tag, Tabs, Checkbox } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { getPrompts, createPrompt, togglePromptActive } from '../services/api';

const { Title } = Typography;

const LLM_TYPES = {
    0: 'Intv（访谈员）',
    1: 'Stn（速记员）',
    2: 'Dir（导演）',
    3: 'Wtr（写作员）',
};

const LLM_TAB_ITEMS = [
    { key: '0', label: 'Intv LLM' },
    { key: '1', label: 'Stn LLM' },
    { key: '2', label: 'Dir LLM' },
    { key: '3', label: 'Wtr LLM' },
];

export default function PromptConfig() {
    const [prompts, setPrompts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [currentTab, setCurrentTab] = useState('0'); // 默认 Intv LLM
    const [showAllVersions, setShowAllVersions] = useState(false); // 默认只显示激活的
    const [form] = Form.useForm();

    useEffect(() => {
        loadPrompts();
    }, [currentTab, showAllVersions]); // Tab 切换或筛选条件变化时重新加载

    const loadPrompts = async () => {
        setLoading(true);
        try {
            const params = {
                llm_type: parseInt(currentTab),
                show_all_versions: showAllVersions,
            };
            const data = await getPrompts(params);
            setPrompts(data.data || []);
        } catch (error) {
            message.error('加载提示词失败: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        form.resetFields();
        // 设置默认 LLM 类型为当前 Tab
        form.setFieldsValue({ llm_type: parseInt(currentTab) });
        setModalVisible(true);
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            await createPrompt(values);
            message.success('创建成功');
            setModalVisible(false);
            loadPrompts();
        } catch (error) {
            message.error('创建失败: ' + error.message);
        }
    };

    const handleToggle = async (promptId) => {
        try {
            await togglePromptActive(promptId);
            message.success('切换成功');
            loadPrompts();
        } catch (error) {
            message.error('切换失败: ' + error.message);
        }
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'prompt_id',
            key: 'prompt_id',
            width: 60,
        },
        {
            title: '提示词内容',
            dataIndex: 'prompt_content',
            key: 'prompt_content',
            render: (text) => (
                <pre style={{
                    margin: 0,
                    whiteSpace: 'pre-wrap',
                    fontSize: 12,
                    fontFamily: 'monospace',
                    lineHeight: 1.5,
                }}>
                    {text}
                </pre>
            ),
        },
        {
            title: '备注',
            dataIndex: 'remark',
            key: 'remark',
            width: 200,
            ellipsis: true,
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 100,
            render: (isActive, record) => (
                <Switch
                    checked={isActive}
                    onChange={() => handleToggle(record.prompt_id)}
                    checkedChildren="激活"
                    unCheckedChildren="停用"
                />
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_time',
            key: 'created_time',
            width: 180,
            render: (time) => time ? new Date(time).toLocaleString('zh-CN') : '-',
        },
    ];

    return (
        <div>
            <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
                <Title level={2} style={{ margin: 0 }}>提示词配置</Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    新增提示词
                </Button>
            </Space>

            <Card>
                <Tabs
                    activeKey={currentTab}
                    onChange={setCurrentTab}
                    items={LLM_TAB_ITEMS}
                    style={{ marginBottom: 16 }}
                />

                <Space style={{ marginBottom: 16 }}>
                    <Checkbox
                        checked={showAllVersions}
                        onChange={(e) => setShowAllVersions(e.target.checked)}
                    >
                        显示全部版本提示词
                    </Checkbox>
                </Space>

                <Table
                    columns={columns}
                    dataSource={prompts}
                    loading={loading}
                    rowKey="prompt_id"
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title="新增提示词"
                open={modalVisible}
                onOk={handleSubmit}
                onCancel={() => setModalVisible(false)}
                width={800}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        label="LLM 类型"
                        name="llm_type"
                        rules={[{ required: true, message: '请选择 LLM 类型' }]}
                    >
                        <Select>
                            <Select.Option value={0}>Intv（访谈员）</Select.Option>
                            <Select.Option value={1}>Stn（速记员）</Select.Option>
                            <Select.Option value={2}>Dir（导演）</Select.Option>
                            <Select.Option value={3}>Wtr（写作员）</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item
                        label="提示词内容"
                        name="prompt_content"
                        rules={[{ required: true, message: '请输入提示词内容' }]}
                    >
                        <Input.TextArea rows={12} placeholder="输入系统提示词..." />
                    </Form.Item>
                    <Form.Item label="备注" name="remark">
                        <Input placeholder="例如：修复了 JSON 解析报错" />
                    </Form.Item>
                    <Form.Item
                        label="立即激活"
                        name="is_active"
                        valuePropName="checked"
                        initialValue={true}
                    >
                        <Switch checkedChildren="是" unCheckedChildren="否" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
