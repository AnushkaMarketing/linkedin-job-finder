let token = "";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (!token) {
    const response = await fetch("/api/session");
    if (!response.ok)
      throw new Error(
        "Local engine is unavailable. Start the Python server on port 8765.",
      );
    token = (await response.json()).token;
  }
  const form = body instanceof FormData;
  const response = await fetch("/api" + path, {
    method,
    headers: {
      "X-Local-Token": token,
      ...(body && !form ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? (form ? body : JSON.stringify(body)) : undefined,
  });
  const data = await response
    .json()
    .catch(() => ({ detail: "The server returned an unreadable response." }));
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail
            ?.map(
              (d: { loc: string[]; msg: string }) =>
                `${d.loc.slice(1).join(".")}: ${d.msg}`,
            )
            .join("; ") || "Request failed",
    );
  return data;
}
