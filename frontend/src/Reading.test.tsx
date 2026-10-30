// @vitest-environment jsdom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import spreads from "../../backend/app/data/spreads.json";
import cards from "../../backend/app/data/cards.json";
import { Account, NewReading, ReadingDetail } from "./pages/Reading";
import InterpretationPanel from "./components/Interpretation";
import type { Reading } from "./api/private";

const fetchMock = vi.fn();
const ok = (data: unknown) => ({ ok: true, json: async () => data });
const reading: Reading = {
  category: "growth",
  background: null,
  id: "saved-reading",
  question: "我可以如何反思？",
  status: "pending_interpretation",
  spread: { name: "单张牌" },
  interpretation: null,
  cards: [
    {
      card_id: cards[0].id,
      name: "愚者",
      position_index: 0,
      position_name: "当前主题",
      orientation: "reversed",
      card_snapshot: cards[0],
    },
  ],
};
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("login stores a session and logout revokes it", async () => {
  fetchMock.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ error: { message: "请登录" } }),
  });
  render(<Account />);
  await userEvent.type(
    await screen.findByLabelText("邮箱"),
    "owner@example.test",
  );
  await userEvent.type(screen.getByLabelText("密码"), "a long password 123");
  fetchMock
    .mockResolvedValueOnce(ok({ access_token: "test-token" }))
    .mockResolvedValueOnce(ok({ email: "owner@example.test" }));
  await userEvent.click(screen.getByRole("button", { name: "登录" }));
  expect(await screen.findByText("已登录：owner@example.test")).toBeTruthy();
  expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe(
    "Bearer test-token",
  );
  fetchMock
    .mockResolvedValueOnce({ ok: true, status: 204 })
    .mockResolvedValueOnce({ ok: false, json: async () => null });
  await userEvent.click(screen.getByRole("button", { name: "退出登录" }));
  await waitFor(() =>
    expect(sessionStorage.getItem("ai-tarot-session")).toBeNull(),
  );
});

test("network retry uses the same draw key and disables repeated submission", async () => {
  fetchMock.mockResolvedValueOnce(ok(spreads));
  render(<NewReading />);
  const question = await screen.findByLabelText("问题");
  await userEvent.type(question, "我可以如何反思？");
  let fail!: (reason: Error) => void;
  fetchMock.mockReturnValueOnce(
    new Promise((_resolve, reject) => {
      fail = reject;
    }),
  );
  const button = screen.getByRole("button", { name: "创建一次新抽牌" });
  await userEvent.click(button);
  expect(
    (screen.getByRole("button", { name: "保存抽牌中…" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.submit(question.closest("form")!);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  fail(new Error("连接中断"));
  await screen.findByRole("alert");
  fetchMock.mockResolvedValueOnce(ok(reading));
  await userEvent.click(screen.getByRole("button", { name: "创建一次新抽牌" }));
  expect(fetchMock.mock.calls[1][1].headers["Idempotency-Key"]).toBe(
    fetchMock.mock.calls[2][1].headers["Idempotency-Key"],
  );
  expect(JSON.parse(fetchMock.mock.calls[2][1].body).cards).toBeUndefined();
  await waitFor(() =>
    expect(window.location.hash).toBe("#/readings/saved-reading"),
  );
});

test("saved reading restores orientation and original meaning", async () => {
  fetchMock.mockResolvedValueOnce(ok(reading));
  render(<ReadingDetail id={reading.id} />);
  expect(
    await screen.findByRole("heading", { name: "当前主题 · 愚者（逆位）" }),
  ).toBeTruthy();
  expect(screen.getByText(cards[0].reversed_meaning)).toBeTruthy();
});

test("AI failure retries interpretation on the saved reading without drawing", async () => {
  const refresh = vi.fn();
  fetchMock.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ error: { message: "模型暂时不可用" } }),
  });
  render(
    <InterpretationPanel reading={reading as Reading} refresh={refresh} />,
  );
  expect(screen.getByText(/资料会离开本机/)).toBeTruthy();
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: "生成 AI 解读" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "牌面与牌位不会改变",
  );
  fetchMock.mockResolvedValueOnce(ok({ status: "completed" }));
  await userEvent.click(
    screen.getByRole("button", { name: "保留原牌重试解读" }),
  );
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
    "/api/v1/readings/saved-reading/interpret",
    "/api/v1/readings/saved-reading/interpret",
  ]);
  expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
    style: "detailed",
    include_sources: true,
  });
});

test("completed reading shows all sections and does not call the model", () => {
  const interpretation = {
    summary: "摘要",
    scope_note: "仅用于反思",
    card_interpretations: [
      {
        card_id: cards[0].id,
        position_index: 0,
        position_name: "当前主题",
        orientation: "reversed" as const,
        traditional_meaning: "Historical excerpt",
        contextual_interpretation: "背景解释",
        source_ids: ["actual-source"],
      },
    ],
    synthesis: "综合",
    possible_scenarios: [{ description: "可能方向", basis: "牌位依据" }],
    action_suggestions: ["建议"],
    reflection_questions: ["问题"],
    uncertainties: ["未知"],
  };
  render(
    <InterpretationPanel
      reading={{ ...reading, status: "completed", interpretation } as Reading}
      refresh={vi.fn()}
    />,
  );
  expect(screen.getByRole("heading", { name: "不确定性" })).toBeTruthy();
  expect(screen.getByText("Historical excerpt")).toBeTruthy();
  expect(screen.getByText("背景解释")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "生成 AI 解读" })).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});
