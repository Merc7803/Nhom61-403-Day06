const API_URL = "https://api.openai.com/v1/chat/completions";

export async function runOpenAIAgent({
  apiKey,
  model,
  systemPrompt,
  systemSuffix = "",
  userAssistantMessages,
  tools,
  onToolCall,
  maxRounds = 10,
}) {
  const fullSystem =
    systemSuffix && String(systemSuffix).trim()
      ? `${systemPrompt}\n\n${String(systemSuffix).trim()}`
      : systemPrompt;
  const messages = [{ role: "system", content: fullSystem }, ...userAssistantMessages];

  const usageTotal = {
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
  };
  let requestCount = 0;
  let totalLatencyMs = 0;

  for (let round = 0; round < maxRounds; round++) {
    const t0 = performance.now();
    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages,
        tools,
        tool_choice: "auto",
        parallel_tool_calls: false,
        temperature: 0.2,
      }),
    });

    const raw = await res.text();
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error(raw.slice(0, 200) || "Invalid JSON from OpenAI");
    }

    if (!res.ok) {
      const msg = data?.error?.message || raw.slice(0, 300);
      throw new Error(msg);
    }

    const t1 = performance.now();
    totalLatencyMs += Math.max(0, t1 - t0);
    requestCount += 1;
    const u = data?.usage || null;
    if (u && typeof u === "object") {
      const pt = Number(u.prompt_tokens) || 0;
      const ct = Number(u.completion_tokens) || 0;
      const tt = Number(u.total_tokens) || pt + ct;
      usageTotal.prompt_tokens += pt;
      usageTotal.completion_tokens += ct;
      usageTotal.total_tokens += tt;
    }

    const choice = data.choices?.[0]?.message;
    if (!choice) throw new Error("No assistant message");

    const toolCalls = choice.tool_calls;
    if (toolCalls?.length) {
      messages.push({
        role: "assistant",
        content: choice.content || null,
        tool_calls: toolCalls,
      });
      for (const tc of toolCalls) {
        const fn = tc.function;
        let args = {};
        try {
          args = JSON.parse(fn.arguments || "{}");
        } catch {
          args = {};
        }
        const content = await onToolCall(fn.name, args);
        messages.push({
          role: "tool",
          tool_call_id: tc.id,
          content: typeof content === "string" ? content : JSON.stringify(content),
        });
      }
      continue;
    }

    const text = (choice.content || "").trim();
    if (!text) throw new Error("Empty assistant reply");
    return {
      text,
      usage: usageTotal,
      request_count: requestCount,
      latency_ms_total: Math.round(totalLatencyMs),
      latency_ms_avg: requestCount ? Math.round(totalLatencyMs / requestCount) : 0,
      rounds: round + 1,
    };
  }

  throw new Error("Too many tool rounds");
}

export function chatUiToApiMessages(uiMessages) {
  const out = [];
  for (const m of uiMessages) {
    if (m.role === "user") out.push({ role: "user", content: m.text });
    else if (m.role === "bot") out.push({ role: "assistant", content: m.text });
  }
  return out;
}

export function getOpenAIConfig() {
  const apiKey = import.meta.env.VITE_OPENAI_API_KEY || "";
  const model = import.meta.env.VITE_OPENAI_MODEL || "gpt-4o-mini";
  return { apiKey: String(apiKey).trim(), model };
}
