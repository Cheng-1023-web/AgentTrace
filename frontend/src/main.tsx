import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  ExternalLink,
  Filter,
  GitBranch,
  Layers3,
  List,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
type Trace = {
  trace_id: string;
  root_name: string;
  status: string;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  span_count: number;
  failed_count: number;
};
type Span = {
  span_id: string;
  parent_span_id?: string;
  name: string;
  span_type: string;
  status: string;
  started_at: string;
  duration_ms?: number;
  input_summary?: string;
  output_summary?: string;
  error_type?: string;
  error_message?: string;
  model_name?: string;
};
type Detail = Trace & {
  spans: Span[];
  error_type?: string;
  error_message?: string;
};
type TreeNode = {
  span_id: string;
  name: string;
  span_type: string;
  status: string;
  duration_ms?: number;
  error_message?: string;
  children: TreeNode[];
};
type Stats = {
  total_traces: number;
  success_count: number;
  failed_count: number;
  running_count: number;
  success_rate: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  recent: { started_at: string; duration_ms: number; status: string }[];
};

const fmtTime = (v?: string) =>
  v
    ? new Date(v).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "—";
const fmtMs = (v?: number) =>
  v == null
    ? "—"
    : v < 1000
      ? `${Math.round(v)} ms`
      : `${(v / 1000).toFixed(2)} s`;
const statusLabel = (s: string) =>
  s === "SUCCESS" ? "成功" : s === "FAILED" ? "失败" : "执行中";

function App() {
  const [route, setRoute] = useState(window.location.pathname);
  const nav = (p: string) => {
    history.pushState({}, "", p);
    setRoute(p);
  };
  useEffect(() => {
    const h = () => setRoute(window.location.pathname);
    addEventListener("popstate", h);
    return () => removeEventListener("popstate", h);
  }, []);
  return (
    <div className="app">
      <Sidebar route={route} nav={nav} />
      <main className="main">
        {route.startsWith("/traces/") ? (
          <DetailPage id={route.split("/")[2]} nav={nav} />
        ) : route === "/stats" ? (
          <StatsPage />
        ) : (
          <ListPage nav={nav} />
        )}
      </main>
    </div>
  );
}

function Sidebar({ route, nav }: { route: string; nav: (p: string) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Activity size={18} />
        </div>
        <div>
          <strong>AgentTrace</strong>
          <span>observability studio</span>
        </div>
      </div>
      <div className="workspace">
        <span className="eyebrow">WORKSPACE</span>
        <div className="workspace-row">
          <span className="dot online" /> local-development{" "}
          <ChevronDown size={14} />
        </div>
      </div>
      <nav>
        <button
          className={route === "/traces" ? "active" : ""}
          onClick={() => nav("/traces")}
        >
          <List size={17} />
          执行记录<span className="nav-count">LIVE</span>
        </button>
        <button
          className={route === "/stats" ? "active" : ""}
          onClick={() => nav("/stats")}
        >
          <BarChart3 size={17} />
          运行统计
        </button>
      </nav>
      <div className="sidebar-foot">
        <div className="status-line">
          <span className="dot online" />
          Collector online
        </div>
        <div className="version">v0.1.0 · local</div>
      </div>
    </aside>
  );
}

function ListPage({ nav }: { nav: (p: string) => void }) {
  const [items, setItems] = useState<Trace[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const load = () => {
    setLoading(true);
    const q = new URLSearchParams({ page: "1", page_size: "50" });
    if (status) q.set("status", status);
    if (query) q.set("name", query);
    fetch(`${API}/api/v1/traces?${q}`)
      .then((r) => r.json())
      .then((d) => {
        setItems(d.items || []);
        setTotal(d.total || 0);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, [status]);
  return (
    <section>
      <Header
        title="执行记录"
        subtitle="所有 Agent 执行的实时追踪与故障入口"
        action={
          <button className="outline-button" onClick={load}>
            <RefreshCw size={15} />
            刷新
          </button>
        }
      />
      <div className="metrics">
        <Metric label="总执行" value={String(total)} icon={<Layers3 />} />
        <Metric
          label="成功率"
          value={
            items.length
              ? `${Math.round((items.filter((x) => x.status === "SUCCESS").length / items.length) * 100)}%`
              : "—"
          }
          icon={<CheckCircle2 />}
          tone="green"
        />
        <Metric
          label="失败步骤"
          value={String(items.reduce((n, x) => n + x.failed_count, 0))}
          icon={<ShieldAlert />}
          tone="red"
        />
        <Metric
          label="平均耗时"
          value={
            items.length
              ? fmtMs(
                  items.reduce((n, x) => n + (x.duration_ms || 0), 0) /
                    items.length,
                )
              : "—"
          }
          icon={<Clock3 />}
        />
      </div>
      <div className="toolbar">
        <div className="search">
          <Search size={16} />
          <input
            aria-label="搜索任务名称"
            placeholder="搜索任务名称..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
          />
        </div>
        <div className="filter">
          <Filter size={15} />
          <select
            aria-label="状态过滤"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">所有状态</option>
            <option value="SUCCESS">成功</option>
            <option value="FAILED">失败</option>
            <option value="RUNNING">执行中</option>
          </select>
        </div>
        <span className="toolbar-note">{total} 条记录</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>状态</th>
              <th>开始时间</th>
              <th>耗时</th>
              <th>步骤</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="empty">
                  正在载入追踪记录...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">
                  <Sparkles size={28} />
                  <strong>还没有执行记录</strong>
                  <span>运行 examples/demo_agent.py 生成真实数据</span>
                </td>
              </tr>
            ) : (
              items.map((t) => (
                <tr
                  key={t.trace_id}
                  onClick={() => nav(`/traces/${t.trace_id}`)}
                >
                  <td>
                    <div className="task-cell">
                      <div className="task-icon">
                        <GitBranch size={16} />
                      </div>
                      <div>
                        <strong>{t.root_name}</strong>
                        <code>{t.trace_id.slice(0, 18)}…</code>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Status status={t.status} />
                  </td>
                  <td className="muted">{fmtTime(t.started_at)}</td>
                  <td className="mono">{fmtMs(t.duration_ms)}</td>
                  <td>
                    <span className="step-pill">{t.span_count} steps</span>
                  </td>
                  <td>
                    <ExternalLink size={16} className="row-arrow" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DetailPage({ id, nav }: { id: string; nav: (p: string) => void }) {
  const [data, setData] = useState<Detail | null>(null);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [selected, setSelected] = useState<Span | null>(null);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/traces/${id}`).then((r) => r.json()),
      fetch(`${API}/api/v1/traces/${id}/tree`).then((r) => r.json()),
    ]).then(([detail, chain]) => {
      setData(detail);
      setTree(chain.roots || []);
    });
  }, [id]);
  if (!data) return <div className="loading-page">正在载入执行详情...</div>;
  return (
    <section>
      <button className="back-button" onClick={() => nav("/traces")}>
        <ArrowLeft size={16} />
        返回执行记录
      </button>
      <Header
        title={data.root_name}
        subtitle={`${data.trace_id} · ${fmtTime(data.started_at)}`}
        action={<Status status={data.status} />}
      />
      <div className="detail-grid">
        <div>
          <div className="panel timeline-panel">
            <div className="panel-head">
              <div>
                <span className="eyebrow">EXECUTION TIMELINE</span>
                <h2>
                  执行步骤 <small>{data.spans.length}</small>
                </h2>
              </div>
              <span className="duration-total">
                <Clock3 size={15} />
                {fmtMs(data.duration_ms)}
              </span>
            </div>
            <div className="timeline">
              {data.spans.map((s, i) => (
                <div
                  className={`timeline-item ${s.status === "FAILED" ? "failed" : ""}`}
                  key={s.span_id}
                  onClick={() => setSelected(s)}
                >
                  <div className="timeline-rail">
                    <span
                      className={`timeline-dot ${s.status.toLowerCase()}`}
                    />
                    {i < data.spans.length - 1 && (
                      <span className="timeline-line" />
                    )}
                  </div>
                  <div className="timeline-body">
                    <div className="timeline-top">
                      <div>
                        <strong>{s.name}</strong>
                        <span className="type-tag">{s.span_type}</span>
                      </div>
                      <span className="mono">{fmtMs(s.duration_ms)}</span>
                    </div>
                    <div className="timeline-meta">
                      <Status status={s.status} />
                      <code>{s.span_id.slice(0, 12)}</code>
                      {s.error_message && (
                        <span className="error-inline">
                          <AlertTriangle size={13} />
                          {s.error_message}
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronRight size={16} className="timeline-chevron" />
                </div>
              ))}
            </div>
          </div>
          <div className="panel chain-panel">
            <div className="panel-head">
              <div>
                <span className="eyebrow">CALL CHAIN</span>
                <h2>父子调用链</h2>
              </div>
              <GitBranch size={18} />
            </div>
            <div className="chain-tree">
              {tree.map((node) => (
                <TreeNodeView key={node.span_id} node={node} depth={0} />
              ))}
            </div>
          </div>
        </div>
        <div className="panel inspect-panel">
          {selected ? (
            <Inspector span={selected} />
          ) : (
            <div className="inspector-empty">
              <Activity size={30} />
              <strong>选择一个步骤</strong>
              <span>查看输入、输出和错误摘要</span>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function TreeNodeView({ node, depth }: { node: TreeNode; depth: number }) {
  return (
    <div className="tree-node">
      <div className="tree-row" style={{ paddingLeft: depth * 18 }}>
        <span className={`tree-status ${node.status.toLowerCase()}`} />
        <strong>{node.name}</strong>
        <span className="type-tag">{node.span_type}</span>
        <span className="mono">{fmtMs(node.duration_ms)}</span>
      </div>
      {node.error_message && (
        <div className="tree-error" style={{ paddingLeft: depth * 18 + 19 }}>
          <AlertTriangle size={12} />
          {node.error_message}
        </div>
      )}
      {node.children.map((child) => (
        <TreeNodeView key={child.span_id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

function Inspector({ span }: { span: Span }) {
  return (
    <div>
      <div className="panel-head">
        <div>
          <span className="eyebrow">SPAN INSPECTOR</span>
          <h2>{span.name}</h2>
        </div>
        <Status status={span.status} />
      </div>
      <div className="inspect-block">
        <label>Span ID</label>
        <code>{span.span_id}</code>
      </div>
      <div className="inspect-block">
        <label>输入摘要</label>
        <pre>{span.input_summary || "无输入摘要"}</pre>
      </div>
      <div className="inspect-block">
        <label>输出摘要</label>
        <pre>{span.output_summary || "无输出摘要"}</pre>
      </div>
      {span.error_message && (
        <div className="error-box">
          <div>
            <AlertTriangle size={16} />
            <strong>{span.error_type || "ExecutionError"}</strong>
          </div>
          <p>{span.error_message}</p>
        </div>
      )}
      {span.model_name && (
        <div className="model-meta">
          <span>模型</span>
          <strong>{span.model_name}</strong>
        </div>
      )}
    </div>
  );
}

function StatsPage() {
  const [data, setData] = useState<Stats | null>(null);
  useEffect(() => {
    fetch(`${API}/api/v1/stats`)
      .then((r) => r.json())
      .then(setData);
  }, []);
  if (!data) return <div className="loading-page">正在载入运行统计...</div>;
  const max = Math.max(...data.recent.map((x) => x.duration_ms), 1);
  return (
    <section>
      <Header
        title="运行统计"
        subtitle="观察近期 Agent 健康度与耗时变化"
        action={
          <div className="live-chip">
            <span className="dot online" />
            实时数据
          </div>
        }
      />
      <div className="metrics stats-metrics">
        <Metric
          label="成功率"
          value={`${data.success_rate}%`}
          icon={<CheckCircle2 />}
          tone="green"
        />
        <Metric
          label="失败次数"
          value={String(data.failed_count)}
          icon={<XCircle />}
          tone="red"
        />
        <Metric
          label="平均耗时"
          value={fmtMs(data.avg_duration_ms)}
          icon={<Clock3 />}
        />
        <Metric
          label="P95 耗时"
          value={fmtMs(data.p95_duration_ms)}
          icon={<Activity />}
        />
      </div>
      <div className="stats-grid">
        <div className="panel chart-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">RECENT RUNS</span>
              <h2>近期执行耗时</h2>
            </div>
            <span className="chart-legend">
              <span className="legend-swatch" />
              duration
            </span>
          </div>
          <div className="bar-chart">
            {data.recent.length ? (
              data.recent.map((x, i) => (
                <div className="bar-col" key={i}>
                  <div
                    className={`bar ${x.status === "FAILED" ? "bar-failed" : ""}`}
                    style={{
                      height: `${Math.max(8, (x.duration_ms / max) * 150)}px`,
                    }}
                    title={`${fmtMs(x.duration_ms)} · ${statusLabel(x.status)}`}
                  />
                  <span>
                    {new Date(x.started_at)
                      .getMinutes()
                      .toString()
                      .padStart(2, "0")}
                  </span>
                </div>
              ))
            ) : (
              <div className="empty">暂无趋势数据</div>
            )}
          </div>
        </div>
        <div className="panel breakdown-panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">HEALTH</span>
              <h2>状态分布</h2>
            </div>
            <BarChart3 size={18} />
          </div>
          <div className="health-ring">
            <div
              className="ring"
              style={
                {
                  "--progress": `${data.success_rate * 3.6}deg`,
                } as React.CSSProperties
              }
            >
              <strong>{data.success_rate}%</strong>
              <span>成功</span>
            </div>
          </div>
          <div className="health-rows">
            <div>
              <span className="dot online" />
              成功<strong>{data.success_count}</strong>
            </div>
            <div>
              <span className="dot danger" />
              失败<strong>{data.failed_count}</strong>
            </div>
            <div>
              <span className="dot running" />
              执行中<strong>{data.running_count}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Header({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <div className="breadcrumb">
          AGENTTRACE <span>/</span> OBSERVABILITY
        </div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
function Metric({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="metric">
      <div className={`metric-icon ${tone || ""}`}>{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function Status({ status }: { status: string }) {
  return (
    <span className={`status ${status.toLowerCase()}`}>
      <span className="status-dot" />
      {statusLabel(status)}
    </span>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
