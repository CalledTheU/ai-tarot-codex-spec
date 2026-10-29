import { useState, type FormEvent } from "react";
import { type Card, type CardPage, suitNames } from "../api/catalog";
import RequestState from "../components/RequestState";
import { useResource } from "../hooks/useResource";

function FilterForm({ query }: { query: string }) {
  const params = new URLSearchParams(query);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [arcana, setArcana] = useState(params.get("arcana_type") ?? "");
  const [suit, setSuit] = useState(params.get("suit") ?? "");
  function submit(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (search.trim()) next.set("q", search.trim());
    if (arcana) next.set("arcana_type", arcana);
    if (suit) next.set("suit", suit);
    window.location.hash = "/cards?" + next.toString();
  }
  return (
    <form className="filters" onSubmit={submit}>
      <label>
        搜索牌名
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          maxLength={100}
          placeholder="中文或英文牌名"
        />
      </label>
      <label>
        分类
        <select value={arcana} onChange={(e) => setArcana(e.target.value)}>
          <option value="">全部分类</option>
          <option value="major">大阿尔卡那</option>
          <option value="minor">小阿尔卡那</option>
        </select>
      </label>
      <label>
        花色
        <select value={suit} onChange={(e) => setSuit(e.target.value)}>
          <option value="">全部花色</option>
          {Object.entries(suitNames).map(([value, name]) => (
            <option key={value} value={value}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <button type="submit">查询</button>
      <a href="#/cards">清除筛选</a>
    </form>
  );
}

export function Cards({ query }: { query: string }) {
  const { state, retry } = useResource<CardPage>("/api/v1/cards?" + query);
  function pageLink(page: number) {
    const params = new URLSearchParams(query);
    params.set("page", String(page));
    return "#/cards?" + params.toString();
  }
  return (
    <>
      <header className="page-heading">
        <h1>牌库</h1>
        <p>从名称与象征入手，查阅每张牌的正逆位文献。</p>
      </header>
      <FilterForm key={query} query={query} />
      {state.status !== "success" ? (
        <RequestState state={state} retry={retry} />
      ) : (
        <>
          <p className="result-count" role="status">
            共 {state.data.total} 张牌
          </p>
          {state.data.items.length === 0 ? (
            <p className="notice">
              没有找到符合条件的牌，请调整筛选或返回上一页。
            </p>
          ) : (
            <div className="card-grid">
              {state.data.items.map((card) => (
                <a
                  className="catalog-card"
                  href={"#/cards/" + card.slug}
                  key={card.id}
                >
                  <div className="card-placeholder" aria-hidden="true">
                    <span>
                      {card.arcana_type === "major"
                        ? card.rank.padStart(2, "0")
                        : card.rank.toUpperCase()}
                    </span>
                    <span>
                      {card.suit ? suitNames[card.suit] : "大阿尔卡那"}
                    </span>
                  </div>
                  <h2>{card.name_zh}</h2>
                  <p lang="en" className="english-name">
                    {card.name_en}
                  </p>
                </a>
              ))}
            </div>
          )}
          <nav className="pagination" aria-label="牌库分页">
            {state.data.page > 1 && (
              <a href={pageLink(state.data.page - 1)}>上一页</a>
            )}
            <span>
              第 {state.data.page} 页 / 共{" "}
              {Math.max(1, Math.ceil(state.data.total / state.data.page_size))}{" "}
              页
            </span>
            {state.data.page * state.data.page_size < state.data.total && (
              <a href={pageLink(state.data.page + 1)}>下一页</a>
            )}
          </nav>
        </>
      )}
    </>
  );
}

export function CardDetail({ identifier }: { identifier: string }) {
  const { state, retry } = useResource<Card>(
    "/api/v1/cards/" + encodeURIComponent(identifier),
  );
  if (state.status !== "success")
    return <RequestState state={state} retry={retry} />;
  const card = state.data,
    source = card.source_reference;
  return (
    <article>
      <a href="#/cards">返回牌库</a>
      <header className="page-heading">
        <p className="eyebrow">
          {card.suit ? suitNames[card.suit] : "大阿尔卡那"}
        </p>
        <h1>{card.name_zh}</h1>
        <p lang="en">{card.name_en}</p>
      </header>
      <aside className="notice">
        历史文献摘录（英文）。原书含过时的性别、外貌、疾病与宿命描述，仅供文化学习，不是对你或他人的事实判断，也不构成专业建议。中文牌义译文尚未审核。
      </aside>
      <div className="meaning-columns">
        <section>
          <h2>正位</h2>
          <p lang="en" className="keywords">
            {card.upright_keywords.join(" · ")}
          </p>
          <blockquote lang="en">{card.upright_meaning}</blockquote>
        </section>
        <section>
          <h2>逆位</h2>
          <p lang="en" className="keywords">
            {card.reversed_keywords.join(" · ")}
          </p>
          <blockquote lang="en">{card.reversed_meaning}</blockquote>
        </section>
      </div>
      <section className="source">
        <h2>来源与版本</h2>
        <p lang="en">{source.title}</p>
        <p>
          {source.author} · {source.publication_year}
        </p>
        <p>{source.locator}</p>
        <p>{source.license}</p>
        <p>内容版本：{card.content_version}</p>
        <a href={source.url} target="_blank" rel="noreferrer">
          查阅原文（新窗口）
        </a>
        {source.reversed_url && (
          <p>
            <a href={source.reversed_url} target="_blank" rel="noreferrer">
              逆位补充章节（新窗口）
            </a>
          </p>
        )}
      </section>
    </article>
  );
}
