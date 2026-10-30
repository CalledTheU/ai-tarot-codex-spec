import { useRef, useState, type FormEvent } from "react";
import { request, type Interpretation, type Reading } from "../api/private";

function InterpretationText({
  value,
  reading,
}: {
  value: Interpretation;
  reading: Reading;
}) {
  return (
    <section aria-label="AI 解读">
      <h2>AI 解读</h2>
      <p>{value.scope_note}</p>
      <h3>整体摘要</h3>
      <p>{value.summary}</p>
      {value.card_interpretations.map((c) => (
        <section key={c.position_index}>
          <h3>
            {c.position_name}（{c.orientation === "upright" ? "正位" : "逆位"}）
          </h3>
          <h4>历史牌义摘录（英文原文）</h4>
          <p>{c.traditional_meaning}</p>
          <h4>结合背景的 AI 解释</h4>
          <p>{c.contextual_interpretation}</p>
          {reading.cards
            .filter((card) => card.position_index === c.position_index)
            .map((card) => (
              <p key={card.card_id}>
                <a
                  href={
                    (card.orientation === "reversed" &&
                      card.card_snapshot.source_reference.reversed_url) ||
                    card.card_snapshot.source_reference.url
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  {card.card_snapshot.source_reference.title}
                </a>
                {" · "}历史摘录版本 {card.card_snapshot.content_version}
              </p>
            ))}
        </section>
      ))}
      <h3>综合解读</h3>
      <p>{value.synthesis}</p>
      <h3>可能情境（推演）</h3>
      <ul>
        {value.possible_scenarios.map((s, i) => (
          <li key={i}>
            {s.description} · 依据：{s.basis}
          </li>
        ))}
      </ul>
      {(
        [
          ["行动建议", value.action_suggestions],
          ["反思问题", value.reflection_questions],
          ["不确定性", value.uncertainties],
        ] as const
      ).map(([title, items]) => (
        <section key={title}>
          <h3>{title}</h3>
          <ul>
            {items.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}

export default function InterpretationPanel({
  reading,
  refresh,
}: {
  reading: Reading;
  refresh: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  const sending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await request("/readings/" + reading.id + "/interpret", {
        style: form.get("style"),
        include_sources: true,
      });
      refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "解读失败，请保留原牌重试",
      );
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  if (reading.interpretation)
    return (
      <InterpretationText value={reading.interpretation} reading={reading} />
    );
  return (
    <section>
      <h2>生成解读</h2>
      <p>
        解读会将本记录的问题、背景和牌面发送至管理员配置的模型服务；若配置为外部服务，资料会离开本机。不要提交敏感个人资料。
      </p>
      {reading.status === "failed" && (
        <p role="status">上次解读失败，原抽牌结果已保留。</p>
      )}
      {reading.status === "processing" ? (
        <>
          <p role="status">
            正在生成解读，请稍后刷新。服务中断后可以沿用原牌重试。
          </p>
          <button onClick={refresh}>刷新状态</button>
        </>
      ) : null}
      {message && <p role="alert">{message}。可以重试，牌面与牌位不会改变。</p>}
      <form className="reading-form" onSubmit={submit}>
        <label>
          解读风格
          <select name="style">
            <option value="detailed">详细</option>
            <option value="concise">简洁</option>
          </select>
        </label>
        <label className="consent">
          <input type="checkbox" required />
          我已了解模型处理范围，同意发送本次记录生成解读
        </label>
        <button disabled={busy}>
          {busy
            ? "生成中…"
            : message || reading.status === "failed"
              ? "保留原牌重试解读"
              : reading.status === "processing"
                ? "检查并恢复解读"
                : "生成 AI 解读"}
        </button>
      </form>
      <p>生成失败不会重新抽牌。已成功的解读会被复用。</p>
    </section>
  );
}
