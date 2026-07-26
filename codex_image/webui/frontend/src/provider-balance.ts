import type { ProviderBalanceStatus } from "./types";
import { getLegacyBridge } from "./state";

interface ProviderBalanceResponse {
  provider_id?: unknown;
  status?: unknown;
  remaining_usd?: unknown;
  used_usd?: unknown;
  total_usd?: unknown;
  remaining?: unknown;
  unit?: unknown;
}

function validAmount(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function formatPoints(value: number): string {
  const formatted = Number.isInteger(value)
    ? String(value)
    : value.toFixed(2).replace(/\.?0+$/, "");
  return `${formatted} 积分`;
}

export function formatProviderBalance(balance: ProviderBalanceStatus): string {
  if (balance.status === "unavailable") return "";
  if (balance.status === "loading") return "查询中…";
  if (balance.status === "error") return "余额未知";
  if (balance.unit === "POINTS" && validAmount(balance.remaining)) {
    return formatPoints(balance.remaining);
  }
  return validAmount(balance.remaining_usd) ? `$${balance.remaining_usd.toFixed(2)}` : "余额未知";
}

function balanceElement(): HTMLElement | null {
  if (typeof document.getElementById !== "function") return null;
  return document.getElementById("generationProviderBalance");
}

export function renderProviderBalance(providerId: string | null): void {
  const { state } = getLegacyBridge();
  const balance = providerId
    ? state.providerBalances[providerId] || { status: "unavailable" as const }
    : { status: "unavailable" as const };
  const element = balanceElement();
  if (!element) return;
  const text = formatProviderBalance(balance);
  element.textContent = text;
  element.hidden = !text;
  element.dataset.balanceStatus = balance.status;
  element.classList.toggle("is-loading", balance.status === "loading");
  element.classList.toggle("is-error", balance.status === "error");
}

function parsedBalance(payload: ProviderBalanceResponse): ProviderBalanceStatus {
  if (payload.status !== "ok") return { status: "error" };
  if (payload.unit === "POINTS" && validAmount(payload.remaining)) {
    return { status: "ok", remaining: payload.remaining, unit: "POINTS" };
  }
  if (!validAmount(payload.remaining_usd)) return { status: "error" };
  const balance: ProviderBalanceStatus = {
    status: "ok",
    remaining_usd: payload.remaining_usd,
  };
  if (validAmount(payload.used_usd)) balance.used_usd = payload.used_usd;
  if (validAmount(payload.total_usd)) balance.total_usd = payload.total_usd;
  return balance;
}

export async function refreshProviderBalance(providerId: string | null): Promise<void> {
  const { state } = getLegacyBridge();
  const requestSeq = ++state.providerBalanceRequestSeq;
  state.providerBalanceSelectedProviderId = providerId;
  const provider = state.generationCatalog?.providers.find((item) => item.id === providerId);
  if (!providerId || !provider || provider.builtin || !provider.balance_configured) {
    if (providerId) state.providerBalances[providerId] = { status: "unavailable" };
    if (state.selectedProviderId === providerId) renderProviderBalance(providerId);
    return;
  }

  state.providerBalances[providerId] = { status: "loading" };
  if (state.selectedProviderId === providerId) renderProviderBalance(providerId);
  try {
    const response = await fetch(`/api/provider-balances/${encodeURIComponent(providerId)}`, {
      headers: { Accept: "application/json" },
    });
    const payload = await response.json() as ProviderBalanceResponse;
    if (!response.ok) throw new Error("provider balance unavailable");
    if (requestSeq !== state.providerBalanceRequestSeq || state.selectedProviderId !== providerId) return;
    state.providerBalances[providerId] = parsedBalance(payload);
  } catch {
    if (requestSeq !== state.providerBalanceRequestSeq || state.selectedProviderId !== providerId) return;
    state.providerBalances[providerId] = { status: "error" };
  }
  renderProviderBalance(providerId);
}

export function syncSelectedProviderBalance(providerId: string | null): void {
  const { state } = getLegacyBridge();
  renderProviderBalance(providerId);
  if (state.providerBalanceSelectedProviderId === providerId) {
    const existing = providerId ? state.providerBalances[providerId] : undefined;
    if (!providerId || (existing && existing.status !== "unavailable")) return;
  }
  void refreshProviderBalance(providerId);
}
