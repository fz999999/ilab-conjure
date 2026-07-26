import assert from "node:assert/strict";
import test from "node:test";

import { formatProviderBalance, syncSelectedProviderBalance } from "../../codex_image/webui/frontend/src/provider-balance";

test("formats successful provider balance as USD", () => {
  assert.equal(formatProviderBalance({ status: "ok", remaining_usd: 12.34 }), "$12.34");
  assert.equal(formatProviderBalance({ status: "ok", remaining_usd: 0 }), "$0.00");
});

test("formats WisArt balance as points", () => {
  assert.equal(formatProviderBalance({ status: "ok", remaining: 4020, unit: "POINTS" }), "4020 积分");
  assert.equal(formatProviderBalance({ status: "ok", remaining: 12.5, unit: "POINTS" }), "12.5 积分");
});

test("uses compact status text for non-success states", () => {
  assert.equal(formatProviderBalance({ status: "loading" }), "查询中…");
  assert.equal(formatProviderBalance({ status: "error" }), "余额未知");
  assert.equal(formatProviderBalance({ status: "unavailable" }), "");
});

test("rejects invalid successful balance values", () => {
  assert.equal(formatProviderBalance({ status: "ok", remaining_usd: Number.NaN }), "余额未知");
  assert.equal(formatProviderBalance({ status: "ok", remaining_usd: -1 }), "余额未知");
});


test("retries a configured provider after an unavailable catalog state", async () => {
  const originalWindow = globalThis.window;
  const originalDocument = globalThis.document;
  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  const balanceElement = {
    textContent: "",
    hidden: true,
    dataset: {} as Record<string, string>,
    classList: { toggle: () => undefined },
  };
  const state = {
    selectedProviderId: "provider-1",
    providerBalanceSelectedProviderId: "provider-1",
    providerBalanceRequestSeq: 0,
    providerBalances: { "provider-1": { status: "unavailable" as const } },
    generationCatalog: {
      providers: [{ id: "provider-1", builtin: false, balance_configured: true }],
    },
  };

  try {
    globalThis.window = {
      __codexImageWebUI: { state },
    } as unknown as Window & typeof globalThis;
    globalThis.document = {
      getElementById: (id: string) => id === "generationProviderBalance" ? balanceElement : null,
    } as unknown as Document;
    globalThis.fetch = async () => {
      fetchCount += 1;
      return {
        ok: true,
        json: async () => ({ status: "ok", remaining_usd: 8.01 }),
      } as Response;
    };

    syncSelectedProviderBalance("provider-1");
    await new Promise<void>((resolve) => setImmediate(resolve));

    assert.equal(fetchCount, 1);
    assert.equal(balanceElement.textContent, "$8.01");
    assert.equal(balanceElement.hidden, false);
  } finally {
    globalThis.window = originalWindow;
    globalThis.document = originalDocument;
    globalThis.fetch = originalFetch;
  }
});
