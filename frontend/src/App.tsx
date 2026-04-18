import { BarChartOutlined, ExperimentOutlined, MenuFoldOutlined, MenuOutlined, MenuUnfoldOutlined, RadarChartOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Drawer, Grid, Layout, Menu, Space, Spin, Typography } from "antd";
import { Suspense, lazy, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

const OverviewPage = lazy(async () => ({
  default: (await import("./pages/ResultsOverviewPage")).ResultsOverviewPage,
}));
const ModelsPage = lazy(async () => ({ default: (await import("./pages/ModelsPage")).ModelsPage }));
const EvaluationsPage = lazy(async () => ({
  default: (await import("./pages/EvaluationsPage")).EvaluationsPage,
}));
const ResultsPage = lazy(async () => ({ default: (await import("./pages/ResultsPage")).ResultsPage }));

const menuItems = [
  {
    key: "/",
    icon: <BarChartOutlined />,
    label: <NavLink to="/" className="nav-link">概览</NavLink>,
  },
  {
    key: "/models",
    icon: <RadarChartOutlined />,
    label: <NavLink to="/models" className="nav-link">模型管理</NavLink>,
  },
  {
    key: "/evaluations",
    icon: <ExperimentOutlined />,
    label: <NavLink to="/evaluations" className="nav-link">评测工作台</NavLink>,
  },
  {
    key: "/results",
    icon: <SearchOutlined />,
    label: <NavLink to="/results" className="nav-link">结果查询</NavLink>,
  },
];

const pageMetaMap: Record<
  string,
  {
    eyebrow: string;
    title: string;
    description: string;
  }
> = {
  "/": {
    eyebrow: "Result Overview",
    title: "概览",
    description: "按模型汇总首轮与多轮累计命中，适合看当前整体榜单表现。",
  },
  "/models": {
    eyebrow: "Model Registry",
    title: "模型管理",
    description: "统一维护模型配置、协议类型、启停状态和在线探活。",
  },
  "/evaluations": {
    eyebrow: "Evaluation Control",
    title: "评测工作台",
    description: "统一通过后端批量任务执行和跟踪，手动题号与范围模式可覆盖单题场景。",
  },
  "/results": {
    eyebrow: "Result Explorer",
    title: "结果查询",
    description: "按题目、模型和三轮 attempt 查询结果，并在同一页面完成结果比对与数据清理。",
  },
};

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.lg;
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [siderCollapsed, setSiderCollapsed] = useState(false);
  const currentPageMeta = pageMetaMap[location.pathname] ?? pageMetaMap["/"];

  const renderNavigation = () => (
    <>
      <div className="brand-block">
        {!siderCollapsed ? <Typography.Text className="brand-kicker">Benchmark Platform</Typography.Text> : null}
        <Typography.Title level={3} className="brand-title">
          {siderCollapsed ? "BEP" : "PDF Math Eval"}
        </Typography.Title>
        {!siderCollapsed ? (
          <Typography.Paragraph className="brand-copy">
            面向模型评测后台的第一版控制台。核心链路聚焦模型配置、连通性检查、题目预览和批量评测任务。
          </Typography.Paragraph>
        ) : null}
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => {
          navigate(key);
          setMobileNavOpen(false);
        }}
        className="nav-menu"
      />
    </>
  );

  const routeFallback = (
    <Card className="panel-card route-loading-card">
      <Space direction="vertical" size={12} align="center" style={{ width: "100%" }}>
        <Spin />
        <Typography.Text type="secondary">页面加载中...</Typography.Text>
      </Space>
    </Card>
  );

  return (
    <Layout className="app-shell">
      {isMobile ? (
        <Drawer
          placement="left"
          open={mobileNavOpen}
          onClose={() => setMobileNavOpen(false)}
          width={304}
          className="app-sider-drawer"
          styles={{ body: { padding: 0 } }}
        >
          <div className="app-sider app-sider-mobile">{renderNavigation()}</div>
        </Drawer>
      ) : (
        <Sider
          width={296}
          collapsedWidth={88}
          collapsible
          collapsed={siderCollapsed}
          trigger={null}
          className={`app-sider${siderCollapsed ? " app-sider-collapsed" : ""}`}
        >
          {renderNavigation()}
        </Sider>
      )}
      <Layout>
        <Header className="app-header">
          <div className="header-main">
            <Space size={16} align="start">
              {isMobile ? (
                <Button
                  type="text"
                  icon={<MenuOutlined />}
                  onClick={() => setMobileNavOpen(true)}
                  className="mobile-nav-button"
                />
              ) : (
                <Button
                  type="text"
                  icon={siderCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                  onClick={() => setSiderCollapsed((current) => !current)}
                  className="mobile-nav-button"
                />
              )}
              <div className="header-heading">
                <Typography.Text className="header-eyebrow">{currentPageMeta.eyebrow}</Typography.Text>
                <Typography.Title level={2} className="header-title">
                  {currentPageMeta.title}
                </Typography.Title>
                <Typography.Paragraph className="header-copy">
                  {currentPageMeta.description}
                </Typography.Paragraph>
              </div>
            </Space>
          </div>
        </Header>
        <Content className="app-content">
          <Suspense fallback={routeFallback}>
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/models" element={<ModelsPage />} />
              <Route path="/evaluations" element={<EvaluationsPage />} />
              <Route path="/results" element={<ResultsPage />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}
