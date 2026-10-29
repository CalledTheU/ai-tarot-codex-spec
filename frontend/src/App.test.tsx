// @vitest-environment jsdom
import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import cardsData from "../../backend/app/data/cards.json";
import spreadsData from "../../backend/app/data/spreads.json";
import App from "./App";

const fetchMock = vi.fn();
const card = cardsData[0];
const page = { items: [card], total: 78, page: 1, page_size: 20 };
const ok = (data: unknown) => ({ ok: true, json: async () => data });

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function navigate(path: string) {
  await act(async () => {
    window.location.hash = path;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

test("home links to the working catalog and identifies future features", async () => {
  render(<App />);
  expect(
    screen.getByRole("link", { name: "走进牌库" }).getAttribute("href"),
  ).toBe("#/cards");
  expect(screen.getByText(/抽牌与 AI 解读将在后续阶段开放/)).toBeTruthy();
  await userEvent.click(screen.getByText("跳到正文"));
  expect(document.activeElement?.id).toBe("main-content");
  expect(fetchMock).not.toHaveBeenCalled();
});

test("catalog loads, filters, and keeps filters in pagination links", async () => {
  window.history.replaceState(null, "", "/#/cards?suit=cups");
  fetchMock.mockResolvedValue(ok(page));
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: card.name_zh }),
  ).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "下一页" }).getAttribute("href"),
  ).toContain("suit=cups&page=2");
  await userEvent.type(screen.getByLabelText("搜索牌名"), "愚者");
  await userEvent.selectOptions(screen.getByLabelText("分类"), "major");
  await userEvent.click(screen.getByRole("button", { name: "查询" }));
  await waitFor(() =>
    expect(fetchMock.mock.lastCall?.[0]).toContain("arcana_type=major"),
  );
  expect(new URLSearchParams(window.location.hash.split("?")[1]).get("q")).toBe(
    "愚者",
  );
});

test("catalog shows loading, errors, retry and empty results", async () => {
  window.history.replaceState(null, "", "/#/cards");
  let finish!: (value: unknown) => void;
  fetchMock.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  render(<App />);
  expect(screen.getByRole("status").textContent).toContain("正在加载");
  await act(async () => {
    finish({
      ok: false,
      json: async () => ({ error: { message: "数据库暂时不可用" } }),
    });
  });
  expect((await screen.findByRole("alert")).textContent).toContain(
    "数据库暂时不可用",
  );
  fetchMock.mockResolvedValueOnce(ok({ ...page, items: [], total: 0 }));
  await userEvent.click(screen.getByRole("button", { name: "重新加载" }));
  expect(await screen.findByText(/没有找到符合条件的牌/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "下一页" })).toBeNull();
});

test("card detail shows both orientations and actual source links", async () => {
  window.history.replaceState(null, "", "/#/cards/the-fool");
  fetchMock.mockResolvedValue(ok(card));
  render(<App />);
  expect(await screen.findByRole("heading", { name: "愚者" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "正位" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "逆位" })).toBeTruthy();
  expect(screen.getByText(card.upright_meaning)).toBeTruthy();
  expect(screen.getByText(card.reversed_meaning)).toBeTruthy();
  expect(screen.getByText(/历史文献摘录（英文）/)).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: "查阅原文（新窗口）" })
      .getAttribute("href"),
  ).toBe(card.source_reference.url);
});

test("missing card displays the server error", async () => {
  window.history.replaceState(null, "", "/#/cards/missing");
  fetchMock.mockResolvedValue({
    ok: false,
    json: async () => ({ error: { message: "未找到这张牌" } }),
  });
  render(<App />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "未找到这张牌",
  );
});

test("network failures show a retry action", async () => {
  window.history.replaceState(null, "", "/#/cards");
  fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
  render(<App />);
  expect((await screen.findByRole("alert")).textContent).toContain(
    "无法加载资料",
  );
  expect(screen.getByRole("button", { name: "重新加载" })).toBeTruthy();
});

test("empty spread catalog is handled without rendering a broken layout", async () => {
  window.history.replaceState(null, "", "/#/spreads");
  fetchMock.mockResolvedValue(ok([]));
  render(<App />);
  expect(await screen.findByText("暂无可用牌阵。")).toBeTruthy();
  expect(screen.queryByRole("list")).toBeNull();
});

test("spread selection derives layout and position count from API data", async () => {
  window.history.replaceState(null, "", "/#/spreads");
  fetchMock.mockResolvedValue(ok(spreadsData));
  render(<App />);
  const five = await screen.findByRole("button", { name: /五张反思牌阵/ });
  await userEvent.click(five);
  expect(five.getAttribute("aria-pressed")).toBe("true");
  const layout = screen.getByRole("list", { name: "五张反思牌阵牌位布局" });
  expect(within(layout).getAllByRole("listitem")).toHaveLength(5);
  expect(within(layout).getByText("可能的发展方向")).toBeTruthy();
  expect(
    screen.getByRole("link", { name: "查看牌阵详情" }).getAttribute("href"),
  ).toBe("#/spreads/five-card-reflection");
});

test("spread detail survives direct navigation", async () => {
  window.history.replaceState(null, "", "/#/spreads/single-card");
  fetchMock.mockResolvedValue(ok(spreadsData[0]));
  render(<App />);
  expect(
    await screen.findByRole("list", { name: "单张牌牌位布局" }),
  ).toBeTruthy();
  expect(screen.getByText(/当前仅供预览，尚不能抽牌/)).toBeTruthy();
});

test("stale requests are aborted and cannot overwrite the new page", async () => {
  window.history.replaceState(null, "", "/#/cards/the-fool");
  let finish!: (value: unknown) => void;
  fetchMock.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  render(<App />);
  const firstSignal = fetchMock.mock.calls[0][1].signal as AbortSignal;
  fetchMock.mockResolvedValueOnce(ok(cardsData[1]));
  await navigate("/cards/the-magician");
  expect(await screen.findByRole("heading", { name: "魔术师" })).toBeTruthy();
  expect(firstSignal.aborted).toBe(true);
  await act(async () => {
    finish(ok(card));
  });
  expect(screen.queryByRole("heading", { name: "愚者" })).toBeNull();
});
