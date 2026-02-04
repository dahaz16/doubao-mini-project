import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, InputNumber, Select, message, Typography, Space, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { getModels, createModel, updateModel, deleteModel } from '../services/api';

const { Title } = Typography;

export default function ModelConfig() {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingModel, setEditingModel] = useState(null);
    const [form] = Form.useForm();

    useEffect(() => {
        loadModels();
    }, []);

    const loadModels = async () => {
        setLoading(true);
        try {
            const data = await getModels();
            setModels(data.data || []);
        } catch (error) {
            message.error('加载模型列表失败: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingModel(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingModel(record);
        form.setFieldsValue(record);
        setModalVisible(true);
    };

    const handleDelete = async (modelId) => {
        try {
            await deleteModel(modelId);
            message.success('删除成功');
            loadModels();
        } catch (error) {
            message.error('删除失败: ' + error.message);
        }
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();

            if (editingModel) {
                await updateModel(editingModel.model_id, values);
                message.success('更新成功');
            } else {
                await createModel(values);
                message.success('创建成功');
            }

            setModalVisible(false);
            loadModels();
        } catch (error) {
            message.error('操作失败: ' + error.message);
        }
    };

    const columns = [
        {
            title: 'ID',
            dataIndex: 'model_id',
            key: 'model_id',
            width: 60,
        },
        {
            title: '中文名',
            dataIndex: 'model_name_cn',
            key: 'model_name_cn',
            width: 120,
        },
        {
            title: '英文名',
            dataIndex: 'model_name_en',
            key: 'model_name_en',
            width: 150,
        },
        {
            title: '类型',
            dataIndex: 'model_type',
            key: 'model_type',
            width: 80,
        },
        {
            title: 'API Model ID',
            dataIndex: 'api_model_id',
            key: 'api_model_id',
            ellipsis: true,
            width: 200,
        },
        {
            title: '输入价格',
            dataIndex: 'input_price',
            key: 'input_price',
            width: 100,
        },
        {
            title: '输出价格',
            dataIndex: 'output_price',
            key: 'output_price',
            width: 100,
        },
        {
            title: '缓存折扣',
            dataIndex: 'cache_discount',
            key: 'cache_discount',
            width: 100,
        },
        {
            title: '操作',
            key: 'action',
            width: 150,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        编辑
                    </Button>
                    <Popconfirm
                        title="确定要删除吗？"
                        onConfirm={() => handleDelete(record.model_id)}
                        okText="确定"
                        cancelText="取消"
                    >
                        <Button
                            type="link"
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                        >
                            删除
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
                <Title level={2} style={{ margin: 0 }}>模型库管理</Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    新增模型
                </Button>
            </Space>

            <Card>
                <Table
                    columns={columns}
                    dataSource={models}
                    loading={loading}
                    rowKey="model_id"
                    scroll={{ x: 'max-content' }}
                />
            </Card>

            <Modal
                title={editingModel ? '编辑模型' : '新增模型'}
                open={modalVisible}
                onOk={handleSubmit}
                onCancel={() => setModalVisible(false)}
                width={600}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        label="中文名"
                        name="model_name_cn"
                        rules={[{ required: true, message: '请输入中文名' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        label="英文名"
                        name="model_name_en"
                        rules={[{ required: true, message: '请输入英文名' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        label="模型类型"
                        name="model_type"
                        rules={[{ required: true, message: '请选择模型类型' }]}
                    >
                        <Select>
                            <Select.Option value="LLM">LLM</Select.Option>
                            <Select.Option value="ASR">ASR</Select.Option>
                            <Select.Option value="TTS">TTS</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item
                        label="API Model ID"
                        name="api_model_id"
                        rules={[{ required: true, message: '请输入 API Model ID' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item label="输入价格" name="input_price">
                        <InputNumber style={{ width: '100%' }} step={0.01} />
                    </Form.Item>
                    <Form.Item label="输出价格" name="output_price">
                        <InputNumber style={{ width: '100%' }} step={0.01} />
                    </Form.Item>
                    <Form.Item label="缓存折扣" name="cache_discount" initialValue={0.5}>
                        <InputNumber style={{ width: '100%' }} step={0.1} min={0} max={1} />
                    </Form.Item>
                    <Form.Item label="缓存存储价格" name="cache_storage_price">
                        <InputNumber style={{ width: '100%' }} step={0.01} />
                    </Form.Item>
                    <Form.Item label="集群 ID" name="cluster_id">
                        <Input />
                    </Form.Item>
                    <Form.Item label="备注" name="remark">
                        <Input.TextArea rows={2} />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
