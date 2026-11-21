"use strict";
const universe = [
  ["NVDA", "NVIDIA", "chips"],
  ["AMD", "AMD", "chips"],
  ["AVGO", "Broadcom", "chips"],
  ["MSFT", "Microsoft", "cloud"],
  ["GOOGL", "Alphabet", "cloud"],
  ["AMZN", "Amazon", "cloud"],
  ["IBM", "IBM", "software"],
  ["PLTR", "Palantir", "software"],
].map(([ticker, name, group]) => ({
  ticker,
  name,
  group,
  exchange: ticker === "IBM" ? "NYSE" : "NASDAQ",
}));
const el = (id) => document.getElementById(id);
const stock = (s) => universe.find((x) => x.ticker === s);
const fmt = (n) => (n > 0 ? "+" : "") + n.toFixed(2) + "%";
const tone = (n) => (n > 0 ? "gain" : n < 0 ? "loss" : "");
const dateLabel = (d) =>
  new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const dateOK = (d) =>
  typeof d === "string" &&
  /^\d{4}-\d{2}-\d{2}$/.test(d) &&
  Number.isFinite(Date.parse(d));
const groupList = () =>
  universe.filter(
    (c) => el("group").value === "all" || c.group === el("group").value,
  );
let selected = "NVDA",
  metrics = null,
  quoteKey = null,
  refreshing = false;
try {
  const saved = JSON.parse(
    localStorage.getItem("aimw.preferences.v10") || "{}",
  );
  if (["all", "chips", "cloud", "software"].includes(saved.group))
    el("group").value = saved.group;
  if (groupList().some((c) => c.ticker === saved.ticker))
    selected = saved.ticker;
} catch {}
function remember() {
  try {
    localStorage.setItem(
      "aimw.preferences.v10",
      JSON.stringify({ group: el("group").value, ticker: selected }),
    );
  } catch {}
}
function option(c) {
  return new Option(c.ticker, c.ticker);
}
function renderPicker() {
  const list = groupList();
  if (!list.some((c) => c.ticker === selected)) selected = list[0].ticker;
  el("company").replaceChildren(...list.map(option));
  el("company").value = selected;
  el("companyName").textContent = stock(selected).name;
}
function renderMetrics() {
  const list = groupList(),
    ranked = list
      .filter((c) => Number.isFinite(metrics?.changes?.[c.ticker]))
      .map((c) => ({ ...c, pct: metrics.changes[c.ticker] }))
      .sort((a, b) => b.pct - a.pct || a.ticker.localeCompare(b.ticker));
  const n = ranked.length,
    median = n
      ? (ranked[Math.floor(n / 2)].pct + ranked[Math.floor((n - 1) / 2)].pct) /
        2
      : null;
  el("median").textContent = n ? fmt(median) : "—";
  el("median").className = n ? tone(median) : "";
  el("breadth").textContent = n
    ? ranked.filter((c) => c.pct > 0).length + " / " + n
    : "—";
  el("coverage").textContent = n + " of " + list.length + " companies covered";
  const leader = ranked.reduce(
    (a, b) => (!a || Math.abs(b.pct) > Math.abs(a.pct) ? b : a),
    null,
  );
  el("leader").replaceChildren();
  if (leader) {
    const move = document.createElement("span");
    move.className = tone(leader.pct);
    move.textContent = fmt(leader.pct);
    el("leader").append(leader.ticker + " ", move);
  } else el("leader").textContent = "—";
  el("session").textContent = metrics
    ? "Peer comparison · " + dateLabel(metrics.date)
    : "Peer comparison unavailable";
  el("basis").textContent = metrics
    ? dateLabel(metrics.previousDate) +
      " → " +
      dateLabel(metrics.date) +
      " · Includes extended hours."
    : "No comparison available.";
  if (
    metrics &&
    Date.now() - Date.parse(metrics.date + "T23:59:59Z") > 6 * 86400000
  )
    el("basis").textContent += " Older snapshot.";
  const max = Math.max(...ranked.map((c) => Math.abs(c.pct)), 0.001);
  const buttons = ranked.map((c) => {
    const b = document.createElement("button");
    b.className = "mover";
    b.setAttribute("aria-pressed", String(c.ticker === selected));
    b.setAttribute("aria-label", c.name + " " + fmt(c.pct) + ", show chart");
    const ticker = document.createElement("span");
    ticker.className = "ticker";
    ticker.textContent = c.ticker;
    const axis = document.createElement("span");
    axis.className = "axis";
    axis.setAttribute("aria-hidden", "true");
    const bar = document.createElement("i");
    bar.className = "bar";
    bar.style[c.pct < 0 ? "right" : "left"] = "50%";
    bar.style.width = (49 * Math.abs(c.pct)) / max + "%";
    bar.style.background = c.pct < 0 ? "var(--loss)" : "var(--gain)";
    axis.append(bar);
    const num = document.createElement("span");
    num.className = "num " + tone(c.pct);
    num.textContent = fmt(c.pct);
    b.append(ticker, axis, num);
    b.onclick = () => choose(c.ticker);
    return b;
  });
  el("movers").replaceChildren(...buttons);
}
function choose(ticker) {
  if (!stock(ticker)) return;
  selected = ticker;
  renderPicker();
  remember();
  renderMetrics();
  renderWatch();
  mountChart();
}
function mount(id, type, config, link, attribution) {
  const host = el(id);
  if (host.cleanup) host.cleanup();
  host.classList.remove("fail");
  const embed = document.createElement("div");
  embed.className = "embed";
  const container = document.createElement("div");
  container.className = "tradingview-widget-container";
  const surface = document.createElement("div");
  surface.className = "tradingview-widget-container__widget";
  const foot = document.createElement("div");
  foot.className = "widget-foot";
  const a = document.createElement("a");
  a.href = link;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.textContent = attribution;
  const message = document.createElement("span");
  message.textContent = "Loading market data…";
  container.append(surface);
  embed.append(container);
  foot.append(a, message);
  host.replaceChildren(embed, foot);
  let timer = 0;
  const observer = new MutationObserver(() => {
    const frame =
      surface.querySelector("iframe") || container.querySelector("iframe");
    if (frame) {
      frame.title =
        id === "chart"
          ? stock(selected).name + " interactive price history"
          : "TradingView watchlist quotes";
      frame.addEventListener(
        "load",
        () => {
          if (container.isConnected) {
            clearTimeout(timer);
            message.textContent = "Timing varies by exchange";
          }
        },
        { once: true },
      );
      observer.disconnect();
    }
  });
  observer.observe(container, { childList: true, subtree: true });
  function fail() {
    if (!container.isConnected) return;
    observer.disconnect();
    clearTimeout(timer);
    host.classList.add("fail");
    embed.textContent =
      "Market data unavailable. Use the source link below or refresh to retry.";
    message.textContent = "Provider unavailable";
  }
  timer = setTimeout(() => {
    if (!container.querySelector("iframe")) {
      fail();
      return;
    }
    message.textContent =
      "Taking longer than usual. Open the source or refresh.";
  }, 20000);
  host.cleanup = () => {
    observer.disconnect();
    clearTimeout(timer);
  };
  const script = document.createElement("script");
  script.async = true;
  script.src =
    "https://s3.tradingview.com/external-embedding/embed-widget-" +
    type +
    ".js";
  script.textContent = JSON.stringify(config);
  script.onerror = fail;
  container.append(script);
}
const common = {
  width: "100%",
  height: "100%",
  colorTheme: "light",
  locale: "en",
  isTransparent: false,
  backgroundColor: "#f0f7ff",
};
function mountChart() {
  const c = stock(selected),
    s = c.exchange + ":" + c.ticker;
  mount(
    "chart",
    "symbol-overview",
    {
      ...common,
      colorTheme: "dark",
      backgroundColor: "#0b1f3b",
      symbols: [[c.name, s + "|1M"]],
      chartOnly: false,
      showVolume: false,
      showMA: false,
      hideDateRanges: false,
      hideMarketStatus: false,
      hideSymbolLogo: false,
      scalePosition: "right",
      scaleMode: "Normal",
      fontFamily: "system-ui, sans-serif",
      lineType: 0,
      chartType: "area",
      lineColor: "#60a5fa",
      topColor: "rgba(96,165,250,0.30)",
      bottomColor: "rgba(96,165,250,0.02)",
      dateRanges: ["1m|1D", "3m|1D", "6m|1D", "12m|1D"],
    },
    "https://www.tradingview.com/symbols/" + c.exchange + "-" + c.ticker + "/",
    c.ticker + " chart by TradingView",
  );
}
function renderWatch(force = false) {
  const q = el("search").value.trim().toLowerCase(),
    matches = groupList().filter((c) =>
      (c.name + " " + c.ticker).toLowerCase().includes(q),
    );
  const buttons = matches.map((c) => {
    const b = document.createElement("button");
    b.className = "stock";
    b.textContent = c.ticker;
    b.title = c.name;
    b.setAttribute("aria-label", c.name + " (" + c.ticker + ")");
    b.setAttribute("aria-pressed", String(c.ticker === selected));
    b.onclick = () => choose(c.ticker);
    return b;
  });
  if (!buttons.length) {
    const p = document.createElement("div");
    p.className = "empty";
    p.textContent = "No companies match.";
    const b = document.createElement("button");
    b.textContent = "Clear search";
    b.onclick = () => {
      el("search").value = "";
      renderWatch();
      el("search").focus();
    };
    p.append(b);
    buttons.push(p);
  }
  el("picks").replaceChildren(...buttons);
  const key = matches.map((c) => c.ticker).join(",");
  if (!force && key === quoteKey) return;
  quoteKey = key;
  el("quotes").hidden = !matches.length;
  if (!matches.length) {
    el("quotes").cleanup?.();
    el("quotes").replaceChildren();
    return;
  }
  mount(
    "quotes",
    "market-quotes",
    {
      ...common,
      showSymbolLogo: true,
      symbolsGroups: [
        {
          name: "AI equities",
          symbols: matches.map((c) => ({
            name: c.exchange + ":" + c.ticker,
            displayName: c.name,
          })),
        },
      ],
    },
    "https://www.tradingview.com/markets/stocks-usa/",
    "Market quotes by TradingView",
  );
}
async function loadMetrics() {
  const r = await fetch("./metrics.json", {
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  if (!r.ok) throw Error("Metrics unavailable");
  const m = await r.json();
  if (
    !dateOK(m.date) ||
    !dateOK(m.previousDate) ||
    m.date <= m.previousDate ||
    !m.changes ||
    !Object.keys(m.changes).some(
      (s) => stock(s) && Number.isFinite(m.changes[s]),
    )
  )
    throw Error("Invalid metrics");
  metrics = m;
  renderMetrics();
}
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  el("refresh").disabled = true;
  el("refresh").textContent = "Checking…";
  const last = metrics?.date;
  mountChart();
  renderWatch(true);
  try {
    await loadMetrics();
    el("status").textContent =
      last === metrics.date
        ? "Quote panels reloaded. Peer comparison is still dated " +
          dateLabel(last) +
          "."
        : "Peer comparison updated to " + dateLabel(metrics.date) + ".";
  } catch {
    el("status").textContent = metrics
      ? "Comparison update unavailable. Showing " +
        dateLabel(metrics.date) +
        "."
      : "Peer comparison unavailable. Refresh to retry.";
  } finally {
    el("refresh").disabled = false;
    el("refresh").textContent = "Refresh";
    refreshing = false;
  }
}
el("group").onchange = () => {
  renderPicker();
  remember();
  renderMetrics();
  renderWatch();
  mountChart();
};
el("company").onchange = () => choose(el("company").value);
el("search").oninput = () => renderWatch();
el("refresh").onclick = refresh;
renderPicker();
renderMetrics();
mountChart();
renderWatch();
loadMetrics().catch(() => {
  el("status").textContent = "Peer comparison unavailable. Refresh to retry.";
});

