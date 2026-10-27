// Groundcheck API dashboard: shows a key's coins, usage and settings. Talks to the same server it is served from.

interface Quota {
  coins: number;
  units: number;
  app_reward_paid: boolean;
  users_this_month: number;
}
interface RecentRequest {
  ts: number;
  path: string;
  method: string;
  user_agent: string | null;
  cf_country: string | null;
}
interface IpUsage {
  ip: string;
  requests: number;
  last_seen: number;
  recent_requests: RecentRequest[];
}
interface Stats {
  created: number | null;
  label: string | null;
  paused: boolean;
  total_requests: number;
  distinct_ips: number;
  ips: IpUsage[];
  limit: string;
}

// prices, as in the API docs: 1 coin = 1,000,000,000 units; a byte out costs 4 units, a byte in 1 unit; at least 1,000 units
const COIN = 1_000_000_000;
const OUT_UNITS = 4;
const MIN_UNITS = 1000;
const DAILY_COINS = 10;
const CAP_COINS = 30;
const APP_USERS = 100;
const ENDPOINTS: { name: string; inBytes: number; outBytes: number }[] = [
  { name: "/api/weather (232 bytes)", inBytes: 280, outBytes: 232 },
  { name: "/api/data with gzip (about 5 MB)", inBytes: 300, outBytes: 5_411_226 },
  { name: "/api/data without gzip (about 42 MB)", inBytes: 300, outBytes: 42_237_750 },
];

const STORAGE_KEY = "groundcheck-api-key";
const app = document.getElementById("app") as HTMLElement;
const signOut = document.getElementById("signout") as HTMLButtonElement;
let timer: number | undefined;
let notice: { text: string; err: boolean } | null = null;

function readKey(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}
function saveKey(k: string): void {
  try {
    if (k) localStorage.setItem(STORAGE_KEY, k);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private window: the key just is not remembered */
  }
}

type Child = Node | string | null | false;
function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string | boolean | ((e: Event) => void)> = {},
  ...kids: Child[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (typeof v === "function") el.addEventListener(k.replace(/^on/, ""), v);
    else if (typeof v === "boolean") {
      if (v) el.setAttribute(k, "");
    } else el.setAttribute(k, v);
  }
  for (const c of kids) if (c) el.append(c);
  return el;
}

function put(...kids: Child[]): void {
  app.replaceChildren(...kids.filter((k): k is Node | string => !!k));
}

const num = (n: number, digits = 0) => n.toLocaleString("en-GB", { maximumFractionDigits: digits });
const coinText = (c: number) => (c >= 1 ? num(c, 2) : c >= 0.001 ? num(c, 4) : num(c, 9));
function when(ts: number): string {
  return new Date(ts * 1000).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function api<T>(path: string, key: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { ...init, headers: { ...(init.headers ?? {}), "X-API-Key": key } });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { message?: string; error?: string }).message ?? (body as { error?: string }).error ?? `HTTP ${res.status}`);
  return body as T;
}

function bar(fraction: number, tone: "" | "good" | "warn" | "bad"): HTMLElement {
  const pct = Math.max(0, Math.min(1, fraction)) * 100;
  const fill = h("i");
  fill.style.width = `${pct}%`;
  return h("div", { class: `bar ${tone}` }, fill);
}

function statCard(label: string, value: string, extra: Child = null, barEl: HTMLElement | null = null): HTMLElement {
  return h("div", { class: "card" }, h("div", { class: "k" }, label), h("div", { class: "big" }, value), barEl, extra);
}

function setNotice(text: string, err = false): void {
  notice = { text, err };
}

function signIn(): void {
  document.title = "Groundcheck dashboard";
  signOut.hidden = true;
  const input = h("input", { type: "text", placeholder: "Paste your API key", autocomplete: "off", spellcheck: "false" });
  const go = async () => {
    const k = input.value.trim();
    if (!k) return;
    saveKey(k);
    await render();
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") void go();
  });
  const make = h("button", {
    onclick: async () => {
      make.disabled = true;
      try {
        const res = await fetch("/api/keys/new", { method: "POST" });
        const body = (await res.json()) as { api_key?: string };
        if (!body.api_key) throw new Error("No key came back");
        saveKey(body.api_key);
        setNotice("Your new key is saved in this browser. Copy it from Settings below. It starts with 10 coins.");
        await render();
      } catch (e) {
        setNotice(String(e instanceof Error ? e.message : e), true);
        signIn();
      }
    },
  }, "Make a new key");
  put(
    h("h1", {}, "Your API key"),
    notice ? h("div", { class: `msg${notice.err ? " err" : ""}` }, notice.text) : null,
    h("div", { class: "card" },
      h("p", { class: "muted" }, "Paste the key to see its coins, usage and settings. The key is only kept in this browser."),
      h("div", { class: "row" }, input, h("button", { class: "primary", onclick: () => void go() }, "Open"), make),
    ),
  );
  notice = null;
  input.focus();
}

function calculator(coins: number): HTMLElement {
  const sel = h("select");
  ENDPOINTS.forEach((e, i) => sel.append(h("option", { value: String(i) }, e.name)));
  const count = h("input", { type: "number", min: "1", value: "100", inputmode: "numeric" });
  const out = h("div", { class: "result" });
  const update = () => {
    const e = ENDPOINTS[Number(sel.value)];
    const n = Math.max(1, Math.floor(Number(count.value) || 1));
    const units = Math.max(MIN_UNITS, e.inBytes + e.outBytes * OUT_UNITS);
    const total = (units * n) / COIN;
    const perCoin = COIN / units;
    out.replaceChildren(
      `${num(n)} requests cost `, h("b", {}, `${coinText(total)} coins`),
      ` (1 coin buys ${num(perCoin)}). `,
      total <= coins ? "Your balance covers it." : `You have ${coinText(coins)}, so about ${num(Math.ceil((total - coins) / DAILY_COINS))} more day(s) of free coins.`,
    );
  };
  sel.addEventListener("change", update);
  count.addEventListener("input", update);
  update();
  return h("div", { class: "card" },
    h("h2", {}, "Price calculator"),
    h("div", { class: "calc" }, h("label", {}, "Request", sel), h("label", {}, "How many", count)),
    out,
  );
}

function settingsCard(key: string, stats: Stats): HTMLElement {
  let shown = false;
  const keyText = h("code", {}, "•".repeat(12) + key.slice(-4));
  const reveal = h("button", { onclick: () => {
    shown = !shown;
    keyText.textContent = shown ? key : "•".repeat(12) + key.slice(-4);
    reveal.textContent = shown ? "Hide" : "Show";
  } }, "Show");
  const copy = h("button", { onclick: async () => {
    try {
      await navigator.clipboard.writeText(key);
      copy.textContent = "Copied";
    } catch {
      copy.textContent = "Copy failed";
    }
    setTimeout(() => (copy.textContent = "Copy"), 1500);
  } }, "Copy");
  const label = h("input", { type: "text", maxlength: "60", placeholder: "A name for this key", value: stats.label ?? "" });
  const post = async (suffix: string, body: unknown, ok: string) => {
    try {
      await api(`/api/keys/${encodeURIComponent(key)}/${suffix}`, key, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setNotice(ok);
    } catch (e) {
      setNotice(String(e instanceof Error ? e.message : e), true);
    }
    await render();
  };
  return h("div", { class: "card" },
    h("h2", {}, "Settings"),
    h("div", { class: "keybox" }, h("span", { class: "muted" }, "Key"), keyText, reveal, copy),
    h("p", {}),
    h("div", { class: "row" }, label, h("button", { onclick: () => void post("settings", { label: label.value.trim() }, "Name saved.") }, "Save name")),
    h("p", {}),
    h("div", { class: "row" },
      h("span", {}, "Status: ", h("span", { class: `pill ${stats.paused ? "bad" : "good"}` }, stats.paused ? "paused" : "active")),
      h("button", { onclick: () => void post("settings", { paused: !stats.paused }, stats.paused ? "Key resumed." : "Key paused. It answers 403 until you resume it.") }, stats.paused ? "Resume" : "Pause"),
      h("button", { class: "danger", onclick: async () => {
        if (!confirm("Delete this key for good? This cannot be undone.")) return;
        try {
          await api(`/api/keys/${encodeURIComponent(key)}/revoke`, key, { method: "POST" });
          saveKey("");
          setNotice("The key was deleted.");
        } catch (e) {
          setNotice(String(e instanceof Error ? e.message : e), true);
        }
        await render();
      } }, "Delete key"),
    ),
    stats.created ? h("p", { class: "muted" }, `Created ${when(stats.created)}. Rate limit: ${stats.limit}.`) : null,
  );
}

function recentCard(stats: Stats): HTMLElement {
  const rows = stats.ips
    .flatMap((ip) => ip.recent_requests.map((r) => ({ ip: ip.ip, r })))
    .sort((a, b) => b.r.ts - a.r.ts)
    .slice(0, 25);
  const body = rows.length
    ? h("div", { class: "scroll" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", {}, "When"), h("th", {}, "Request"), h("th", {}, "From"), h("th", {}, "Client"))),
        h("tbody", {}, ...rows.map(({ ip, r }) => h("tr", {},
          h("td", {}, when(r.ts)),
          h("td", {}, h("code", {}, `${r.method} ${r.path.replace(/key=[^&]+/, "key=…")}`)),
          h("td", {}, `${ip}${r.cf_country ? ` · ${r.cf_country}` : ""}`),
          h("td", {}, (r.user_agent ?? "").slice(0, 60)),
        ))),
      ))
    : h("p", { class: "muted" }, "No requests yet. Try: ", h("code", {}, "curl -X QUERY /api/weather …"));
  return h("div", { class: "card" }, h("h2", {}, "Recent requests"), body);
}

async function render(): Promise<void> {
  window.clearTimeout(timer);
  const key = readKey();
  if (!key) {
    signIn();
    return;
  }
  signOut.hidden = false;
  try {
    const [quota, stats] = await Promise.all([
      api<Quota>("/api/quota", key),
      api<Stats>(`/api/keys/${encodeURIComponent(key)}/stats`, key),
    ]);
    document.title = `${coinText(quota.coins)} coins · Groundcheck dashboard`;
    const coinTone = quota.coins < 1 ? "bad" : quota.coins < 5 ? "warn" : "good";
    const usersLeft = Math.max(0, APP_USERS - quota.users_this_month);
    put(
      h("h1", {}, stats.label ? `${stats.label}` : "Your API key"),
      notice ? h("div", { class: `msg${notice.err ? " err" : ""}` }, notice.text) : null,
      h("div", { class: "grid" },
        statCard("Coins left", coinText(quota.coins),
          h("div", { class: "muted" }, `+${DAILY_COINS} a day, up to ${CAP_COINS} stored`), bar(quota.coins / CAP_COINS, coinTone)),
        statCard("Requests", num(stats.total_requests), h("div", { class: "muted" }, `from ${num(stats.distinct_ips)} address${stats.distinct_ips === 1 ? "" : "es"}`)),
        statCard("App users this month", `${num(quota.users_this_month)} / ${APP_USERS}`,
          h("div", { class: "muted" }, quota.app_reward_paid ? "The 100 coin reward was paid." : usersLeft ? `${usersLeft} more unique users for +100 coins` : "Reward on the next request"),
          bar(quota.app_reward_paid ? 1 : quota.users_this_month / APP_USERS, quota.app_reward_paid ? "good" : "")),
      ),
      calculator(quota.coins),
      recentCard(stats),
      settingsCard(key, stats),
      h("p", { class: "muted" }, "Refreshes every 15 seconds. Send ", h("code", {}, "X-Groundcheck-User"), " with an anonymous id of each of your app's users to count toward the 100-user reward."),
    );
    notice = null;
    timer = window.setTimeout(() => void render(), 15000);
  } catch (e) {
    const msg = String(e instanceof Error ? e.message : e);
    setNotice(/unknown api key|not found|404/i.test(msg) ? "That key was not found. Check it or make a new one." : msg, true);
    saveKey("");
    signIn();
  }
}

signOut.addEventListener("click", () => {
  saveKey("");
  void render();
});
void render();
