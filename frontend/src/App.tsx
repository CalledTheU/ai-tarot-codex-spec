import { useSyncExternalStore } from "react";
import { Account, NewReading, ReadingDetail } from "./pages/Reading";
import { CardDetail, Cards } from "./pages/Cards";
import { SpreadDetail, Spreads } from "./pages/Spreads";

function subscribe(callback: () => void) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}

function Home() {
  return (
    <section className="home">
      <p className="eyebrow">AI TAROT / 学习与反思</p>
      <h1>
        读懂每张牌，
        <br />
        从观察开始。
      </h1>
      <p className="intro">
        浏览 78
        张塔罗牌与四种牌阵。让象征成为理解自己的线索，保留思考与选择的空间。
      </p>
      <div className="home-links">
        <a className="primary-link" href="#/cards">
          走进牌库
        </a>
        <a href="#/spreads">了解牌阵</a>
      </div>
      <div className="home-note">
        <h2>先学习，再提问。</h2>
        <p>
          牌库提供可追溯的英文历史文献摘录。塔罗不具有经科学验证的预测能力。
          登录后可创建并保存抽牌记录。
        </p>
      </div>
    </section>
  );
}

export default function App() {
  const hash = useSyncExternalStore(
    subscribe,
    () => window.location.hash,
    () => "",
  );
  const [path, query = ""] = (hash.slice(1) || "/").split("?");
  const segments = path.split("/").filter(Boolean);
  let page;
  if (path === "/account") page = <Account />;
  else if (path === "/new") page = <NewReading />;
  else if (segments[0] === "readings" && segments.length === 2)
    page = <ReadingDetail key={segments[1]} id={segments[1]} />;
  else if (path === "/") page = <Home />;
  else if (path === "/cards") page = <Cards query={query} />;
  else if (segments[0] === "cards" && segments.length === 2)
    page = <CardDetail key={segments[1]} identifier={segments[1]} />;
  else if (path === "/spreads") page = <Spreads />;
  else if (segments[0] === "spreads" && segments.length === 2)
    page = <SpreadDetail key={segments[1]} identifier={segments[1]} />;
  else
    page = (
      <section>
        <h1>页面不存在</h1>
        <a href="#/">返回首页</a>
      </section>
    );
  return (
    <>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        跳到正文
      </a>
      <header className="site-header">
        <a className="brand" href="#/">
          AI TAROT
        </a>
        <nav aria-label="主导航">
          <a href="#/new">开始抽牌</a>
          <a href="#/account">账户</a>
          <a href="#/" aria-current={path === "/" ? "page" : undefined}>
            首页
          </a>
          <a
            href="#/cards"
            aria-current={segments[0] === "cards" ? "page" : undefined}
          >
            牌库
          </a>
          <a
            href="#/spreads"
            aria-current={segments[0] === "spreads" ? "page" : undefined}
          >
            牌阵
          </a>
        </nav>
      </header>
      <main id="main-content" tabIndex={-1}>
        {page}
      </main>
      <footer className="site-footer">
        用于文化学习与自我反思 · 不替代医疗、法律或投资建议
      </footer>
    </>
  );
}
