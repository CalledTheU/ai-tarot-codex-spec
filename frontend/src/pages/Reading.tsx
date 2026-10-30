import { useRef, useState, type FormEvent } from "react";
import type { Spread } from "../api/catalog";
import { clearToken, request, saveToken, type Reading } from "../api/private";
import { useResource } from "../hooks/useResource";
import RequestState from "../components/RequestState";
import InterpretationPanel from "../components/Interpretation";

export function Account() {
  const { state, retry } = useResource<{ email: string }>("/api/v1/auth/me");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const sending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const credentials = {
      email: form.get("email"),
      password: form.get("password"),
    };
    try {
      if (mode === "register") await request("/auth/register", credentials);
      const login = await request<{ access_token: string }>(
        "/auth/login",
        credentials,
      );
      saveToken(login.access_token);
      retry();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "认证失败");
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  async function logout() {
    setBusy(true);
    setMessage("");
    try {
      await request("/auth/logout");
      clearToken();
      retry();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "退出失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h1>账户</h1>
      {message && <p role="alert">{message}</p>}
      {state.status === "loading" ? (
        <p role="status">正在检查登录状态…</p>
      ) : state.status === "success" ? (
        <>
          <p>已登录：{state.data.email}</p>
          <a href="#/new">开始抽牌</a>{" "}
          <button disabled={busy} onClick={logout}>
            退出登录
          </button>
        </>
      ) : (
        <>
          <p>请登录后创建和查看个人抽牌记录。会话仅在当前浏览器标签页保存。</p>
          <form className="reading-form" onSubmit={submit}>
            <label>
              邮箱
              <input
                name="email"
                type="email"
                required
                maxLength={320}
                autoComplete="username"
              />
            </label>
            <label>
              密码
              <input
                name="password"
                type="password"
                required
                minLength={12}
                maxLength={128}
                autoComplete={
                  mode === "register" ? "new-password" : "current-password"
                }
              />
            </label>
            <p>密码须为 12–128 个字符，支持长口令；不强制字符组合。</p>
            <button disabled={busy}>
              {busy ? "提交中…" : mode === "register" ? "注册并登录" : "登录"}
            </button>
          </form>
          <button
            disabled={busy}
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "创建账户" : "已有账户，去登录"}
          </button>
          <p>{state.message}</p>
        </>
      )}
    </section>
  );
}

const categories = {
  love: "爱情",
  relationship: "人际关系",
  career: "事业",
  study: "学业",
  growth: "成长",
  other: "其他",
};

export function NewReading() {
  const { state, retry } = useResource<Spread[]>("/api/v1/spreads");
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  const pending = useRef<{ fingerprint: string; key: string } | null>(null);
  const sending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    const form = new FormData(event.currentTarget);
    const data = {
      question: String(form.get("question")).trim(),
      category: form.get("category"),
      background: String(form.get("background")).trim() || null,
      spread_id: form.get("spread_id"),
    };
    const fingerprint = JSON.stringify(data);
    if (pending.current?.fingerprint !== fingerprint)
      pending.current = { fingerprint, key: crypto.randomUUID() };
    sending.current = true;
    setBusy(true);
    setMessage("");
    try {
      const reading = await request<Reading>(
        "/readings",
        data,
        pending.current.key,
      );
      window.location.hash = "/readings/" + reading.id;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "抽牌失败");
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  if (state.status !== "success")
    return <RequestState state={state} retry={retry} />;
  return (
    <section>
      <h1>提出你的问题</h1>
      <p>由服务器抽牌并保存。塔罗仅用于文化学习和自我反思。</p>
      <a href="#/account">登录 / 账户</a>
      {message && <p role="alert">{message}</p>}
      <form className="reading-form" onSubmit={submit}>
        <label>
          牌阵
          <select name="spread_id" required>
            {state.data.map((s) => (
              <option key={s.id} value={s.slug}>
                {s.name} · {s.positions.length} 张牌
              </option>
            ))}
          </select>
        </label>
        <label>
          问题
          <textarea name="question" required maxLength={1000} />
        </label>
        <label>
          领域
          <select name="category">
            {Object.entries(categories).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          背景（可选）
          <textarea name="background" maxLength={5000} />
        </label>
        <button disabled={busy || !state.data.length}>
          {busy ? "保存抽牌中…" : "创建一次新抽牌"}
        </button>
      </form>
    </section>
  );
}

export function ReadingDetail({ id }: { id: string }) {
  const { state, retry } = useResource<Reading>(
    "/api/v1/readings/" + encodeURIComponent(id),
  );
  if (state.status !== "success")
    return (
      <>
        <RequestState state={state} retry={retry} />
        <a href="#/account">登录 / 账户</a>
      </>
    );
  const reading = state.data;
  return (
    <article>
      <a href="#/new">显式创建另一次抽牌</a>
      <h1>{reading.spread.name}</h1>
      <p>{reading.question}</p>
      <p>记录编号：{reading.id}</p>
      <p>抽牌结果已保存，刷新此地址可恢复。</p>
      <ol className="drawn-cards">
        {reading.cards.map((c) => (
          <li key={c.position_index}>
            <h2>
              {c.position_name} · {c.name}（
              {c.orientation === "upright" ? "正位" : "逆位"}）
            </h2>
            <p>
              {c.orientation === "upright"
                ? c.card_snapshot.upright_meaning
                : c.card_snapshot.reversed_meaning}
            </p>
            <a
              href={
                (c.orientation === "reversed" &&
                  c.card_snapshot.source_reference.reversed_url) ||
                c.card_snapshot.source_reference.url
              }
              target="_blank"
              rel="noreferrer"
            >
              创建时的历史牌义来源
            </a>
          </li>
        ))}
      </ol>
      <p>
        历史文献含年代局限，仅用于文化学习；AI 背景解释与可能情境属于生成内容。
      </p>
      <InterpretationPanel reading={reading} refresh={retry} />
    </article>
  );
}
