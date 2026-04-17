import { ReloadOutlined, SendOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";

import { api } from "../api/client";
import type { APIStyle, EvalModelProbeResponse, EvalModelRead, EvalModelUpdate } from "../api/types";

interface ModelFormValues {
  model_name?: string;
  release_date?: string;
  api_url?: string;
  api_style?: APIStyle;
  api_model?: string;
  api_key?: string;
  is_active?: boolean;
  sort_order?: number;
}

type StatusFilter = "all" | "active" | "inactive";
type ConfigFilter = "all" | "configured" | "missing";
type ProbeStatus = "idle" | "running";

export function ModelsPage() {
  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();
  const [editingModel, setEditingModel] = useState<EvalModelRead | null>(null);
  const [probeResults, setProbeResults] = useState<Record<number, EvalModelProbeResponse>>({});
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [configFilter, setConfigFilter] = useState<ConfigFilter>("all");
  const [protocolFilter, setProtocolFilter] = useState<APIStyle | "all">("all");
  const [batchProbeState, setBatchProbeState] = useState<ProbeStatus>("idle");
  const [form] = Form.useForm<ModelFormValues>();

  const modelsQuery = useQuery({
    queryKey: ["models"],
    queryFn: api.listModels,
  });

  const updateMutation = useMutation({
    mutationFn: ({ modelId, payload }: { modelId: number; payload: EvalModelUpdate }) =>
      api.updateModel(modelId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["models"] });
      messageApi.success("模型配置已更新");
      setEditingModel(null);
    },
    onError: (error: Error) => {
      messageApi.error(error.message);
    },
  });

  const probeMutation = useMutation({
    mutationFn: (modelId: number) => api.probeModel(modelId),
    onSuccess: (data) => {
      setProbeResults((current) => ({
        ...current,
        [data.model_id]: data,
      }));
      messageApi.success(`Probe 完成: ${data.model_name}`);
    },
    onError: (error: Error) => {
      messageApi.error(error.message);
    },
  });

  const models = modelsQuery.data ?? [];
  const filteredModels = models.filter((model) => {
    const normalizedSearch = searchText.trim().toLowerCase();
    const matchesSearch =
      !normalizedSearch ||
      model.model_name.toLowerCase().includes(normalizedSearch) ||
      model.api_model.toLowerCase().includes(normalizedSearch) ||
      String(model.model_id).includes(normalizedSearch);
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "active" && model.is_active) ||
      (statusFilter === "inactive" && !model.is_active);
    const matchesConfig =
      configFilter === "all" ||
      (configFilter === "configured" && model.is_configured) ||
      (configFilter === "missing" && !model.is_configured);
    const matchesProtocol = protocolFilter === "all" || model.api_style === protocolFilter;

    return matchesSearch && matchesStatus && matchesConfig && matchesProtocol;
  });

  const activeCount = models.filter((model) => model.is_active).length;
  const configuredCount = models.filter((model) => model.is_configured).length;
  const responseCount = models.filter((model) => model.api_style === "responses").length;
  const missingConfigCount = models.filter((model) => !model.is_configured).length;
  const missingReleaseDateCount = models.filter((model) => !model.release_date).length;
  const filteredConfiguredCount = filteredModels.filter((model) => model.is_configured).length;
  const filteredActiveCount = filteredModels.filter((model) => model.is_active).length;
  const probeEntries = Object.values(probeResults);
  const latestProbe = probeEntries.at(-1) ?? null;
  const probeFailureCount = probeEntries.filter((item) => !item.ok).length;

  const runBatchProbe = async () => {
    const candidates = filteredModels.filter((model) => model.is_configured);
    if (candidates.length === 0) {
      messageApi.warning("当前筛选结果里没有可探活的已配置模型");
      return;
    }

    setBatchProbeState("running");
    for (const model of candidates) {
      try {
        const data = await api.probeModel(model.model_id);
        setProbeResults((current) => ({
          ...current,
          [data.model_id]: data,
        }));
      } catch (error) {
        const message = error instanceof Error ? error.message : "Probe 失败";
        setProbeResults((current) => ({
          ...current,
          [model.model_id]: {
            model_id: model.model_id,
            model_name: model.model_name,
            api_style: model.api_style,
            api_model: model.api_model,
            ok: false,
            latency_ms: 0,
            provider_error: message,
            response_text_preview: null,
          },
        }));
      }
    }
    setBatchProbeState("idle");
    messageApi.success(`已完成 ${candidates.length} 个模型的探活`);
  };

  const columns: ColumnsType<EvalModelRead> = [
    {
      title: "ID",
      dataIndex: "model_id",
      width: 72,
    },
    {
      title: "模型",
      key: "model",
      width: 260,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text>{record.model_name}</Typography.Text>
          <Typography.Text type="secondary">{record.api_model}</Typography.Text>
          <Typography.Text type="secondary">{record.release_date || "release_date 未填"}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "协议",
      dataIndex: "api_style",
      width: 112,
      render: (value: APIStyle) => (
        <Tag color={value === "responses" ? "processing" : "default"}>{value}</Tag>
      ),
    },
    {
      title: "状态",
      key: "flags",
      width: 176,
      render: (_, record) => (
        <Space wrap>
          <Tag color={record.is_active ? "success" : "error"}>
            {record.is_active ? "active" : "inactive"}
          </Tag>
          <Tag color={record.is_configured ? "blue" : "warning"}>
            {record.is_configured ? "configured" : "missing creds"}
          </Tag>
        </Space>
      ),
    },
    {
      title: "最近 Probe",
      key: "probe",
      width: 146,
      render: (_, record) => {
        const probeResult = probeResults[record.model_id];
        if (!probeResult) {
          return <Typography.Text type="secondary">未执行</Typography.Text>;
        }

        return (
          <Space wrap>
            <Tag color={probeResult.ok ? "success" : "error"}>
              {probeResult.ok ? "OK" : "FAILED"}
            </Tag>
            <Typography.Text>{probeResult.latency_ms} ms</Typography.Text>
          </Space>
        );
      },
    },
    {
      title: "操作",
      key: "actions",
      width: 206,
      render: (_, record) => (
        <Space wrap>
          <Button
            size="small"
            onClick={() => {
              setEditingModel(record);
              form.setFieldsValue({
                model_name: record.model_name,
                release_date: record.release_date ?? undefined,
                api_url: record.api_url,
                api_style: record.api_style,
                api_model: record.api_model,
                is_active: record.is_active,
                sort_order: record.sort_order,
              });
            }}
          >
            编辑
          </Button>
          <Button
            size="small"
            loading={probeMutation.isPending && probeMutation.variables === record.model_id}
            onClick={() => probeMutation.mutate(record.model_id)}
          >
            Probe
          </Button>
          <Button
            size="small"
            onClick={() =>
              updateMutation.mutate({
                modelId: record.model_id,
                payload: { is_active: !record.is_active },
              })
            }
            loading={updateMutation.isPending}
          >
            {record.is_active ? "停用" : "启用"}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ display: "flex" }}>
      {contextHolder}
      {modelsQuery.error instanceof Error ? (
        <Alert type="error" showIcon message={modelsQuery.error.message} />
      ) : null}

      <Card className="panel-card">
        <Space className="page-toolbar" wrap>
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              模型筛选与操作
            </Typography.Title>
            <Typography.Paragraph className="soft-note">
              支持搜索、筛选、快速启停和批量 Probe。
            </Typography.Paragraph>
          </div>
          <Space wrap className="toolbar-actions">
            <Tag color="blue">模型 {models.length}</Tag>
            <Tag color="success">已配置 {configuredCount}</Tag>
            <Tag color="processing">responses {responseCount}</Tag>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void modelsQuery.refetch()}
              loading={modelsQuery.isFetching}
            >
              刷新列表
            </Button>
            <Button
              icon={<SendOutlined />}
              onClick={() => void runBatchProbe()}
              loading={batchProbeState === "running"}
            >
              Probe 当前筛选结果
            </Button>
          </Space>
        </Space>
        <Row gutter={[16, 16]} className="filter-grid">
          <Col xs={24} xl={8}>
            <Input.Search
              placeholder="按模型 ID / 名称 / API Model 搜索"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={8} xl={4}>
            <Select<StatusFilter>
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: "全部状态" },
                { value: "active", label: "仅 active" },
                { value: "inactive", label: "仅 inactive" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={24} sm={8} xl={5}>
            <Select<ConfigFilter>
              value={configFilter}
              onChange={setConfigFilter}
              options={[
                { value: "all", label: "全部配置状态" },
                { value: "configured", label: "仅已配置" },
                { value: "missing", label: "仅缺凭据" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={24} sm={8} xl={4}>
            <Select<APIStyle | "all">
              value={protocolFilter}
              onChange={setProtocolFilter}
              options={[
                { value: "all", label: "全部协议" },
                { value: "chat_completions", label: "chat_completions" },
                { value: "responses", label: "responses" },
              ]}
              style={{ width: "100%" }}
            />
          </Col>
          <Col xs={24} xl={3}>
            <Typography.Paragraph className="soft-note">
              批量 Probe 只会对当前筛选结果里已配置完成的模型执行，缺凭据模型会自动跳过。
            </Typography.Paragraph>
          </Col>
        </Row>
        <Space wrap className="filter-summary">
          <Tag color="blue">筛选后 {filteredModels.length} / {models.length}</Tag>
          <Tag color="success">active {filteredActiveCount}</Tag>
          <Tag color="processing">configured {filteredConfiguredCount}</Tag>
          <Tag color="warning">missing creds {filteredModels.length - filteredConfiguredCount}</Tag>
        </Space>
      </Card>

      <Row gutter={[20, 20]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Statistic title="模型总数" value={models.length} loading={modelsQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Statistic title="启用模型" value={activeCount} loading={modelsQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Space className="metric-stack">
              <Statistic title="已配置模型" value={configuredCount} loading={modelsQuery.isLoading} />
              <Tag color="processing">responses {responseCount}</Tag>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Space className="metric-stack">
              <Statistic title="缺配置模型" value={missingConfigCount} loading={modelsQuery.isLoading} />
              <Tag color="warning">release_date 缺失 {missingReleaseDateCount}</Tag>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card className="panel-card">
        <div className="table-header">
          <Typography.Title level={4} style={{ marginBottom: 6 }}>
            模型清单
          </Typography.Title>
        </div>
        <Table
          rowKey="model_id"
          columns={columns}
          dataSource={filteredModels}
          loading={modelsQuery.isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {latestProbe ? (
        <Card className="panel-card">
          <div className="table-header">
            <Typography.Title level={5} style={{ marginBottom: 6 }}>
              Probe 结果摘要
            </Typography.Title>
          </div>
          <Space direction="vertical" style={{ display: "flex" }}>
            <Space wrap>
              <Tag color="blue">本轮 Probe {probeEntries.length}</Tag>
              <Tag color="success">成功 {probeEntries.length - probeFailureCount}</Tag>
              <Tag color="error">失败 {probeFailureCount}</Tag>
            </Space>
            <Space wrap>
              <Tag color={latestProbe.ok ? "success" : "error"}>
                {latestProbe.ok ? "OK" : "FAILED"}
              </Tag>
              <Tag>{latestProbe.model_name}</Tag>
              <Tag>{latestProbe.api_style}</Tag>
              <Tag>{latestProbe.latency_ms} ms</Tag>
            </Space>
            <Typography.Paragraph className="mono-block">
              {latestProbe.provider_error || latestProbe.response_text_preview || "No response body"}
            </Typography.Paragraph>
          </Space>
        </Card>
      ) : null}

      <Drawer
        title={editingModel ? `编辑模型 #${editingModel.model_id}` : "编辑模型"}
        open={editingModel !== null}
        onClose={() => setEditingModel(null)}
        width={520}
        destroyOnClose
      >
        <Form<ModelFormValues>
          form={form}
          layout="vertical"
          onFinish={(values) => {
            if (!editingModel) {
              return;
            }

            const payload: EvalModelUpdate = {
              model_name: values.model_name,
              release_date: values.release_date || null,
              api_url: values.api_url,
              api_style: values.api_style,
              api_model: values.api_model,
              api_key: values.api_key,
              is_active: values.is_active,
              sort_order: values.sort_order,
            };

            updateMutation.mutate({
              modelId: editingModel.model_id,
              payload,
            });
          }}
        >
          <Form.Item label="模型名称" name="model_name">
            <Input />
          </Form.Item>
          <Form.Item label="发布时间" name="release_date">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item label="API URL" name="api_url">
            <Input />
          </Form.Item>
          <Form.Item label="协议类型" name="api_style">
            <Select
              options={[
                { value: "chat_completions", label: "chat_completions" },
                { value: "responses", label: "responses" },
              ]}
            />
          </Form.Item>
          <Form.Item label="API Model" name="api_model">
            <Input />
          </Form.Item>
          <Form.Item label="API Key" name="api_key">
            <Input.Password placeholder="留空则不更新" />
          </Form.Item>
          <Form.Item label="是否启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item label="排序值" name="sort_order">
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
          <Space>
            <Button onClick={() => setEditingModel(null)}>取消</Button>
            <Button type="primary" htmlType="submit" loading={updateMutation.isPending}>
              保存
            </Button>
          </Space>
        </Form>
      </Drawer>
    </Space>
  );
}
