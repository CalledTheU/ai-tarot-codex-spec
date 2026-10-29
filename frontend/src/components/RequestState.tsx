import type { Resource } from "../hooks/useResource";

export default function RequestState({
  state,
  retry,
}: {
  state: Exclude<Resource<unknown>, { status: "success" }>;
  retry: () => void;
}) {
  return state.status === "loading" ? (
    <p role="status" className="notice">
      正在加载资料…
    </p>
  ) : (
    <div role="alert" className="notice error">
      <p>{state.message}</p>
      <button onClick={retry}>重新加载</button>
    </div>
  );
}
