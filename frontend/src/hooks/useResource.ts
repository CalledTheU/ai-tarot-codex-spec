import { useEffect, useReducer, useState } from "react";
import { ApiError, fetchJson } from "../api/catalog";

export type Resource<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

export function useResource<T>(url: string) {
  const [state, setState] = useState<Resource<T>>({ status: "loading" });
  const [attempt, retry] = useReducer((n: number) => n + 1, 0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    fetchJson<T>(url, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "success", data });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "无法加载资料，请检查网络与服务状态。",
          });
      });
    return () => controller.abort();
  }, [url, attempt]);
  return { state, retry };
}
