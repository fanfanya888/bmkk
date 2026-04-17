import { PauseOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Form, Input, InputNumber, Progress, Row, Select, Space, Switch, Table, Tag, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type {
  BatchSelectionMode,
  EvaluationExecutionMode,
  EvaluationBatchJobCreateRequest,
  EvaluationBatchJobItemResponse,
  EvaluationBatchJobSummaryResponse,
} from "../api/types";
import { countBatchItems, parseQuestionSpec } from "../lib/evaluation";

interface BatchEvaluationFormValues {
  model_id: number;
  attempt: number;
  persist_result: boolean;
  request_timeout_seconds?: number;
  execution_mode: EvaluationExecutionMode;
  selection_mode: BatchSelectionMode;
  limit?: number;
  question_id_start?: number;
  question_id_end?: number;
  question_spec?: string;
  force: boolean;
}

const executionModeTextMap: Record<EvaluationExecutionMode, string> = {
  generate_only: "仅生成",
  judge_only: "仅判分",
  generate_and_judge: "生成并判分",
};

const selectionModeTextMap: Record<BatchSelectionMode, string> = {
  pending_limit: "前 N 条未完成",
  pending_all: "全部未完成",
  range: "按题号范围",
  manual: "手动题号",
};

const statusTextMap: Record<string, string> = {
  pending: "待处理",
  queued: "排队中",
  running: "运行中",
  generated: "已生成",
  correct: "正确",
  incorrect: "不正确",
  error: "失败",
  unknown: "未知",
  completed: "已完成",
  cancelled: "已取消",
  failed: "任务失败",
};

const batchJobColor = (status: EvaluationBatchJobSummaryResponse["status"]) =>
  status === "completed" ? "success" : status === "failed" ? "error" : status === "cancelled" ? "warning" : "processing";

const toChineseText = (value: string) => statusTextMap[value] ?? value;

export function EvaluationsPage() {
  const [messageApi, contextHolder] = message.useMessage();
  const [manualPreviewIds, setManualPreviewIds] = useState<number[]>([]);
  const [manualPreviewWarnings, setManualPreviewWarnings] = useState<string[]>([]);
  const [selectedBatchJobId, setSelectedBatchJobId] = useState<string | null>(null);
  const [batchForm] = Form.useForm<BatchEvaluationFormValues>();

  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const batchJobsQuery = useQuery({
    queryKey: ["batch-jobs"],
    queryFn: api.listBatchJobs,
    refetchInterval: (query) =>
      query.state.data?.some((job) => job.status === "queued" || job.status === "running") ? 2000 : 15000,
  });

  useEffect(() => {
    if (!selectedBatchJobId && batchJobsQuery.data?.length) {
      setSelectedBatchJobId(batchJobsQuery.data[0].job_id);
    }
  }, [batchJobsQuery.data, selectedBatchJobId]);

  const batchDetailQuery = useQuery({
    queryKey: ["batch-job-detail", selectedBatchJobId],
    queryFn: () => api.getBatchJob(selectedBatchJobId!),
    enabled: !!selectedBatchJobId,
    refetchInterval: (query) =>
      query.state.data?.status === "queued" || query.state.data?.status === "running" ? 1500 : false,
  });

  const createBatchJobMutation = useMutation({
    mutationFn: (payload: EvaluationBatchJobCreateRequest) => api.createBatchJob(payload),
    onSuccess: async (job) => {
      setSelectedBatchJobId(job.job_id);
      await Promise.all([batchJobsQuery.refetch(), batchDetailQuery.refetch()]);
      messageApi.success(`批量任务已创建: ${job.job_id.slice(0, 8)}`);
    },
    onError: (error: Error) => messageApi.error(error.message),
  });

  const cancelBatchJobMutation = useMutation({
    mutationFn: (jobId: string) => api.cancelBatchJob(jobId),
    onSuccess: async (job) => {
      setSelectedBatchJobId(job.job_id);
      await Promise.all([batchJobsQuery.refetch(), batchDetailQuery.refetch()]);
      messageApi.success("已请求停止当前批量任务");
    },
    onError: (error: Error) => messageApi.error(error.message),
  });

  const currentSelectionMode = Form.useWatch("selection_mode", batchForm) ?? "pending_limit";
  const batchDetail = batchDetailQuery.data;
  const batchItems = batchDetail?.items ?? [];
  const batchItemSummary = countBatchItems(batchItems);
  const batchJobs = batchJobsQuery.data ?? [];
  const selectedBatchSummary = useMemo(
    () => batchJobs.find((job) => job.job_id === selectedBatchJobId) ?? null,
    [batchJobs, selectedBatchJobId],
  );
  const queuedJobCount = batchJobs.filter((job) => job.status === "queued").length;
  const runningJobCount = batchJobs.filter((job) => job.status === "running").length;
  const failedJobCount = batchJobs.filter((job) => job.status === "failed").length;
  const selectedBatchProgress = selectedBatchSummary?.total_questions
    ? Number(((selectedBatchSummary.completed_questions / selectedBatchSummary.total_questions) * 100).toFixed(1))
    : 0;

  const previewManualIds = async () => {
    const values = await batchForm.validateFields(["question_spec"]);
    const parsed = parseQuestionSpec(values.question_spec ?? "");
    setManualPreviewIds(parsed.ids);
    setManualPreviewWarnings(parsed.warnings);
    if (!parsed.ids.length) {
      messageApi.warning("没有解析出可执行的 question_id");
      return;
    }
    messageApi.success(`已解析 ${parsed.ids.length} 个 question_id`);
  };

  const submitBatchCreate = async () => {
    const values = await batchForm.validateFields();
    let questionIds: number[] | null = null;
    if (values.selection_mode === "manual") {
      const parsed = parseQuestionSpec(values.question_spec ?? "");
      setManualPreviewIds(parsed.ids);
      setManualPreviewWarnings(parsed.warnings);
      if (!parsed.ids.length) {
        messageApi.warning("没有可执行的 question_id");
        return;
      }
      questionIds = parsed.ids;
    }
    createBatchJobMutation.mutate({
      model_id: values.model_id,
      attempt: values.attempt,
      persist_result: values.persist_result,
      request_timeout_seconds: values.request_timeout_seconds,
      execution_mode: values.execution_mode,
      selection_mode: values.selection_mode,
      limit: values.selection_mode === "pending_limit" ? values.limit ?? 20 : null,
      question_id_start: values.selection_mode === "range" ? values.question_id_start ?? null : null,
      question_id_end: values.selection_mode === "range" ? values.question_id_end ?? null : null,
      question_ids: values.selection_mode === "manual" ? questionIds : null,
      force: values.force,
    });
  };

  const batchColumns: ColumnsType<EvaluationBatchJobItemResponse> = [
    { title: "Question ID", dataIndex: "question_id", width: 110 },
    {
      title: "状态",
      dataIndex: "status",
      width: 120,
      render: (value) => (
        <Tag color={value === "correct" ? "success" : value === "incorrect" ? "warning" : value === "error" ? "error" : value === "running" ? "processing" : "default"}>
          {toChineseText(value)}
        </Tag>
      ),
    },
    { title: "错误", dataIndex: "error", ellipsis: true, render: (value: string | null) => value || "-" },
    { title: "完成时间", dataIndex: "finished_at", width: 190, render: (value: string | null) => (value ? new Date(value).toLocaleString() : "-") },
  ];

  const batchJobColumns: ColumnsType<EvaluationBatchJobSummaryResponse> = [
    { title: "Job ID", dataIndex: "job_id", width: 180, render: (value: string) => value.slice(0, 12) },
    { title: "模型", dataIndex: "model_name", width: 150 },
    { title: "执行模式", dataIndex: "execution_mode", width: 150, render: (value: EvaluationExecutionMode) => executionModeTextMap[value] ?? value },
    { title: "批量模式", dataIndex: "selection_mode", width: 140, render: (value: BatchSelectionMode) => selectionModeTextMap[value] ?? value },
    { title: "状态", dataIndex: "status", width: 120, render: (value: EvaluationBatchJobSummaryResponse["status"]) => <Tag color={batchJobColor(value)}>{toChineseText(value)}</Tag> },
    { title: "进度", width: 150, render: (_, record) => `${record.completed_questions}/${record.total_questions}` },
    { title: "创建时间", dataIndex: "created_at", width: 190, render: (value: string) => new Date(value).toLocaleString() },
  ];

  return (
    <Space direction="vertical" size={20} style={{ display: "flex" }}>
      {contextHolder}
      {modelsQuery.error instanceof Error ? <Alert type="error" showIcon message={modelsQuery.error.message} /> : null}

      <Card className="panel-card">
        <Space className="page-toolbar" wrap>
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              批量运行状态
            </Typography.Title>
            <Typography.Paragraph className="soft-note">
              手动题号和题号范围都可以覆盖单题场景，不再单独保留单题调试页面。
            </Typography.Paragraph>
          </div>
          <Space wrap className="toolbar-actions">
            <Tag color="blue">批量任务 {batchJobs.length}</Tag>
            <Tag color="processing">运行中 {runningJobCount}</Tag>
            <Tag color="warning">排队中 {queuedJobCount}</Tag>
            <Tag color="error">失败 {failedJobCount}</Tag>
          </Space>
        </Space>
        <Space wrap>
          <Tag color="cyan">支持单题</Tag>
          <Tag>手动题号</Tag>
          <Tag>题号范围</Tag>
          {selectedBatchSummary ? (
            <Tag color={batchJobColor(selectedBatchSummary.status)}>
              当前任务 {selectedBatchSummary.completed_questions}/{selectedBatchSummary.total_questions} · {selectedBatchProgress}%
            </Tag>
          ) : null}
        </Space>
      </Card>

      <Card className="panel-card">
        <Typography.Title level={4}>后端批量任务</Typography.Title>
        <Typography.Paragraph className="soft-note">
          默认入口就是后端批量任务。跑单题时直接用手动题号输入一个 `question_id`，或者用范围模式指定同一个起止值即可。
        </Typography.Paragraph>
        <Form<BatchEvaluationFormValues> form={batchForm} layout="vertical" initialValues={{ attempt: 1, persist_result: true, execution_mode: "generate_and_judge", selection_mode: "pending_limit", limit: 20, force: false }}>
          <Row gutter={[16, 0]}>
            <Col xs={24} md={8}><Form.Item label="Model" name="model_id" rules={[{ required: true }]}><Select loading={modelsQuery.isLoading} options={(modelsQuery.data ?? []).map((model) => ({ value: model.model_id, label: `${model.model_id} · ${model.model_name} · ${model.api_style}` }))} showSearch optionFilterProp="label" /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item label="Attempt" name="attempt"><Select options={[{ value: 1, label: "1" }, { value: 2, label: "2" }, { value: 3, label: "3" }]} /></Form.Item></Col>
            <Col xs={24} md={4}><Form.Item label="Timeout (s)" name="request_timeout_seconds"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item label="写回数据库" name="persist_result" valuePropName="checked"><Switch /></Form.Item></Col>
          </Row>
          <Row gutter={[16, 0]}>
            <Col xs={24} md={8}><Form.Item label="执行模式" name="execution_mode"><Select options={[{ value: "generate_and_judge", label: "生成并判分" }, { value: "generate_only", label: "仅生成" }, { value: "judge_only", label: "仅判分" }]} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item label="批量模式" name="selection_mode"><Select options={[{ value: "pending_limit", label: "跑前 N 条未完成" }, { value: "pending_all", label: "跑全部未完成" }, { value: "range", label: "按 question_id 范围" }, { value: "manual", label: "手动指定题号" }]} /></Form.Item></Col>
            {currentSelectionMode === "pending_limit" ? <Col xs={24} md={8}><Form.Item label="数量限制" name="limit"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col> : null}
            {currentSelectionMode === "range" ? (
              <>
                <Col xs={24} md={8}><Form.Item label="起始 Question ID" name="question_id_start"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
                <Col xs={24} md={8}><Form.Item label="结束 Question ID" name="question_id_end"><InputNumber min={1} style={{ width: "100%" }} /></Form.Item></Col>
              </>
            ) : null}
          </Row>
          {currentSelectionMode === "manual" ? <Form.Item label="Question IDs" name="question_spec"><Input.TextArea rows={5} placeholder={"例如:\n9\n9,10,11\n20-25\n33 34 35"} /></Form.Item> : null}
          {(currentSelectionMode === "range" || currentSelectionMode === "manual") ? <Form.Item label="包含已完成题目" name="force" valuePropName="checked"><Switch /></Form.Item> : null}
          <Space wrap>
            {currentSelectionMode === "manual" ? <Button onClick={() => void previewManualIds()}>预览手动题号</Button> : null}
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => void submitBatchCreate()} loading={createBatchJobMutation.isPending}>创建批量任务</Button>
          </Space>
        </Form>
      </Card>

      {currentSelectionMode === "manual" ? (
        <Card className="panel-card">
          <Typography.Title level={5}>手动题号解析</Typography.Title>
          {manualPreviewIds.length ? (
            <Space direction="vertical" style={{ display: "flex" }}>
              <Typography.Paragraph>共解析出 {manualPreviewIds.length} 个 question_id。</Typography.Paragraph>
              <Space wrap>{manualPreviewIds.slice(0, 40).map((id) => <Tag key={id}>{id}</Tag>)}{manualPreviewIds.length > 40 ? <Tag>... +{manualPreviewIds.length - 40}</Tag> : null}</Space>
              {manualPreviewWarnings.length ? <Alert type="warning" showIcon message={`解析警告: ${manualPreviewWarnings.join(" | ")}`} /> : null}
            </Space>
          ) : <Typography.Paragraph type="secondary">尚未解析手动题号。</Typography.Paragraph>}
        </Card>
      ) : null}

      <Row gutter={[20, 20]}>
        <Col xs={24} xl={12}>
          <Card className="panel-card">
            <Typography.Title level={5}>当前任务进度</Typography.Title>
            {batchDetail ? (
              <Space direction="vertical" style={{ display: "flex" }}>
                <Space wrap>
                  <Tag color={batchJobColor(batchDetail.status)}>{toChineseText(batchDetail.status)}</Tag>
                  <Tag>{batchDetail.model_name}</Tag>
                  <Tag>{executionModeTextMap[batchDetail.execution_mode]}</Tag>
                  <Tag>{selectionModeTextMap[batchDetail.selection_mode]}</Tag>
                  {batchDetail.current_question_id ? <Tag>当前题号 {batchDetail.current_question_id}</Tag> : null}
                </Space>
                <Progress percent={batchDetail.total_questions ? Number(((batchDetail.completed_questions / batchDetail.total_questions) * 100).toFixed(1)) : 0} status={batchDetail.status === "running" ? "active" : batchDetail.status === "failed" ? "exception" : "normal"} />
                <Space wrap>
                  <Tag>已完成 {batchDetail.completed_questions}</Tag>
                  <Tag>总数 {batchDetail.total_questions}</Tag>
                  <Tag color="cyan">已生成 {batchDetail.generated_count}</Tag>
                  <Tag color="success">正确 {batchDetail.correct_count}</Tag>
                  <Tag color="warning">不正确 {batchDetail.incorrect_count}</Tag>
                  <Tag color="error">失败 {batchDetail.error_count}</Tag>
                  <Tag>未知 {batchDetail.unknown_count}</Tag>
                  <Tag>已取消 {batchDetail.cancelled_count}</Tag>
                </Space>
                {batchDetail.job_error ? <Alert type="error" showIcon message={batchDetail.job_error} /> : null}
                <Space wrap>
                  <Button onClick={() => void batchJobsQuery.refetch()} loading={batchJobsQuery.isFetching}>刷新任务列表</Button>
                  <Button icon={<PauseOutlined />} disabled={!selectedBatchJobId || !selectedBatchSummary || !["queued", "running"].includes(selectedBatchSummary.status)} loading={cancelBatchJobMutation.isPending} onClick={() => selectedBatchJobId && cancelBatchJobMutation.mutate(selectedBatchJobId)}>请求停止</Button>
                </Space>
              </Space>
            ) : <Typography.Paragraph type="secondary">还没有选中批量任务。</Typography.Paragraph>}
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="panel-card">
            <Typography.Title level={5}>任务结果分布</Typography.Title>
            {batchDetail ? (
              <Space wrap>
                <Tag>待处理 {batchItemSummary.pending}</Tag>
                <Tag color="processing">运行中 {batchItemSummary.running}</Tag>
                <Tag color="cyan">已生成 {batchItemSummary.generated}</Tag>
                <Tag color="success">正确 {batchItemSummary.correct}</Tag>
                <Tag color="warning">不正确 {batchItemSummary.incorrect}</Tag>
                <Tag color="error">失败 {batchItemSummary.error}</Tag>
                <Tag>未知 {batchItemSummary.unknown}</Tag>
                <Tag>已取消 {batchItemSummary.cancelled}</Tag>
              </Space>
            ) : <Typography.Paragraph type="secondary">尚未获取任务明细。</Typography.Paragraph>}
          </Card>
        </Col>
      </Row>

      <Card className="panel-card">
        <Typography.Title level={5}>任务明细</Typography.Title>
        <Typography.Paragraph>这里只展示状态和错误摘要，不回显模型原始回复或 judge 详情。</Typography.Paragraph>
        <Table rowKey={(record) => `${record.question_id}-${record.finished_at ?? "pending"}`} columns={batchColumns} dataSource={batchItems} pagination={{ pageSize: 8 }} scroll={{ x: 900 }} />
      </Card>

      <Card className="panel-card">
        <Typography.Title level={5}>最近批量任务</Typography.Title>
        <Table rowKey="job_id" columns={batchJobColumns} dataSource={batchJobs} pagination={{ pageSize: 5 }} onRow={(record) => ({ onClick: () => setSelectedBatchJobId(record.job_id) })} scroll={{ x: 1050 }} />
      </Card>
    </Space>
  );
}
