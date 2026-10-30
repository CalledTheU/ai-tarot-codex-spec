import { useState, type CSSProperties } from "react";
import type { Spread } from "../api/catalog";
import RequestState from "../components/RequestState";
import { useResource } from "../hooks/useResource";

function SpreadLayout({ spread }: { spread: Spread }) {
  const xs = spread.positions.map((p) => p.x),
    ys = spread.positions.map((p) => p.y);
  const minX = Math.min(...xs),
    minY = Math.min(...ys);
  const width = Math.max(...xs) - minX + 1,
    height = Math.max(...ys) - minY + 1;
  return (
    <>
      <div
        className="spread-scroll"
        role="region"
        aria-label="牌位布局，可横向滚动"
        tabIndex={0}
      >
        <ol
          className="spread-layout"
          aria-label={spread.name + "牌位布局"}
          style={{
            width: Math.max(220, width * 130),
            height: Math.max(170, height * 170),
          }}
        >
          {spread.positions.map((p) => (
            <li
              key={p.index}
              style={
                {
                  "--left": `${((p.x - minX + 0.5) / width) * 100}%`,
                  "--top": `${((p.y - minY + 0.5) / height) * 100}%`,
                } as CSSProperties
              }
            >
              <span>{p.index + 1}</span>
              <strong>{p.name}</strong>
            </li>
          ))}
        </ol>
      </div>
      <p className="layout-hint">
        空间不足时可横向滚动查看全部牌位；下方列出完整说明。
      </p>
      <ol className="position-notes">
        {spread.positions.map((p) => (
          <li key={p.index}>
            <strong>{p.name}</strong> · {p.description}
          </li>
        ))}
      </ol>
    </>
  );
}

export function Spreads() {
  const { state, retry } = useResource<Spread[]>("/api/v1/spreads");
  const [selected, setSelected] = useState<string | null>(null);
  if (state.status !== "success")
    return <RequestState state={state} retry={retry} />;
  const spread = state.data.find((s) => s.slug === selected) ?? state.data[0];
  return (
    <>
      <header className="page-heading">
        <h1>选择一个观察角度</h1>
        <p>牌阵帮助你整理问题。了解牌位后，可以登录并创建一次抽牌。</p>
      </header>
      {state.data.length === 0 ? (
        <p className="notice">暂无可用牌阵。</p>
      ) : (
        <div className="spread-workspace">
          <div className="spread-options" role="group" aria-label="选择牌阵">
            {state.data.map((s) => (
              <button
                className="spread-option"
                key={s.id}
                aria-pressed={s.slug === spread.slug}
                onClick={() => setSelected(s.slug)}
              >
                <strong>{s.name}</strong>
                <span>{s.positions.length} 张牌</span>
              </button>
            ))}
          </div>
          <section className="spread-preview">
            <h2>{spread.name}</h2>
            <p>{spread.description}</p>
            <SpreadLayout spread={spread} />
            <a href={"#/spreads/" + spread.slug}>查看牌阵详情</a>
            <p>
              <a href="#/new">开始抽牌</a>
            </p>
          </section>
        </div>
      )}
    </>
  );
}

export function SpreadDetail({ identifier }: { identifier: string }) {
  const { state, retry } = useResource<Spread>(
    "/api/v1/spreads/" + encodeURIComponent(identifier),
  );
  if (state.status !== "success")
    return <RequestState state={state} retry={retry} />;
  return (
    <article>
      <a href="#/spreads">返回牌阵选择</a>
      <header className="page-heading">
        <h1>{state.data.name}</h1>
        <p>{state.data.description}</p>
      </header>
      <SpreadLayout spread={state.data} />
      <p className="note">
        本项目定义的反思牌阵 · {state.data.positions.length} 个牌位 · 版本{" "}
        {state.data.version}。
      </p>
      <a href="#/new">开始抽牌</a>
    </article>
  );
}
