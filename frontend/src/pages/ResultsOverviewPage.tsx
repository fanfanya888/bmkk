import { ReloadOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Progress, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo } from "react";

import { api } from "../api/client";
import type { EvaluationLeaderboardRowResponse } from "../api/types";
import { formatPercent } from "../lib/evaluation";

function toPercent(value: number, total: number) {
  if (total <= 0) {
    return 0;
  }

  return Number(((value / total) * 100).toFixed(1));
}

function RateCell({
  count,
  total,
  strokeColor,
}: {
  count: number;
  total: number;
  strokeColor: string;
}) {
  const percent = toPercent(count, total);

  return (
    <div className="leaderboard-rate-cell">
      <Space size={6} wrap className="leaderboard-rate-cell-inline">
        <Typography.Text strong>{formatPercent(count, total)}</Typography.Text>
        <Typography.Text type="secondary">
          {count}/{total}
        </Typography.Text>
      </Space>
      <Progress
        percent={percent}
        size="small"
        showInfo={false}
        strokeColor={strokeColor}
        trailColor="#e8eef7"
      />
    </div>
  );
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderHtmlRateCell(count: number, total: number, fillClassName: string) {
  return `
    <div class="metric">
      <div class="metric-head">
        <span class="metric-percent">${escapeHtml(formatPercent(count, total))}</span>
        <span class="metric-count">${count}/${total}</span>
      </div>
      <div class="metric-track">
        <div class="metric-fill ${fillClassName}" style="width:${toPercent(count, total)}%"></div>
      </div>
    </div>
  `;
}

export function ResultsOverviewPage() {
  const leaderboardQuery = useQuery({
    queryKey: ["evaluation-leaderboard"],
    queryFn: api.getEvaluationLeaderboard,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const rows = leaderboardQuery.data?.items ?? [];
  const filteredRows = useMemo(
    () =>
      rows
        .filter((row) => row.sample_count > 0)
        .sort((left, right) => {
          const rightAttempt3Rate = toPercent(
            right.attempt_3_cumulative_correct_count,
            right.sample_count,
          );
          const leftAttempt3Rate = toPercent(
            left.attempt_3_cumulative_correct_count,
            left.sample_count,
          );
          if (rightAttempt3Rate !== leftAttempt3Rate) {
            return rightAttempt3Rate - leftAttempt3Rate;
          }
          const rightAttempt1Rate = toPercent(right.attempt_1_correct_count, right.sample_count);
          const leftAttempt1Rate = toPercent(left.attempt_1_correct_count, left.sample_count);
          if (rightAttempt1Rate !== leftAttempt1Rate) {
            return rightAttempt1Rate - leftAttempt1Rate;
          }
          if (right.attempt_3_cumulative_correct_count !== left.attempt_3_cumulative_correct_count) {
            return right.attempt_3_cumulative_correct_count - left.attempt_3_cumulative_correct_count;
          }
          if (left.sort_order !== right.sort_order) {
            return left.sort_order - right.sort_order;
          }
          return left.model_id - right.model_id;
        }),
    [rows],
  );

  const exportHtml = () => {
    const generatedAt = new Date();
    const generatedAtText = generatedAt.toLocaleString();
    const tableRows = filteredRows
      .map((record, index) => {
        const latestFinishedDate = record.latest_finished_at
          ? new Date(record.latest_finished_at).toLocaleDateString()
          : "-";
        return `
          <tr>
            <td>${index + 1}</td>
            <td>
              <div class="model-name">${escapeHtml(record.model_name)}</div>
              <div class="model-meta">${escapeHtml(record.api_model)}</div>
            </td>
            <td>${escapeHtml(record.release_date ?? "-")}</td>
            <td>${record.sample_count}</td>
            <td>${renderHtmlRateCell(record.attempt_1_correct_count, record.sample_count, "metric-fill-success")}</td>
            <td>${renderHtmlRateCell(record.attempt_2_cumulative_correct_count, record.sample_count, "metric-fill-primary")}</td>
            <td>${renderHtmlRateCell(record.attempt_3_cumulative_correct_count, record.sample_count, "metric-fill-primary")}</td>
            <td>${escapeHtml(latestFinishedDate)}</td>
          </tr>
        `;
      })
      .join("");

    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>模型榜单概览</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #edf2f8;
      --panel: #ffffff;
      --text: #182235;
      --muted: #60728f;
      --border: #dbe4f2;
      --accent: #1a73e8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 32px;
      font-family: "Segoe UI Variable", "IBM Plex Sans", "PingFang SC", "Noto Sans SC", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(26, 115, 232, 0.14), transparent 28%),
        linear-gradient(180deg, #f6f9fd 0%, var(--bg) 100%);
    }
    .sheet {
      max-width: 1360px;
      margin: 0 auto;
      background: rgba(255, 255, 255, 0.76);
      border: 1px solid rgba(219, 228, 242, 0.9);
      border-radius: 24px;
      box-shadow: 0 18px 48px rgba(24, 53, 103, 0.1);
      backdrop-filter: blur(10px);
      overflow: hidden;
    }
    .header {
      padding: 28px 32px 20px;
      border-bottom: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(247,250,255,0.92));
    }
    .kicker {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.2;
    }
    .sub {
      margin-top: 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .table-wrap {
      padding: 20px 24px 28px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border-radius: 18px;
      overflow: hidden;
    }
    thead th {
      padding: 14px 16px;
      text-align: left;
      font-size: 13px;
      color: #4c607f;
      background: #f6f9fd;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }
    tbody td {
      padding: 15px 16px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
      font-size: 14px;
    }
    tbody tr:last-child td {
      border-bottom: none;
    }
    .model-name {
      font-weight: 700;
    }
    .model-meta {
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }
    .metric {
      min-width: 110px;
    }
    .metric-head {
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }
    .metric-percent {
      font-weight: 700;
    }
    .metric-count {
      color: var(--muted);
      font-size: 13px;
    }
    .metric-track {
      margin-top: 6px;
      height: 6px;
      border-radius: 999px;
      background: #e8eef7;
      overflow: hidden;
    }
    .metric-fill {
      height: 100%;
      border-radius: inherit;
    }
    .metric-fill-success {
      background: linear-gradient(90deg, #34a853, #6dcb78);
    }
    .metric-fill-primary {
      background: linear-gradient(90deg, #1a73e8, #4da3ff);
    }
  </style>
</head>
<body>
  <div class="sheet">
    <div class="header">
      <span class="kicker">Result Overview</span>
      <h1>模型榜单概览</h1>
      <div class="sub">生成时间：${escapeHtml(generatedAtText)}</div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>排名</th>
            <th>模型</th>
            <th>模型发布时间</th>
            <th>样本</th>
            <th>首轮命中</th>
            <th>二轮累计命中</th>
            <th>三轮累计命中</th>
            <th>最近更新时间</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
  </div>
</body>
</html>`;

    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const downloadUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = downloadUrl;
    anchor.download = `results-overview-${generatedAt
      .toISOString()
      .replace(/:/g, "-")
      .slice(0, 19)}.html`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(downloadUrl);
  };

  const columns: ColumnsType<EvaluationLeaderboardRowResponse> = [
    {
      title: "排名",
      key: "rank",
      width: 60,
      render: (_, __, index) => index + 1,
    },
    {
      title: "模型",
      key: "model",
      width: 220,
      render: (_, record) => (
        <Space direction="vertical" size={4} className="leaderboard-model-meta">
          <Space wrap>
            <Typography.Text strong>{record.model_name}</Typography.Text>
            {!record.is_active ? <Tag>停用</Tag> : <Tag color="success">启用</Tag>}
          </Space>
          <Typography.Text type="secondary">{record.api_model}</Typography.Text>
          <Space wrap>
            <Tag color="default">样本 {record.sample_count}</Tag>
            {record.release_date ? <Tag color="purple">{record.release_date}</Tag> : null}
          </Space>
        </Space>
      ),
    },
    {
      title: "首轮命中",
      key: "attempt_1",
      width: 140,
      render: (_, record) => (
        <RateCell
          count={record.attempt_1_correct_count}
          total={record.sample_count}
          strokeColor="#34a853"
        />
      ),
    },
    {
      title: "二轮累计命中",
      key: "attempt_2",
      width: 140,
      render: (_, record) => (
        <RateCell
          count={record.attempt_2_cumulative_correct_count}
          total={record.sample_count}
          strokeColor="#1a73e8"
        />
      ),
    },
    {
      title: "三轮累计命中",
      key: "attempt_3",
      width: 140,
      render: (_, record) => (
        <RateCell
          count={record.attempt_3_cumulative_correct_count}
          total={record.sample_count}
          strokeColor="#1a73e8"
        />
      ),
    },
    {
      title: "最近更新时间",
      dataIndex: "latest_finished_at",
      width: 156,
      render: (value: string | null) => (value ? new Date(value).toLocaleString() : "-"),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ display: "flex" }}>
      {leaderboardQuery.error instanceof Error ? (
        <Alert type="error" message={leaderboardQuery.error.message} showIcon />
      ) : null}

      <Card className="panel-card">
        <div className="table-header">
          <Typography.Title level={4} style={{ marginBottom: 6 }}>
            模型榜单
          </Typography.Title>
          <Space wrap className="toolbar-actions">
            <Tag color="blue">模型 {filteredRows.length}</Tag>
            <Button onClick={exportHtml} disabled={!filteredRows.length}>
              导出 HTML
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void leaderboardQuery.refetch()}
              loading={leaderboardQuery.isFetching}
            >
              刷新
            </Button>
          </Space>
        </div>
        <Table
          rowKey="model_id"
          columns={columns}
          dataSource={filteredRows}
          loading={leaderboardQuery.isLoading}
          pagination={false}
        />
      </Card>
    </Space>
  );
}
