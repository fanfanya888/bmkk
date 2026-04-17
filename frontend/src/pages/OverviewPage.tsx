import { ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Progress,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
} from "antd";

import { api } from "../api/client";
import { formatPercent } from "../lib/evaluation";

export function OverviewPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: api.getHealth,
    refetchInterval: 30_000,
  });
  const dbHealthQuery = useQuery({
    queryKey: ["database-health"],
    queryFn: api.getDatabaseHealth,
    refetchInterval: 30_000,
  });
  const questionStatsQuery = useQuery({
    queryKey: ["question-stats"],
    queryFn: api.getQuestionStats,
  });
  const evaluationStatsQuery = useQuery({
    queryKey: ["evaluation-stats"],
    queryFn: api.getEvaluationStats,
  });
  const modelsQuery = useQuery({
    queryKey: ["models"],
    queryFn: api.listModels,
  });

  const error =
    healthQuery.error ??
    dbHealthQuery.error ??
    questionStatsQuery.error ??
    evaluationStatsQuery.error ??
    modelsQuery.error;

  const models = modelsQuery.data ?? [];
  const activeModels = models.filter((model) => model.is_active);
  const configuredModels = models.filter((model) => model.is_configured);
  const responsesModels = models.filter((model) => model.api_style === "responses");
  const missingConfigCount = models.filter((model) => !model.is_configured).length;
  const newestModel = models
    .filter((model) => model.release_date)
    .sort((left, right) => (left.release_date && right.release_date ? right.release_date.localeCompare(left.release_date) : 0))[0];
  const totalQuestions = questionStatsQuery.data?.total_questions ?? 0;
  const contentImageCount = questionStatsQuery.data?.questions_with_content_images ?? 0;
  const answerImageCount = questionStatsQuery.data?.questions_with_answer_images ?? 0;
  const analysisImageCount = questionStatsQuery.data?.questions_with_analysis_images ?? 0;
  const totalEvalRows = evaluationStatsQuery.data?.total_eval_rows ?? 0;
  const attempt1Completed = evaluationStatsQuery.data?.attempt_1_completed ?? 0;
  const attempt2Completed = evaluationStatsQuery.data?.attempt_2_completed ?? 0;
  const attempt3Completed = evaluationStatsQuery.data?.attempt_3_completed ?? 0;
  const platformHealth =
    healthQuery.data?.status === "ok" && dbHealthQuery.data?.database === "reachable"
      ? "稳定"
      : healthQuery.data?.status === "ok" || dbHealthQuery.data?.database === "reachable"
        ? "需关注"
        : "未知";

  const refreshAll = async () => {
    await Promise.all([
      healthQuery.refetch(),
      dbHealthQuery.refetch(),
      questionStatsQuery.refetch(),
      evaluationStatsQuery.refetch(),
      modelsQuery.refetch(),
    ]);
  };

  return (
    <Space direction="vertical" size={20} style={{ display: "flex" }}>
      <Card className="panel-card">
        <Space className="page-toolbar" wrap>
          <div>
            <Typography.Title level={4} style={{ marginBottom: 4 }}>
              运行概览
            </Typography.Title>
            <Typography.Paragraph className="soft-note">
              汇总服务状态、模型池状态和评测完成度。
            </Typography.Paragraph>
          </div>
          <Space wrap className="toolbar-actions">
            <Tag color={platformHealth === "稳定" ? "success" : platformHealth === "需关注" ? "warning" : "default"}>
              平台状态 {platformHealth}
            </Tag>
            <Tag color="processing">questions {totalQuestions}</Tag>
            <Tag color="blue">models {models.length}</Tag>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refreshAll()}
              loading={
                healthQuery.isFetching ||
                dbHealthQuery.isFetching ||
                questionStatsQuery.isFetching ||
                evaluationStatsQuery.isFetching ||
                modelsQuery.isFetching
              }
            >
              刷新
            </Button>
          </Space>
        </Space>
      </Card>

      {error instanceof Error ? <Alert type="error" message={error.message} showIcon /> : null}

      <Row gutter={[20, 20]}>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card panel-highlight">
            <Statistic
              title="服务健康"
              value={healthQuery.data?.status === "ok" ? "在线" : "未知"}
              loading={healthQuery.isLoading}
            />
            <Tag color={healthQuery.data?.status === "ok" ? "success" : "default"}>
              /health
            </Tag>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card panel-highlight-alt">
            <Statistic
              title="数据库连接"
              value={dbHealthQuery.data?.database === "reachable" ? "可达" : "未知"}
              loading={dbHealthQuery.isLoading}
            />
            <Tag color={dbHealthQuery.data?.database === "reachable" ? "processing" : "default"}>
              /health/db
            </Tag>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Statistic
              title="题目总数"
              value={questionStatsQuery.data?.total_questions ?? 0}
              loading={questionStatsQuery.isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card className="panel-card">
            <Statistic
              title="评测行总数"
              value={totalEvalRows}
              loading={evaluationStatsQuery.isLoading}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[20, 20]}>
        <Col xs={24} md={8}>
          <Card className="panel-card">
            <Statistic title="模型总数" value={models.length} loading={modelsQuery.isLoading} />
            <Space wrap style={{ marginTop: 16 }}>
              <Tag color="success">active {activeModels.length}</Tag>
              <Tag color="blue">configured {configuredModels.length}</Tag>
              <Tag color="processing">responses {responsesModels.length}</Tag>
              <Tag color="warning">missing {missingConfigCount}</Tag>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="panel-card">
            <Statistic
              title="Attempt 1 完成率"
              value={formatPercent(attempt1Completed, totalEvalRows)}
              loading={evaluationStatsQuery.isLoading}
            />
            <Progress percent={totalEvalRows ? Number(((attempt1Completed / totalEvalRows) * 100).toFixed(1)) : 0} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="panel-card">
            <Statistic
              title="最新模型发布时间"
              value={newestModel?.release_date ?? "-"}
              loading={modelsQuery.isLoading}
            />
            <Typography.Paragraph style={{ marginTop: 16, marginBottom: 0 }}>
              {newestModel ? `${newestModel.model_name} · ${newestModel.api_model}` : "尚未维护 release_date"}
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={[20, 20]}>
        <Col xs={24} xl={12}>
          <Card className="panel-card">
            <div className="table-header">
              <Typography.Title level={4} style={{ marginBottom: 6 }}>
                题目数据分布
              </Typography.Title>
            </div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="带题面图片"
                  value={contentImageCount}
                  suffix={totalQuestions ? ` / ${totalQuestions}` : ""}
                  loading={questionStatsQuery.isLoading}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="带标准答案图片"
                  value={answerImageCount}
                  suffix={totalQuestions ? ` / ${totalQuestions}` : ""}
                  loading={questionStatsQuery.isLoading}
                />
              </Col>
              <Col span={24}>
                <Statistic
                  title="带分析图片"
                  value={analysisImageCount}
                  suffix={totalQuestions ? ` / ${totalQuestions}` : ""}
                  loading={questionStatsQuery.isLoading}
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card className="panel-card">
            <div className="table-header">
              <Typography.Title level={4} style={{ marginBottom: 6 }}>
                评测完成情况
              </Typography.Title>
            </div>
            <Space direction="vertical" size={18} style={{ display: "flex" }}>
              <div>
                <Typography.Text>Attempt 1 · {attempt1Completed}/{totalEvalRows}</Typography.Text>
                <Progress percent={totalEvalRows ? Number(((attempt1Completed / totalEvalRows) * 100).toFixed(1)) : 0} />
              </div>
              <div>
                <Typography.Text>Attempt 2 · {attempt2Completed}/{totalEvalRows}</Typography.Text>
                <Progress percent={totalEvalRows ? Number(((attempt2Completed / totalEvalRows) * 100).toFixed(1)) : 0} />
              </div>
              <div>
                <Typography.Text>Attempt 3 · {attempt3Completed}/{totalEvalRows}</Typography.Text>
                <Progress percent={totalEvalRows ? Number(((attempt3Completed / totalEvalRows) * 100).toFixed(1)) : 0} />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
