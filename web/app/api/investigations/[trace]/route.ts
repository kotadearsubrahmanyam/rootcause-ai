import { NextRequest } from "next/server";

type Context = { params: Promise<{ trace: string }> };

async function forward(req: NextRequest, context: Context) {
  const { trace } = await context.params;
  if (!/^[a-f0-9]{32}$/i.test(trace)) return new Response(null, {status: 400});
  if (req.method === "POST" && req.headers.get("origin") !== process.env.NEXTAUTH_URL) {
    return new Response(null, {status: 403});
  }
  const streaming = req.method === "GET" && req.nextUrl.searchParams.has("events");
  const upstream = await fetch(process.env.API_URL + "/investigations/" + trace + (streaming ? "/events" : ""), {
    method: req.method, cache: "no-store", signal: req.signal,
  });
  return new Response(upstream.body, {status: upstream.status, headers: {
    "Content-Type": upstream.headers.get("content-type") || "application/json", "Cache-Control": "no-store"
  }});
}
export { forward as GET, forward as POST };
