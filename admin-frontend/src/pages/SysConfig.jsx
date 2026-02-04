import React, { useState, useEffect } from 'react';
import { Card, Table, Input, InputNumber, Select, Button, message, Typography, Space } from 'antd';
import { EditOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons';
import { getSysConfigs, updateSysConfig } from '../services/api';

const { Title } = Typography;

export default function SysConfig() {
    const [configs, setConfigs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editingKey, setEditingKey] = useState('');
    const [editingValue, setEditingValue] = useState('');

    useEffect(() => {
        loadConfigs();
    }, []);

    const loadConfigs = async () => {
        setLoading(true);
        try {
            const data = await getSysConfigs();
            setConfigs(data.data || []);
        } catch (error) {
            message.error('加载配置失败: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (record) => {
        setEditingKey(record.config_key);
        setEditingValue(record.config_value);
    };

    const handleSave = async (configKey) => {
        try {
            await updateSysConfig(configKey, editingValue);
            message.success('保存成功');
            setEditingKey('');
            loadConfigs();
        } catch (error) {
            message.error('保存失败: ' + error.message);
        }
    };

    const handleCancel = () => {
        setEditingKey('');
        setEditingValue('');
    };

    const renderValueEditor = (record) => {
        if (editingKey !== record.config_key) {
            return record.config_value;
        }

        switch (record.config_type) {
            case 'number':
                return (
                    <InputNumber
                        value={editingValue}
                        onChange={setEditingValue}
                        style={{ width: '100%' }}
                    />
                );
            case 'select':
                // 这里可以根据 remark 解析选项
                return (
                    <Input
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                    />
                );
            case 'text':
            default:
                return (
                    <Input
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                    />
                );
        }
    };

    const columns = [
        {
            title: '配置键',
            dataIndex: 'config_key',
            key: 'config_key',
            width: 200,
        },
        {
            title: '配置名称',
            dataIndex: 'config_name',
            key: 'config_name',
            width: 200,
        },
        {
            title: '配置值',
            dataIndex: 'config_value',
            key: 'config_value',
            width: 300,
            render: (_, record) => renderValueEditor(record),
        },
        {
            title: '类型',
            dataIndex: 'config_type',
            key: 'config_type',
            width: 100,
        },
        {
            title: '备注',
            dataIndex: 'remark',
            key: 'remark',
            ellipsis: true,
        },
        {
            title: '操作',
            key: 'action',
            width: 150,
            render: (_, record) => {
                const isEditing = editingKey === record.config_key;
                return isEditing ? (
                    <Space>
                        <Button
                            type="primary"
                            size="small"
                            icon={<SaveOutlined />}
                            onClick={() => handleSave(record.config_key)}
                        >
                            保存
                        </Button>
                        <Button
                            size="small"
                            icon={<CloseOutlined />}
                            onClick={handleCancel}
                        >
                            取消
                        </Button>
                    </Space>
                ) : (
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                        disabled={editingKey !== ''}
                    >
                        编辑
                    </Button>
                );
            },
        },
    ];

    return (
        <div>
            <Title level={2}>系统配置</Title>
            <Card>
                <Table
                    columns={columns}
                    dataSource={configs}
                    loading={loading}
                    rowKey="config_key"
                    pagination={false}
                />
            </Card>
        </div>
    );
}
