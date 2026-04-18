import { DeleteOutlined, SearchOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Form,
  Image,
  InputNumber,
  Popconfirm,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { api } from "../api/client";
import type {
  EvaluationResultAttemptRead,
  EvaluationResultAttemptStatus,
  EvaluationResultClearScope,
  EvaluationResultQueryParams,
  EvaluationResultRowResponse,
} from "../api/types";
import "katex/dist/katex.min.css";

interface ResultFilterFormValues {
  model_id?: number;
  question_id?: number;
  question_id_start?: number;
  question_id_end?: number;
  attempt: number;
  attempt_statuses: EvaluationResultAttemptStatus[];
  only_with_data: boolean;
}

const attemptDefinitions = [
  { key: "attempt_1", attempt: 1, label: "第一轮" },
  { key: "attempt_2", attempt: 2, label: "第二轮" },
  { key: "attempt_3", attempt: 3, label: "第三轮" },
] as const;

const attemptStatusOptions: Array<{ value: EvaluationResultAttemptStatus; label: string }> = [
  { value: "pending", label: "未运行" },
  { value: "generated", label: "已生成" },
  { value: "correct", label: "正确" },
  { value: "incorrect", label: "不正确" },
  { value: "error", label: "失败" },
];

const attemptStatusColorMap: Record<EvaluationResultAttemptStatus, string> = {
  pending: "default",
  generated: "processing",
  correct: "success",
  incorrect: "warning",
  error: "error",
};

const attemptStatusTextMap: Record<EvaluationResultAttemptStatus, string> = {
  pending: "未运行",
  generated: "已生成",
  correct: "正确",
  incorrect: "不正确",
  error: "失败",
};

function toAttemptStatusText(status: EvaluationResultAttemptStatus) {
  return attemptStatusTextMap[status] ?? status;
}

function renderAttemptSummaryTag(attempt: EvaluationResultAttemptRead) {
  return <Tag color={attemptStatusColorMap[attempt.status]}>{toAttemptStatusText(attempt.status)}</Tag>;
}

function renderEditedTag(attempt: EvaluationResultAttemptRead) {
  return attempt.is_result_overridden ? <Tag color="magenta">已更改</Tag> : null;
}

function hasAttemptData(attempt: EvaluationResultAttemptRead) {
  return Boolean(
    attempt.response_text ||
    attempt.judge_feedback ||
    attempt.error ||
    attempt.result !== null ||
    attempt.finished_at,
  );
}

function getAttemptLabel(attempt: number) {
  return attemptDefinitions.find((item) => item.attempt === attempt)?.label ?? `第 ${attempt} 轮`;
}

function getAttemptData(record: EvaluationResultRowResponse, attempt: number): EvaluationResultAttemptRead {
  if (attempt === 2) {
    return record.attempt_2;
  }
  if (attempt === 3) {
    return record.attempt_3;
  }
  return record.attempt_1;
}

function MarkdownPreview({
  text,
  emptyText,
  imageVersion,
}: {
  text: string | null | undefined;
  emptyText: string;
  imageVersion?: string;
}) {
  if (!text) {
    return <Typography.Text type="secondary">{emptyText}</Typography.Text>;
  }

  return (
    <div className="markdown-preview">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          img: ({ src, alt }) =>
            src ? (
              <Image
                src={api.getImageUrl(src, imageVersion)}
                alt={alt ?? ""}
                className="markdown-embedded-image"
              />
            ) : null,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

function PathPreviewList({ paths, imageVersion }: { paths: string[]; imageVersion?: string }) {
  if (!paths.length) {
    return <Typography.Text type="secondary">无</Typography.Text>;
  }

  return (
    <Space direction="vertical" size={12} style={{ display: "flex" }}>
      <Space wrap>
        {paths.map((path) => (
          <Tag key={path}>{path}</Tag>
        ))}
      </Space>
      <Image.PreviewGroup>
        <div className="image-grid">
          {paths.map((path) => (
            <Image
              key={path}
              src={api.getImageUrl(path, imageVersion)}
              alt={path}
              className="result-image"
            />
          ))}
        </div>
      </Image.PreviewGroup>
    </Space>
  );
}

export function ResultsPage() {
  const queryClient = useQueryClient();
  const [messageApi, contextHolder] = message.useMessage();
  const [filterForm] = Form.useForm<ResultFilterFormValues>();
  const [filters, setFilters] = useState<EvaluationResultQueryParams>({
    attempt: 1,
    only_with_data: true,
    limit: 20,
    offset: 0,
  });
  const [selectedRow, setSelectedRow] = useState<EvaluationResultRowResponse | null>(null);
  const [drawerAttempt, setDrawerAttempt] = useState<number>(1);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [overrideResultValue, setOverrideResultValue] = useState<0 | 1 | undefined>(undefined);
  const [imageVersion] = useState(() => String(Date.now()));

  const fetchResults = (params: EvaluationResultQueryParams) => api.listEvaluationResults(params);

  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const resultsQuery = useQuery({
    queryKey: ["evaluation-results", filters],
    queryFn: () => fetchResults(filters),
  });

  const clearAttemptMutation = useMutation({
    mutationFn: ({
      evalResultId,
      attempt,
      scope,
    }: {
      evalResultId: number;
      attempt: number;
      scope: EvaluationResultClearScope;
    }) => api.clearEvaluationResultAttempt(evalResultId, { attempt, scope }),
    onSuccess: async (row, variables) => {
      setSelectedRow(row);
      await queryClient.invalidateQueries({ queryKey: ["evaluation-results"] });
      messageApi.success(
        variables.scope === "generation_data"
          ? `已清除第 ${variables.attempt} 轮生成数据`
          : `已清除第 ${variables.attempt} 轮质检数据`,
      );
    },
    onError: (error: Error) => messageApi.error(error.message),
  });

  const overrideAttemptMutation = useMutation({
    mutationFn: ({
      evalResultId,
      attempt,
      result,
    }: {
      evalResultId: number;
      attempt: number;
      result: 0 | 1 | null;
    }) => api.overrideEvaluationResultAttempt(evalResultId, { attempt, result }),
    onSuccess: async (row, variables) => {
      setSelectedRow(row);
      setOverrideResultValue(undefined);
      await queryClient.invalidateQueries({ queryKey: ["evaluation-results"] });
      messageApi.success(
        variables.result === null
          ? `已撤销第 ${variables.attempt} 轮人工更改`
          : `已更新第 ${variables.attempt} 轮结果`,
      );
    },
    onError: (error: Error) => messageApi.error(error.message),
  });

  const currentAttempt = filters.attempt ?? 1;
  const drawerAttemptData = selectedRow ? getAttemptData(selectedRow, drawerAttempt) : null;
  const currentItems = resultsQuery.data?.items ?? [];
  const pagination = useMemo(() => {
    const total = resultsQuery.data?.total ?? 0;
    const pageSize = filters.limit ?? 20;
    const current = Math.floor((filters.offset ?? 0) / pageSize) + 1;
    return { total, pageSize, current };
  }, [filters.limit, filters.offset, resultsQuery.data?.total]);
  const selectedRowIndex = selectedRow
    ? currentItems.findIndex((item) => item.eval_result_id === selectedRow.eval_result_id)
    : -1;
  const hasPreviousOnCurrentPage = selectedRowIndex > 0;
  const hasPreviousPage =
    selectedRowIndex === 0 &&
    (filters.offset ?? 0) > 0;
  const hasNextOnCurrentPage = selectedRowIndex >= 0 && selectedRowIndex < currentItems.length - 1;
  const hasNextPage =
    selectedRowIndex >= 0 &&
    !hasNextOnCurrentPage &&
    (filters.offset ?? 0) + currentItems.length < (resultsQuery.data?.total ?? 0);
  const canGoPrevious = selectedRowIndex >= 0 && (hasPreviousOnCurrentPage || hasPreviousPage);
  const canGoNext = selectedRowIndex >= 0 && (hasNextOnCurrentPage || hasNextPage);

  useEffect(() => {
    setOverrideResultValue(undefined);
  }, [selectedRow?.eval_result_id, drawerAttempt]);

  const columns: ColumnsType<EvaluationResultRowResponse> = [
    {
      title: "Question ID",
      key: "question_id",
      width: 92,
      render: (_, record) => record.question.question_id,
    },
    {
      title: "模型",
      key: "model",
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text>{record.model.model_name}</Typography.Text>
          <Typography.Text type="secondary">{record.model.api_model}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "科目/题型",
      key: "meta",
      width: 150,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Typography.Text>{record.question.subject || "-"}</Typography.Text>
          <Typography.Text type="secondary">
            {record.question.question_type || record.question.difficulty || "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: `${getAttemptLabel(currentAttempt)}状态`,
      key: "selected_attempt",
      width: 145,
      render: (_, record) => {
        const attempt = getAttemptData(record, currentAttempt);
        return (
          <Space direction="vertical" size={2}>
            <Space wrap>
              {renderAttemptSummaryTag(attempt)}
              {renderEditedTag(attempt)}
            </Space>
            <Typography.Text type="secondary">result={attempt.result ?? "-"}</Typography.Text>
          </Space>
        );
      },
    },
    {
      title: "最近完成时间",
      dataIndex: "latest_finished_at",
      width: 168,
      render: (value: string | null) => (value ? new Date(value).toLocaleString() : "-"),
    },
    {
      title: "操作",
      key: "actions",
      width: 88,
      render: (_, record) => <Button size="small" onClick={() => openResultDrawer(record)}>比对</Button>,
    },
  ];

  const openResultDrawer = (record: EvaluationResultRowResponse) => {
    setSelectedRow(record);
    setDrawerAttempt(currentAttempt);
  };

  const goToNextResult = async () => {
    if (!selectedRow) {
      return;
    }

    if (hasNextOnCurrentPage) {
      setSelectedRow(currentItems[selectedRowIndex + 1]);
      return;
    }

    if (!hasNextPage) {
      return;
    }

    const nextFilters: EvaluationResultQueryParams = {
      ...filters,
      offset: (filters.offset ?? 0) + (filters.limit ?? 20),
    };

    setIsAdvancing(true);
    try {
      const nextPage = await queryClient.fetchQuery({
        queryKey: ["evaluation-results", nextFilters],
        queryFn: () => fetchResults(nextFilters),
      });
      setFilters(nextFilters);
      if (nextPage.items.length) {
        setSelectedRow(nextPage.items[0]);
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "切换到下一条失败");
    } finally {
      setIsAdvancing(false);
    }
  };

  const goToPreviousResult = async () => {
    if (!selectedRow) {
      return;
    }

    if (hasPreviousOnCurrentPage) {
      setSelectedRow(currentItems[selectedRowIndex - 1]);
      return;
    }

    if (!hasPreviousPage) {
      return;
    }

    const previousFilters: EvaluationResultQueryParams = {
      ...filters,
      offset: Math.max((filters.offset ?? 0) - (filters.limit ?? 20), 0),
    };

    setIsAdvancing(true);
    try {
      const previousPage = await queryClient.fetchQuery({
        queryKey: ["evaluation-results", previousFilters],
        queryFn: () => fetchResults(previousFilters),
      });
      setFilters(previousFilters);
      if (previousPage.items.length) {
        setSelectedRow(previousPage.items[previousPage.items.length - 1]);
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "切换到上一条失败");
    } finally {
      setIsAdvancing(false);
    }
  };

  const applyFilters = async () => {
    const values = await filterForm.validateFields();
    setFilters({
      model_id: values.model_id,
      question_id: values.question_id,
      question_id_start: values.question_id_start,
      question_id_end: values.question_id_end,
      attempt: values.attempt,
      attempt_statuses: values.attempt_statuses.length ? values.attempt_statuses : undefined,
      only_with_data: values.only_with_data,
      limit: filters.limit ?? 20,
      offset: 0,
    });
  };

  const resetFilters = () => {
    filterForm.setFieldsValue({
      model_id: undefined,
      question_id: undefined,
      question_id_start: undefined,
      question_id_end: undefined,
      attempt: 1,
      attempt_statuses: [],
      only_with_data: true,
    });
    setFilters({
      attempt: 1,
      only_with_data: true,
      limit: filters.limit ?? 20,
      offset: 0,
    });
  };

  return (
    <Space direction="vertical" size={20} style={{ display: "flex" }}>
      {contextHolder}
      {resultsQuery.error instanceof Error ? <Alert type="error" showIcon message={resultsQuery.error.message} /> : null}

      <Card className="panel-card">
        <Space className="page-toolbar" wrap>
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              结果查询与比对
            </Typography.Title>
            <Typography.Paragraph className="soft-note">
              可按轮次和状态筛选，默认查看第一轮。抽屉里支持 Markdown / LaTeX 渲染和图片预览。
            </Typography.Paragraph>
          </div>
          <Space wrap className="toolbar-actions">
            <Tag color="blue">总记录 {resultsQuery.data?.total ?? 0}</Tag>
            <Tag color="processing">当前轮次 {getAttemptLabel(currentAttempt)}</Tag>
            <Tag color="cyan">当前页 {resultsQuery.data?.items.length ?? 0}</Tag>
          </Space>
        </Space>

        <Form<ResultFilterFormValues>
          form={filterForm}
          layout="vertical"
          initialValues={{ attempt: 1, attempt_statuses: [], only_with_data: true }}
        >
          <Row gutter={[16, 0]}>
            <Col xs={24} md={8} xl={6}>
              <Form.Item label="Model" name="model_id">
                <Select
                  allowClear
                  loading={modelsQuery.isLoading}
                  options={(modelsQuery.data ?? []).map((model) => ({
                    value: model.model_id,
                    label: `${model.model_id} · ${model.model_name} · ${model.api_style}`,
                  }))}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="Question ID" name="question_id">
                <InputNumber min={1} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="起始题号" name="question_id_start">
                <InputNumber min={1} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="结束题号" name="question_id_end">
                <InputNumber min={1} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="轮次" name="attempt">
                <Select options={attemptDefinitions.map((item) => ({ value: item.attempt, label: item.label }))} />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="状态" name="attempt_statuses">
                <Select
                  mode="multiple"
                  allowClear
                  options={attemptStatusOptions}
                  placeholder="可多选"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={4} xl={3}>
              <Form.Item label="仅显示有结果" name="only_with_data" valuePropName="checked">
                <Switch />
              </Form.Item>
            </Col>
            <Col xs={24} md={24} xl={3}>
              <Form.Item label="操作">
                <Space wrap>
                  <Button type="primary" icon={<SearchOutlined />} onClick={() => void applyFilters()} loading={resultsQuery.isFetching}>
                    查询
                  </Button>
                  <Button onClick={resetFilters}>重置</Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      <Card className="panel-card">
        <Table
          rowKey="eval_result_id"
          columns={columns}
          dataSource={resultsQuery.data?.items ?? []}
          loading={resultsQuery.isLoading}
          pagination={{
            total: pagination.total,
            pageSize: pagination.pageSize,
            current: pagination.current,
            onChange: (page, pageSize) => {
              setFilters((current) => ({
                ...current,
                limit: pageSize,
                offset: (page - 1) * pageSize,
              }));
            },
          }}
          onRow={(record) => ({
            onClick: () => openResultDrawer(record),
          })}
        />
      </Card>

      <Drawer
        title={selectedRow ? `结果比对 · question ${selectedRow.question.question_id} · ${selectedRow.model.model_name}` : "结果比对"}
        open={selectedRow !== null}
        onClose={() => setSelectedRow(null)}
        width={1380}
        footer={
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <Space wrap>
              <Select<0 | 1>
                placeholder="更改为..."
                value={overrideResultValue}
                onChange={setOverrideResultValue}
                style={{ width: 160 }}
                options={[
                  { value: 1, label: "标记为正确" },
                  { value: 0, label: "标记为不正确" },
                ]}
                disabled={!selectedRow}
              />
              <Button
                type="primary"
                disabled={!selectedRow || overrideResultValue === undefined}
                loading={overrideAttemptMutation.isPending && overrideResultValue !== undefined}
                onClick={() =>
                  selectedRow &&
                  overrideResultValue !== undefined &&
                  overrideAttemptMutation.mutate({
                    evalResultId: selectedRow.eval_result_id,
                    attempt: drawerAttempt,
                    result: overrideResultValue,
                  })
                }
              >
                更改结果
              </Button>
              <Button
                disabled={!selectedRow || !drawerAttemptData?.is_result_overridden}
                loading={overrideAttemptMutation.isPending && overrideResultValue === undefined}
                onClick={() =>
                  selectedRow &&
                  overrideAttemptMutation.mutate({
                    evalResultId: selectedRow.eval_result_id,
                    attempt: drawerAttempt,
                    result: null,
                  })
                }
              >
                撤销更改
              </Button>
            </Space>
            <Space wrap>
              <Button onClick={() => void goToPreviousResult()} disabled={!canGoPrevious} loading={isAdvancing}>
                上一个
              </Button>
              <Button type="primary" onClick={() => void goToNextResult()} disabled={!canGoNext} loading={isAdvancing}>
                下一个
              </Button>
            </Space>
          </div>
        }
      >
        {selectedRow ? (
          <Space direction="vertical" size={20} style={{ display: "flex" }}>
            <Card className="panel-card">
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="Eval Result ID">{selectedRow.eval_result_id}</Descriptions.Item>
                <Descriptions.Item label="Question ID">{selectedRow.question.question_id}</Descriptions.Item>
                <Descriptions.Item label="模型">{selectedRow.model.model_name}</Descriptions.Item>
                <Descriptions.Item label="API Model">{selectedRow.model.api_model}</Descriptions.Item>
                <Descriptions.Item label="API Style">{selectedRow.model.api_style}</Descriptions.Item>
                <Descriptions.Item label="发布时间">{selectedRow.model.release_date || "-"}</Descriptions.Item>
                <Descriptions.Item label="科目">{selectedRow.question.subject || "-"}</Descriptions.Item>
                <Descriptions.Item label="题型">{selectedRow.question.question_type || "-"}</Descriptions.Item>
                <Descriptions.Item label="难度">{selectedRow.question.difficulty || "-"}</Descriptions.Item>
                <Descriptions.Item label="章节">{selectedRow.question.textbook_chapter || "-"}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card className="panel-card">
              <Typography.Title level={5}>题目内容</Typography.Title>
              <MarkdownPreview
                text={selectedRow.question.content_text}
                emptyText="无题面文本"
                imageVersion={imageVersion}
              />
              <Typography.Text strong>题面图片</Typography.Text>
              <div style={{ marginTop: 8 }}>
                <PathPreviewList paths={selectedRow.question.content_image_paths} imageVersion={imageVersion} />
              </div>
            </Card>

            <Card className="panel-card compare-attempt-card">
              <Space direction="vertical" size={16} style={{ display: "flex" }}>
                <Space className="page-toolbar" wrap>
                  <Space wrap>
                    {attemptDefinitions.map(({ attempt, label }) => (
                      <Tag
                        key={attempt}
                        color={drawerAttempt === attempt ? "processing" : "default"}
                        style={{ cursor: "pointer" }}
                        onClick={() => setDrawerAttempt(attempt)}
                      >
                        {label} · {toAttemptStatusText(getAttemptData(selectedRow, attempt).status)}
                      </Tag>
                    ))}
                  </Space>
                  {drawerAttemptData ? (
                    <Space wrap>
                      {renderAttemptSummaryTag(drawerAttemptData)}
                      {renderEditedTag(drawerAttemptData)}
                      <Tag>result={drawerAttemptData.result ?? "-"}</Tag>
                      <Tag color="default">judge_result={drawerAttemptData.judge_result ?? "-"}</Tag>
                      <Typography.Text type="secondary">
                        完成时间: {drawerAttemptData.finished_at ? new Date(drawerAttemptData.finished_at).toLocaleString() : "-"}
                      </Typography.Text>
                      {drawerAttemptData.result_overridden_at ? (
                        <Typography.Text type="secondary">
                          更改时间: {new Date(drawerAttemptData.result_overridden_at).toLocaleString()}
                        </Typography.Text>
                      ) : null}
                    </Space>
                  ) : null}
                </Space>

                {drawerAttemptData ? (
                  <>
                    <Space wrap>
                      <Popconfirm
                        title={`确认清除${getAttemptLabel(drawerAttempt)}生成数据？`}
                        description="会同时清掉该轮 response、judge feedback、result、error 和 finished_at。"
                        onConfirm={() =>
                          clearAttemptMutation.mutate({
                            evalResultId: selectedRow.eval_result_id,
                            attempt: drawerAttempt,
                            scope: "generation_data",
                          })
                        }
                        okButtonProps={{ loading: clearAttemptMutation.isPending }}
                        disabled={!hasAttemptData(drawerAttemptData)}
                      >
                        <Button
                          icon={<DeleteOutlined />}
                          danger
                          disabled={!hasAttemptData(drawerAttemptData)}
                        >
                          清除生成数据
                        </Button>
                      </Popconfirm>
                    </Space>

                    <Card size="small" className="panel-card">
                      <Typography.Title level={5}>模型回复</Typography.Title>
                      <Tabs
                        size="small"
                        items={[
                          {
                            key: "response-rendered",
                            label: "渲染",
                            children: (
                              <MarkdownPreview
                                text={drawerAttemptData.response_text}
                                emptyText="无模型回复"
                                imageVersion={imageVersion}
                              />
                            ),
                          },
                          {
                            key: "response-raw",
                            label: "原文",
                            children: (
                              <Typography.Paragraph className="mono-block">
                                {drawerAttemptData.response_text || "无模型回复"}
                              </Typography.Paragraph>
                            ),
                          },
                        ]}
                      />
                    </Card>

                    <Card size="small" className="panel-card">
                      <Typography.Title level={5}>Judge 回复</Typography.Title>
                      <Tabs
                        size="small"
                        items={[
                          {
                            key: "judge-rendered",
                            label: "渲染",
                            children: (
                              <MarkdownPreview
                                text={drawerAttemptData.judge_feedback}
                                emptyText="无 Judge 评价"
                                imageVersion={imageVersion}
                              />
                            ),
                          },
                          {
                            key: "judge-raw",
                            label: "原文",
                            children: (
                              <Typography.Paragraph className="mono-block">
                                {drawerAttemptData.judge_feedback || "无 Judge 评价"}
                              </Typography.Paragraph>
                            ),
                          },
                          {
                            key: "error",
                            label: "错误信息",
                            children: (
                              <Typography.Paragraph className="mono-block">
                                {drawerAttemptData.error || "无错误"}
                              </Typography.Paragraph>
                            ),
                          },
                        ]}
                      />
                    </Card>
                  </>
                ) : null}
              </Space>
            </Card>

            <Row gutter={[20, 20]}>
              <Col xs={24} xl={12}>
                <Card className="panel-card">
                  <Typography.Title level={5}>标准答案</Typography.Title>
                  <MarkdownPreview
                    text={selectedRow.question.answer_text}
                    emptyText="无标准答案文本"
                    imageVersion={imageVersion}
                  />
                  <Typography.Text strong>答案图片</Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    <PathPreviewList paths={selectedRow.question.answer_image_paths} imageVersion={imageVersion} />
                  </div>
                </Card>
              </Col>
              <Col xs={24} xl={12}>
                <Card className="panel-card">
                  <Typography.Title level={5}>解析信息</Typography.Title>
                  <MarkdownPreview
                    text={selectedRow.question.analysis_text}
                    emptyText="无解析文本"
                    imageVersion={imageVersion}
                  />
                  <Typography.Text strong>解析图片</Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    <PathPreviewList paths={selectedRow.question.analysis_image_paths} imageVersion={imageVersion} />
                  </div>
                </Card>
              </Col>
            </Row>
          </Space>
        ) : null}
      </Drawer>
    </Space>
  );
}
