// ---------------- ابزارهای پایه ----------------
const $ = (sel) => document.querySelector(sel);

async function api(path, opts = {}) {
  const init = { headers: {}, ...opts };
  if (init.body && typeof init.body === "object") {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(init.body);
  }
  const r = await fetch(path, init);
  let data = null;
  try { data = await r.json(); } catch (e) { /* ignore */ }
  if (!r.ok) {
    const msg = (data && (data.detail || data.message)) || "خطایی رخ داد";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function toast(msg, isErr = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => (t.className = "toast"), 3200);
}

const FA_NUM = (v) => String(v ?? "").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);
function faDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("fa-IR", { weekday: "short", month: "long", day: "numeric" }) +
    "، ساعت " + d.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
}
function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const STATUS_LABEL = {
  draft: "پیش‌نویس",
  ai_draft: "پیش‌نویس هوشمند — نیاز به تأیید",
  scheduled: "زمان‌بندی شده",
  ready: "آماده انتشار دستی",
  published: "منتشر شده",
  failed: "خطا در انتشار",
};

// ---------------- ناوبری ----------------
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => go(btn.dataset.view));
});
function go(view) {
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) =>
    v.classList.toggle("active", v.id === "view-" + view));
  if (view === "dashboard") loadState();
  if (view === "setup") loadSetup();
  if (view === "calendar") loadCalendar("");
  if (view === "news") loadNews();
  if (view === "analytics") loadAnalytics();
  if (view === "growth") { loadRecommendations(); loadTasks(); }
  if (view === "products") loadProducts();
  if (view === "settings") fillSettings();
  if (view === "create-post" || view === "create-story") { loadProductSelects(); applyPageMode(); }
}

let currentPageType = "shop";
async function applyPageMode() {
  try {
    const s = await api("/api/state");
    currentPageType = s.settings.page_type || "shop";
  } catch (e) { /* ignore */ }
  const isAI = currentPageType === "ai";
  const postShop = $("#shop-post-form"), postAI = $("#ai-post-form");
  const storyShop = $("#shop-story-form"), storyAI = $("#ai-story-form");
  if (postShop) postShop.style.display = isAI ? "none" : "";
  if (postAI) postAI.style.display = isAI ? "" : "none";
  if (storyShop) storyShop.style.display = isAI ? "none" : "";
  if (storyAI) storyAI.style.display = isAI ? "" : "none";
  if (isAI) aiTplChanged("post");
  if (isAI) aiTplChanged("story");
}

function aiTplChanged(kind) {
  const tpl = $("#ai-" + kind + "-tpl").value;
  const tool = $("#ai-" + kind + "-tool-extra");
  const extra = $("#ai-" + kind + "-extra");
  if (tool) tool.style.display = tpl === "tool" ? "" : "none";
  if (extra) extra.style.display = tpl === "comparison" ? "" : "none";
}

async function aiGenerate(kind) {
  const body = {
    kind,
    template: $("#ai-" + kind + "-tpl").value,
    title: $("#ai-" + kind + "-title").value,
    text: $("#ai-" + kind + "-text").value,
    price: $("#ai-" + kind + "-price") ? $("#ai-" + kind + "-price").value : "",
    use: $("#ai-" + kind + "-use") ? $("#ai-" + kind + "-use").value : "",
    a: $("#ai-" + kind + "-a") ? $("#ai-" + kind + "-a").value : "",
    b: $("#ai-" + kind + "-b") ? $("#ai-" + kind + "-b").value : "",
    verdict: $("#ai-" + kind + "-verdict") ? $("#ai-" + kind + "-verdict").value : "",
    scheduled_at: $("#ai-" + kind + "-schedule").value || null,
  };
  try {
    const r = await api("/api/ai/generate", { method: "POST", body });
    const p = r.post;
    $("#ai-" + kind + "-preview").innerHTML =
      `<img class="preview-img ${kind === "story" ? "story" : ""}" src="/generated/${p.image_path.split("/").pop()}">`;
    toast("🤖 محتوا ساخته شد" + (p.status === "scheduled" ? " و زمان‌بندی شد!" : " (پیش‌نویس)"));
    loadState();
  } catch (e) { toast(e.message, true); }
}

// ---------------- اخبار ----------------
const CATEGORY_BADGE_COLORS = {
  "سیاسی": "#fdeaea;color:#b91c1c",
  "اقتصادی": "#fef3c7;color:#b45309",
  "ورزشی": "#d9f7ec;color:#047857",
  "فناوری": "#e3e8ff;color:#4f46e5",
  "فرهنگی": "#fce7f3;color:#be185d",
  "حوادث": "#ffedd5;color:#c2410c",
  "عمومی": "#f1effa;color:#6d6a85",
};
function catBadge(cat) {
  const style = CATEGORY_BADGE_COLORS[cat] || CATEGORY_BADGE_COLORS["عمومی"];
  return `<span class="badge" style="${style}">${esc(cat)}</span>`;
}

async function loadNews() {
  try {
    const r = await api("/api/news");
    const news = r.news;
    const unused = news.filter((n) => !n.used).length;
    $("#news-cards").innerHTML = `
      <div class="card"><div class="num">${FA_NUM(r.count)}</div><div class="lbl">📰 کل اخبار آرشیو</div></div>
      <div class="card amber"><div class="num">${FA_NUM(unused)}</div><div class="lbl">🆕 خبر استفاده‌نشده</div></div>
      <div class="card"><div class="num">${FA_NUM(news.filter((n) => n.source).length)}</div><div class="lbl">🌐 از منابع مختلف</div></div>`;

    $("#news-list").innerHTML = news.length ? news.map(newsItem).join("") :
      '<div class="empty">هنوز خبری دریافت نشده. دکمه «🔄 دریافت اخبار» را بزن.</div>';
    loadNewsSources();
  } catch (e) { toast(e.message, true); }
}

function newsItem(n) {
  const breaking = (n.headline + " " + (n.summary || "")).match(/فوری|لحظاتی پیش|دقایقی پیش|breaking/i);
  const actions = [];
  if (!n.used) {
    actions.push(`<button class="btn small primary" onclick="newsToPost(${n.id})">🖼️ ساخت پست</button>`);
    actions.push(`<button class="btn small" onclick="newsToStory(${n.id})">📱 ساخت استوری</button>`);
  }
  if (n.link) actions.push(`<a class="btn small ghost" href="${esc(n.link)}" target="_blank">🔗 منبع</a>`);
  actions.push(`<button class="btn small danger" onclick="deleteNewsItem(${n.id})">🗑️</button>`);
  return `
    <div class="item news-item">
      <div class="grow">
        <div class="t">${breaking ? '<span class="badge" style="background:#dc2626;color:#fff">🔴 فوری</span> ' : ""}${esc(n.headline)}</div>
        ${n.summary ? `<div class="s news-summary">${esc(n.summary)}</div>` : ""}
        <div class="s">${catBadge(n.category)} · ${esc(n.source)} · ${n.published_at ? faDateTime(n.published_at.replace(" ", "T") + "+03:30") : "—"}
        ${n.used ? ' · <span class="badge published">استفاده شده</span>' : ' · <span class="badge ready">جدید</span>'}</div>
      </div>
      <div class="btn-row">${actions.join("")}</div>
    </div>`;
}

async function fetchNews() {
  try {
    const r = await api("/api/news/fetch", { method: "POST", body: {} });
    const extra = r.instant_stories ? ` — ⚡ ${FA_NUM(r.instant_stories)} استوری فوری ساخته شد!` : "";
    toast(`📰 دریافت شد: ${FA_NUM(r.fetched)} خبر بررسی، ${FA_NUM(r.new)} خبر جدید${extra}`);
    if (r.instant_stories) loadState();
    loadNews();
  } catch (e) {
    toast(e.message, true);
    loadNews();
  }
}

async function generateNewsToday() {
  try {
    const r = await api("/api/news/generate", { method: "POST", body: {} });
    toast(r.made ? `🤖 ${FA_NUM(r.made)} محتوای خبری ساخته و زمان‌بندی شد!` : "⚠️ خبر تازه‌ای برای ساخت محتوا نبود");
    loadState();
  } catch (e) { toast(e.message, true); }
}

function addManualNews() {
  openModal(`<h3>✍️ افزودن خبر دستی</h3>
    <label>تیتر خبر <input id="mn-headline"></label>
    <label>خلاصه (اختیاری) <textarea id="mn-summary" rows="3"></textarea></label>
    <div class="form-grid">
      <label>منبع <input id="mn-source" value="دستی"></label>
      <label>دسته
        <select id="mn-cat">
          <option value="هوش مصنوعی">هوش مصنوعی</option>
          <option value="سیاسی">سیاسی</option>
          <option value="اقتصادی">اقتصادی</option>
          <option value="ورزشی">ورزشی</option>
          <option value="فناوری">فناوری</option>
          <option value="فرهنگی">فرهنگی</option>
          <option value="حوادث">حوادث</option>
          <option value="عمومی" selected>عمومی</option>
        </select>
      </label>
    </div>
    <label>لینک خبر (اختیاری) <input id="mn-link" dir="ltr"></label>
    <div class="btn-row">
      <button class="btn primary" onclick="saveManualNews()">ذخیره</button>
      <button class="btn ghost" onclick="closeModal(event)">انصراف</button>
    </div>`);
}
async function saveManualNews() {
  try {
    const r = await api("/api/news/manual", {
      method: "POST",
      body: {
        headline: $("#mn-headline").value,
        summary: $("#mn-summary").value,
        source: $("#mn-source").value,
        category: $("#mn-cat").value,
        link: $("#mn-link").value,
      },
    });
    closeModal(); loadNews();
    if (r.instant_stories) { toast("⚡ خبر فوری! استوری فوری ساخته شد و ۱۰ دقیقه دیگر منتشر می‌شود"); loadState(); }
    else toast("📰 خبر ذخیره شد");
  } catch (e) { toast(e.message, true); }
}

async function _getNewsItem(id) {
  const r = await api("/api/news");
  return r.news.find((x) => x.id === id);
}

function newsTemplateModal(id, kind) {
  _getNewsItem(id).then((n) => {
    if (!n) { toast("خبر یافت نشد", true); return; }
    const stats = n.stats || [];
    const quotes = n.quotes || [];
    const autoTpl = quotes.length ? "quote" : (stats.length >= 2 ? "stats" : "standard");
    const labels = { standard: "📰 استاندارد — تیتر بزرگ + خلاصه", stats: "📊 آماری — کارت اعداد کلیدی خبر", quote: "💬 نقل‌قول — نمایش متن داخل گیومه", auto: "✨ خودکار (هوشمند)" };
    openModal(`<h3>${kind === "post" ? "🖼️ ساخت پست" : "📱 ساخت استوری"} خبری</h3>
      <div class="idea" style="cursor:default"><b>${esc(n.headline)}</b>
        ${n.summary ? `<div class="s" style="margin-top:6px">${esc(n.summary)}</div>` : ""}</div>
      <label style="margin-bottom:10px">قالب تصویر
        <select id="ntpl">
          <option value="auto">${labels.auto} → ${labels[autoTpl]}</option>
          <option value="standard">${labels.standard}</option>
          <option value="stats" ${stats.length >= 2 ? "" : "disabled"}>${labels.stats}${stats.length >= 2 ? "" : " (عددی در خبر نیست)"}</option>
          <option value="quote" ${quotes.length ? "" : "disabled"}>${labels.quote}${quotes.length ? "" : " (نقل‌قولی در خبر نیست)"}</option>
        </select>
      </label>
      <label>زمان انتشار (خالی = ${kind === "post" ? "پیش‌نویس برای تأیید" : "پیش‌نویس"})
        <input type="datetime-local" id="ntime">
      </label>
      <div class="btn-row">
        <button class="btn primary" onclick="confirmNewsCreate(${id}, '${kind}')">ساخت</button>
        <button class="btn ghost" onclick="closeModal(event)">انصراف</button>
      </div>`);
  }).catch((e) => toast(e.message, true));
}

async function newsToPost(id) { newsTemplateModal(id, "post"); }
async function newsToStory(id) { newsTemplateModal(id, "story"); }

async function confirmNewsCreate(id, kind) {
  try {
    const body = { template: $("#ntpl").value, scheduled_at: $("#ntime").value || null };
    const r = await api(`/api/news/${id}/${kind}`, { method: "POST", body });
    closeModal();
    if (kind === "post") toast("🖼️ پست خبری ساخته شد — در تقویم انتشار تأییدش کن");
    else toast("📱 استوری خبری ساخته شد");
    loadNews(); loadState();
  } catch (e) { toast(e.message, true); }
}
async function deleteNewsItem(id) {
  if (!confirm("این خبر حذف شود؟")) return;
  await api(`/api/news/${id}`, { method: "DELETE" });
  loadNews();
}

async function loadNewsSources() {
  try {
    const r = await api("/api/news/sources");
    $("#news-sources").innerHTML = r.sources.map((s) => `
      <div class="item">
        <div class="grow">
          <div class="t">${esc(s.name)} ${s.is_default ? '<span class="badge draft">پیش‌فرض</span>' : ""}</div>
          <div class="s" dir="ltr" style="text-align:right">${esc(s.url)}</div>
        </div>
        <label class="switch-row" style="margin:0">
          <input type="checkbox" ${s.enabled ? "checked" : ""} onchange="toggleSource(${s.id}, this.checked)">
        </label>
        <button class="btn small danger" onclick="deleteSource(${s.id})">🗑️</button>
      </div>`).join("");
  } catch (e) { /* ignore */ }
}
async function toggleSource(id, enabled) {
  await api(`/api/news/sources/${id}`, { method: "POST", body: { enabled: enabled ? 1 : 0 } });
}
async function deleteSource(id) {
  if (!confirm("منبع حذف شود؟")) return;
  await api(`/api/news/sources/${id}`, { method: "DELETE" });
  loadNewsSources();
}
async function addSource() {
  try {
    await api("/api/news/sources", {
      method: "POST",
      body: { name: $("#src-name").value, url: $("#src-url").value, category: $("#src-cat").value },
    });
    $("#src-name").value = $("#src-url").value = "";
    loadNewsSources(); toast("🌐 منبع اضافه شد");
  } catch (e) { toast(e.message, true); }
}

// ---------------- مودال ----------------
function openModal(html) {
  $("#modal-box").innerHTML = html;
  $("#modal-back").classList.add("open");
}
function closeModal(e) {
  if (!e || e.target === $("#modal-back")) $("#modal-back").classList.remove("open");
}

// ---------------- راه‌اندازی پیج ----------------
async function copyText(id) {
  const el = document.getElementById(id);
  if (!el) return;
  try {
    await navigator.clipboard.writeText(el.value);
    toast("📋 کپی شد");
  } catch (e) {
    el.select();
    document.execCommand("copy");
    toast("📋 کپی شد");
  }
}

async function loadSetup() {
  try {
    const s = await api("/api/setup");
    $("#setup-names").innerHTML = s.names.map((n) => `
      <div class="item copy-row">
        <div class="grow"><div class="t">${esc(n)}</div></div>
        <button class="btn small" onclick="copyPlain('${esc(n).replace(/'/g, "\\'")}')">📋</button>
      </div>`).join("");
    $("#setup-usernames").innerHTML = s.usernames.map((u) => `
      <div class="item copy-row">
        <div class="grow"><div class="t" dir="ltr" style="text-align:right">@${esc(u)}</div></div>
        <button class="btn small" onclick="copyPlain('${esc(u)}')">📋</button>
      </div>`).join("");
    $("#setup-bio").value = s.bio;
    $("#setup-highlights").innerHTML = s.assets.highlights.map((h) => `
      <div class="brand-card">
        <img src="${h.url}" alt="${esc(h.label)}">
        <div class="s">${esc(h.label)}</div>
        <a class="btn small" href="${h.url}" download>⬇️ دانلود</a>
      </div>`).join("");

    // چک‌لیست با ذخیره محلی
    const done = JSON.parse(localStorage.getItem("setup_steps") || "{}");
    $("#setup-steps").innerHTML = s.steps.map((st, i) => `
      <div class="task ${done[i] ? "done" : ""}">
        <input type="checkbox" ${done[i] ? "checked" : ""} onchange="toggleSetupStep(${i}, this.checked)">
        <div><b>${esc(st[0])}</b><div class="s">${esc(st[1])}</div></div>
      </div>`).join("");
  } catch (e) { toast(e.message, true); }
}

function copyPlain(text) {
  const tmp = document.createElement("textarea");
  tmp.value = text;
  document.body.appendChild(tmp);
  tmp.select();
  try { document.execCommand("copy"); toast("📋 کپی شد"); } catch (e) { toast("کپی ناموفق", true); }
  tmp.remove();
}

function toggleSetupStep(i, checked) {
  const done = JSON.parse(localStorage.getItem("setup_steps") || "{}");
  done[i] = checked;
  localStorage.setItem("setup_steps", JSON.stringify(done));
  loadSetup();
}

// ---------------- داشبورد ----------------
async function loadState() {
  try {
    const s = await api("/api/state");
    const apiOk = s.api_configured;
    $("#api-badge").textContent = apiOk ? "🔗 متصل به اینستاگرام" : "🔌 بدون اتصال API";
    $("#api-badge").style.color = apiOk ? "#7ef0c0" : "#fcd34d";

    const c = s.counts;
    $("#dash-cards").innerHTML = `
      <div class="card"><div class="num">${FA_NUM(c.scheduled)}</div><div class="lbl">⏳ زمان‌بندی شده</div></div>
      <div class="card amber"><div class="num">${FA_NUM(c.ai_drafts)}</div><div class="lbl">🤖 پیش‌نویس هوشمند (تأیید کن)</div></div>
      <div class="card green"><div class="num">${FA_NUM(c.published)}</div><div class="lbl">✅ منتشر شده</div></div>
      <div class="card"><div class="num">${FA_NUM(c.ready)}</div><div class="lbl">📦 آماده انتشار دستی</div></div>
      <div class="card"><div class="num">${FA_NUM(c.products)}</div><div class="lbl">🛍️ محصول</div></div>
      <div class="card"><div class="num">${FA_NUM(s.news_count)}</div><div class="lbl">📰 خبر در آرشیو</div></div>`;

    $("#dash-upcoming").innerHTML = s.upcoming.length ? s.upcoming.map(upcomingItem).join("") :
      '<div class="empty">چیزی در صف نیست. از «ساخت پست» شروع کن 🚀</div>';

    $("#dash-activity").innerHTML = s.activity.length ? s.activity.map((a) =>
      `<div class="activity">${faDateTime(String(a.ts).replace(" ", "T") + "Z").split("،")[0]} — ${esc(a.message)}</div>`).join("")
      : '<div class="empty">فعلاً فعالیتی ثبت نشده</div>';

    // پیش‌نویس‌های هوشمند
    const drafts = s.upcoming.filter((p) => p.status === "ai_draft");
    if (drafts.length) toast(`🤖 ${FA_NUM(drafts.length)} پیش‌نویس هوشمند منتظر تأیید توست!`);
  } catch (e) {
    toast(e.message, true);
  }
}

function upcomingItem(p) {
  const isStory = p.kind === "story";
  const actions = [];
  if (p.status === "ai_draft") {
    actions.push(`<button class="btn small green" onclick="approvePost(${p.id})">👍 تأیید و زمان‌بندی</button>`);
  }
  if (p.status === "ready") {
    actions.push(`<button class="btn small primary" onclick="publishNow(${p.id})">🚀 انتشار</button>`);
    actions.push(`<button class="btn small green" onclick="markPublished(${p.id})">✅ دستی منتشر کردم</button>`);
  }
  if (p.status === "scheduled") {
    actions.push(`<button class="btn small primary" onclick="publishNow(${p.id})">🚀 انتشار الان</button>`);
  }
  actions.push(`<button class="btn small ghost" onclick="downloadPackage(${p.id})">⬇️ بسته</button>`);
  return `
    <div class="item">
      <img class="thumb ${isStory ? "story" : ""}" src="${p.image_path ? "/generated/" + p.image_path.split("/").pop() : ""}" onerror="this.style.visibility='hidden'">
      <div class="grow">
        <div class="t">${isStory ? "📱" : "🖼️"} ${esc(p.title)}</div>
        <div class="s">${faDateTime(p.scheduled_at)} · <span class="badge ${p.status}">${STATUS_LABEL[p.status] || p.status}</span></div>
      </div>
      <div class="btn-row">${actions.join("")}</div>
    </div>`;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (m) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

// ---------------- ساخت پست و استوری ----------------
async function loadProductSelects() {
  const prods = (await api("/api/products")).products;
  const opts = '<option value="">— بدون محصول / دستی —</option>' +
    prods.map((p) => `<option value="${p.id}">${esc(p.name)} ${p.price ? "(" + FA_NUM(p.price) + " تومان)" : ""}</option>`).join("");
  $("#post-product").innerHTML = opts;
  $("#story-product").innerHTML = opts;
}

async function generatePost() {
  const body = {
    kind: "post",
    template: $("#post-template").value,
    product_id: $("#post-product").value || null,
    title: $("#post-title").value,
    text: $("#post-text").value,
    price: $("#post-price").value,
    old_price: $("#post-oldprice").value,
    caption: $("#post-caption").value,
    hashtags: $("#post-hashtags").value,
    scheduled_at: $("#post-schedule").value || null,
  };
  try {
    const r = await api("/api/posts/generate", { method: "POST", body });
    const p = r.post;
    $("#post-preview").innerHTML = `<img class="preview-img" src="/generated/${p.image_path.split("/").pop()}">`;
    toast("🎨 پست ساخته شد" + (p.status === "scheduled" ? " و زمان‌بندی شد!" : " (پیش‌نویس)"));
    loadState();
  } catch (e) { toast(e.message, true); }
}

async function generateStory() {
  const body = {
    kind: "story",
    template: $("#story-template").value,
    product_id: $("#story-product").value || null,
    title: $("#story-title").value,
    text: $("#story-title").value,
    extra: $("#story-extra").value,
    price: $("#story-price").value,
    caption: $("#story-caption").value,
    scheduled_at: $("#story-schedule").value || null,
  };
  try {
    const r = await api("/api/posts/generate", { method: "POST", body });
    const p = r.post;
    $("#story-preview").innerHTML = `<img class="preview-img story" src="/generated/${p.image_path.split("/").pop()}">`;
    toast("📱 استوری ساخته شد" + (p.status === "scheduled" ? " و زمان‌بندی شد!" : " (پیش‌نویس)"));
    loadState();
  } catch (e) { toast(e.message, true); }
}

async function ideasForPost() {
  try {
    const r = await api("/api/content/ideas", {
      method: "POST",
      body: {
        product_id: $("#post-product").value || null,
        title: $("#post-title").value,
        text: $("#post-text").value,
        price: $("#post-price").value,
      },
    });
    openModal(`<h3>✨ سه پیشنهاد کپشن برای این پست</h3>
      ${r.ideas.map((idea, i) => `
        <div class="idea" onclick="applyIdea(${i})">
          <b>پیشنهاد ${FA_NUM(i + 1)}</b>
          <pre>${esc(idea.caption)}</pre>
        </div>`).join("")}
      <div class="btn-row"><button class="btn ghost" onclick="closeModal(event)">بستن</button></div>`);
    window._ideas = r.ideas;
  } catch (e) { toast(e.message, true); }
}
function applyIdea(i) {
  const idea = window._ideas[i];
  if (!idea) return;
  const caption = idea.caption.replace(/\n#[^\n]*$/s, "").trim();
  const tags = (idea.hashtags || "").trim();
  $("#post-caption").value = caption;
  $("#post-hashtags").value = tags;
  closeModal();
  toast("✅ کپشن پیشنهادی اعمال شد");
}

// ---------------- تقویم ----------------
let calendarFilterVal = "";
async function loadCalendar(filter) {
  if (filter !== undefined) calendarFilterVal = filter;
  try {
    const r = await api("/api/posts?status=" + calendarFilterVal);
    const posts = r.posts;
    $("#calendar-list").innerHTML = posts.length
      ? posts.map(calendarItem).join("")
      : '<div class="empty">موردی پیدا نشد</div>';
  } catch (e) { toast(e.message, true); }
}
function calendarFilter(f) { loadCalendar(f); }

function calendarItem(p) {
  const isStory = p.kind === "story";
  const actions = [];
  if (p.status === "ai_draft")
    actions.push(`<button class="btn small green" onclick="approvePost(${p.id})">👍 تأیید</button>`);
  if (p.status === "scheduled")
    actions.push(`<button class="btn small primary" onclick="publishNow(${p.id})">🚀 انتشار الان</button>`);
  if (p.status === "ready") {
    actions.push(`<button class="btn small primary" onclick="publishNow(${p.id})">🚀 انتشار</button>`);
    actions.push(`<button class="btn small green" onclick="markPublished(${p.id})">✅ دستی منتشر شد</button>`);
  }
  if (p.status === "failed")
    actions.push(`<button class="btn small primary" onclick="publishNow(${p.id})">🔁 تلاش مجدد</button>`);
  actions.push(`<button class="btn small ghost" onclick="rescheduleModal(${p.id})">🕓 زمان</button>`);
  actions.push(`<button class="btn small ghost" onclick="viewPost(${p.id})">👁️</button>`);
  actions.push(`<button class="btn small ghost" onclick="downloadPackage(${p.id})">⬇️</button>`);
  actions.push(`<button class="btn small danger" onclick="deletePost(${p.id})">🗑️</button>`);
  return `
    <div class="item">
      <img class="thumb ${isStory ? "story" : ""}" src="/generated/${p.image_path.split("/").pop()}" onerror="this.style.visibility='hidden'">
      <div class="grow">
        <div class="t">${isStory ? "📱" : "🖼️"} ${esc(p.title)}</div>
        <div class="s">${faDateTime(p.scheduled_at)} · ${p.permalink ? `<a href="${p.permalink}" target="_blank">مشاهده در اینستاگرام</a> · ` : ""}<span class="badge ${p.status}">${STATUS_LABEL[p.status] || p.status}</span>
        ${p.error ? `<br><span style="color:#b91c1c">${esc(p.error)}</span>` : ""}</div>
      </div>
      <div class="btn-row">${actions.join("")}</div>
    </div>`;
}

async function approvePost(id) {
  try {
    const at = await api("/api/posts/" + id, { method: "POST", body: {} });
    await api(`/api/posts/${id}/approve`, { method: "POST", body: { scheduled_at: at.post.scheduled_at } });
    toast("👍 پیش‌نویس تأیید و زمان‌بندی شد");
    loadCalendar(); loadState();
  } catch (e) { toast(e.message, true); }
}
async function publishNow(id) {
  try {
    await api(`/api/posts/${id}/publish`, { method: "POST", body: {} });
    toast("🚀 در حال انتشار روی اینستاگرام...");
    setTimeout(() => { loadCalendar(); loadState(); }, 4000);
  } catch (e) { toast(e.message, true); }
}
async function markPublished(id) {
  await api(`/api/posts/${id}/mark_published`, { method: "POST", body: {} });
  toast("✅ ثبت شد");
  loadCalendar(); loadState();
}
async function deletePost(id) {
  if (!confirm("این مورد حذف شود؟")) return;
  await api(`/api/posts/${id}`, { method: "DELETE" });
  toast("🗑️ حذف شد");
  loadCalendar(); loadState();
}
function downloadPackage(id) {
  window.open(`/api/posts/${id}/package`, "_blank");
}
function rescheduleModal(id) {
  openModal(`<h3>🕓 زمان جدید انتشار</h3>
    <input type="datetime-local" id="resched-input">
    <div class="btn-row">
      <button class="btn primary" onclick="doReschedule(${id})">ذخیره</button>
      <button class="btn ghost" onclick="closeModal(event)">انصراف</button>
    </div>`);
  api("/api/posts/" + id).then((r) => {
    const inp = $("#resched-input");
    if (inp) inp.value = toLocalInput(r.post.scheduled_at);
  }).catch(() => { /* ignore */ });
}
async function doReschedule(id) {
  try {
    const val = $("#resched-input").value;
    await api(`/api/posts/${id}/schedule`, { method: "POST", body: { scheduled_at: val || null } });
    closeModal(); loadCalendar(); loadState(); toast("🕓 زمان به‌روزرسانی شد");
  } catch (e) { toast(e.message, true); }
}
async function viewPost(id) {
  try {
    const r = await api("/api/posts");
    const p = r.posts.find((x) => x.id === id);
    openModal(`<h3>👁️ پیش‌نمایش — ${esc(p ? p.title : "")}</h3>
      ${p ? `<img src="/generated/${p.image_path.split("/").pop()}" onerror="this.alt='تصویر یافت نشد'">` : '<div class="empty">یافت نشد</div>'}
      <div class="btn-row"><button class="btn ghost" onclick="closeModal(event)">بستن</button></div>`);
  } catch (e) { toast(e.message, true); }
}

// ---------------- آنالیز ----------------
async function loadAnalytics() {
  try {
    const r = await api("/api/analytics");
    const m = r.metrics;
    const last = m[m.length - 1];
    const first = m[0];
    const followers = last ? last.followers : 0;
    const growth = m.length > 1 && first.followers ? ((last.followers - first.followers) / first.followers * 100) : 0;
    const reach = last ? (last.reach || 0) : 0;
    const views = last ? (last.profile_views || 0) : 0;
    const demo = m.length && m[0].source === "demo";

    $("#analytics-cards").innerHTML = `
      <div class="card"><div class="num">${FA_NUM(followers)}</div><div class="lbl">👥 فالوور فعلی</div></div>
      <div class="card ${growth >= 0 ? "green" : "red"}"><div class="num">${growth >= 0 ? "+" : ""}${FA_NUM(growth.toFixed(1))}٪</div><div class="lbl">📈 رشد دوره</div></div>
      <div class="card"><div class="num">${FA_NUM(reach)}</div><div class="lbl">👁️ ریچ (دسترسی)</div></div>
      <div class="card"><div class="num">${FA_NUM(views)}</div><div class="lbl">👀 بازدید پروفایل</div></div>`;

    $("#analytics-hint").innerHTML = r.use_api
      ? "💡 اینسایت به‌صورت خودکار هر شب ساعت ۲۳:۴۵ ذخیره می‌شود؛ با دکمه بالا می‌توانی الان هم دریافت کنی."
      : (demo
        ? "⚠️ این داده‌ها <b>نمونه</b> هستند تا شکل نمودار را ببینی. برای داده واقعی: اتصال API را در تنظیمات برقرار کن یا آمار را دستی ثبت کن، بعد داده‌های نمونه را پاک کن."
        : "✍️ هنوز داده‌ای ثبت نشده. آمار امروز را دستی ثبت کن یا API را در تنظیمات وصل کن.");

    drawLineChart($("#chart-followers"), m.map((x) => x.followers || 0), "#7c3aed", m.map((x) => x.date.slice(5)));
    drawBarChart($("#chart-reach"), m.map((x) => x.reach || 0), "#4f46e5", m.map((x) => x.date.slice(5)));
  } catch (e) { toast(e.message, true); }
}

async function fetchInsights() {
  try {
    const r = await api("/api/analytics/fetch", { method: "POST", body: {} });
    toast("📊 اینسایت دریافت شد — فالوور: " + FA_NUM(r.summary.followers_count));
    loadAnalytics();
  } catch (e) { toast(e.message, true); }
}

function openManualMetric() {
  openModal(`<h3>✍️ ثبت دستی آمار امروز</h3>
    <div class="form-grid">
      <label>تعداد فالوور <input id="mm-followers" type="number"></label>
      <label>تعداد دنبال‌شونده <input id="mm-following" type="number"></label>
      <label>تعداد پست‌ها <input id="mm-media" type="number"></label>
      <label>ریچ امروز <input id="mm-reach" type="number"></label>
      <label>ایمپرشن امروز <input id="mm-imp" type="number"></label>
      <label>بازدید پروفایل <input id="mm-views" type="number"></label>
    </div>
    <div class="btn-row">
      <button class="btn primary" onclick="saveManualMetric()">ذخیره</button>
      <button class="btn ghost" onclick="closeModal(event)">انصراف</button>
    </div>`);
}
async function saveManualMetric() {
  try {
    await api("/api/analytics/manual", {
      method: "POST",
      body: {
        followers: $("#mm-followers").value, following: $("#mm-following").value,
        media_count: $("#mm-media").value, reach: $("#mm-reach").value,
        impressions: $("#mm-imp").value, profile_views: $("#mm-views").value,
      },
    });
    closeModal(); loadAnalytics(); toast("✅ آمار ثبت شد");
  } catch (e) { toast(e.message, true); }
}
async function resetAnalytics() {
  if (!confirm("همه داده‌های آماری (از جمله داده نمونه) پاک شود؟")) return;
  await api("/api/analytics/reset", { method: "POST", body: {} });
  loadAnalytics(); toast("🗑️ داده‌های آماری پاک شد");
}

// ---------------- نمودارهای SVG ----------------
function drawLineChart(svg, values, color, labels) {
  const W = 800, H = 300, pad = 34;
  const maxV = Math.max(...values, 1) * 1.15;
  const minV = Math.min(...values, 0) * 0.85;
  const stepX = values.length > 1 ? (W - pad * 2) / (values.length - 1) : 0;
  const y = (v) => pad + (H - pad * 2) * (1 - (v - minV) / (maxV - minV || 1));
  let grid = "", line = "", area = `M${pad},${y(values[0])}`;
  values.forEach((v, i) => {
    const x = pad + i * stepX;
    grid += `<line x1="${x}" y1="${pad}" x2="${x}" y2="${H - pad}" stroke="#eee" stroke-width="1"/>`;
    line += (i ? " L" : "M") + x + "," + y(v);
    area += (i ? " L" : " L") + x + "," + y(v);
  });
  area += ` L${pad + (values.length - 1) * stepX},${H - pad} L${pad},${H - pad} Z`;
  const lastX = pad + (values.length - 1) * stepX;
  const lastY = y(values[values.length - 1]);
  svg.innerHTML = `
    ${grid}
    <path d="${area}" fill="${color}" opacity="0.12"/>
    <path d="${line}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round"/>
    <circle cx="${lastX}" cy="${lastY}" r="6" fill="${color}" stroke="#fff" stroke-width="3"/>
    <text x="${lastX}" y="${lastY - 14}" text-anchor="middle" font-size="13" font-weight="bold" fill="${color}" font-family="Vazirmatn">${FA_NUM(values[values.length - 1])}</text>
    <text x="${pad}" y="${H - 6}" font-size="11" fill="#999" font-family="Vazirmatn">${labels[0] || ""}</text>
    <text x="${lastX}" y="${H - 6}" text-anchor="end" font-size="11" fill="#999" font-family="Vazirmatn">${labels[labels.length - 1] || ""}</text>`;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
}

function drawBarChart(svg, values, color, labels) {
  const W = 800, H = 240, pad = 30;
  const maxV = Math.max(...values, 1) * 1.15;
  const bw = (W - pad * 2) / Math.max(values.length, 1);
  let bars = "";
  values.forEach((v, i) => {
    const h = (v / maxV) * (H - pad * 2 - 20);
    const x = pad + i * bw + bw * 0.18;
    bars += `<rect x="${x}" y="${H - pad - h}" width="${bw * 0.64}" height="${h}" rx="6" fill="${color}" opacity="${0.55 + 0.45 * (v / maxV)}"/>
             <text x="${x + bw * 0.32}" y="${H - pad - h - 6}" text-anchor="middle" font-size="10" fill="#888" font-family="Vazirmatn">${FA_NUM(v)}</text>`;
  });
  svg.innerHTML = bars;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
}

// ---------------- رشد پیج ----------------
async function loadRecommendations() {
  try {
    const r = await api("/api/recommendations");
    $("#recommendations").innerHTML = r.recommendations.map((rec) => `
      <div class="rec ${rec.priority}">
        <div class="ricon">${rec.icon}</div>
        <div><div class="rtitle">${esc(rec.title)}</div><div class="rtext">${esc(rec.text)}</div></div>
      </div>`).join("");
  } catch (e) { toast(e.message, true); }
}
async function loadTasks() {
  const s = await api("/api/state");
  $("#task-list").innerHTML = s.tasks.map((t) => `
    <div class="task ${t.done ? "done" : ""}">
      <input type="checkbox" ${t.done ? "checked" : ""} onchange="toggleTask(${t.id})">
      <span>${esc(t.text)}</span>
      <button class="del" onclick="delTask(${t.id})">✕</button>
    </div>`).join("");
}
async function addTask() {
  const inp = $("#new-task");
  if (!inp.value.trim()) return;
  await api("/api/tasks", { method: "POST", body: { text: inp.value.trim() } });
  inp.value = "";
  loadTasks();
}
async function toggleTask(id) {
  await api(`/api/tasks/${id}/toggle`, { method: "POST", body: {} });
  loadTasks();
}
async function delTask(id) {
  await api(`/api/tasks/${id}`, { method: "DELETE" });
  loadTasks();
}
async function loadReport() {
  const r = await api("/api/report");
  $("#report-text").textContent = r.report;
}

// ---------------- محصولات ----------------
let productImagePath = "";
async function loadProducts() {
  const r = await api("/api/products");
  $("#products-grid").innerHTML = r.products.length ? r.products.map((p) => `
    <div class="product-card">
      ${p.image_path ? `<img src="/uploads/${p.image_path.split("/").pop()}" onerror="this.style.visibility='hidden'">` : `<div style="height:100px;display:flex;align-items:center;justify-content:center;font-size:42px;background:#f2f1fa">${p.emoji}</div>`}
      <div class="pbody">
        <div class="pname">${esc(p.name)}</div>
        ${p.price ? `<div class="pprice">${FA_NUM(p.price)} تومان</div>` : ""}
        <div class="pdesc">${esc(p.description)}</div>
        <div class="pactions">
          <button class="btn small" onclick="editProduct(${p.id})">✏️ ویرایش</button>
          <button class="btn small danger" onclick="deleteProduct(${p.id})">🗑️</button>
        </div>
      </div>
    </div>`).join("") : '<div class="empty">هنوز محصولی نداری. فرم بالا را پر کن.</div>';
}

$("#prod-file").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  const data = await r.json();
  productImagePath = data.path;
  $("#prod-file-hint").textContent = "✅ عکس آپلود شد: " + f.name;
});

async function saveProduct() {
  const body = {
    name: $("#prod-name").value,
    price: $("#prod-price").value,
    description: $("#prod-desc").value,
    emoji: $("#prod-emoji").value || "🛍️",
    image_path: productImagePath,
  };
  const id = $("#prod-id").value;
  try {
    if (id) await api(`/api/products/${id}`, { method: "POST", body });
    else await api("/api/products", { method: "POST", body });
    toast("💾 محصول ذخیره شد");
    clearProductForm();
    loadProducts();
  } catch (e) { toast(e.message, true); }
}
async function editProduct(id) {
  const r = await api("/api/products");
  const p = r.products.find((x) => x.id === id);
  if (!p) return;
  $("#prod-id").value = p.id;
  $("#prod-name").value = p.name;
  $("#prod-price").value = p.price;
  $("#prod-desc").value = p.description;
  $("#prod-emoji").value = p.emoji;
  productImagePath = p.image_path;
  $("#prod-file-hint").textContent = p.image_path ? "عکس فعلی نگه داشته می‌شود؛ با انتخاب فایل جدید عوض می‌شود" : "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function clearProductForm() {
  $("#prod-id").value = "";
  $("#prod-name").value = $("#prod-price").value = $("#prod-desc").value = "";
  $("#prod-emoji").value = "🛍️";
  $("#prod-file").value = "";
  $("#prod-file-hint").textContent = "";
  productImagePath = "";
}
async function deleteProduct(id) {
  if (!confirm("محصول حذف شود؟")) return;
  await api(`/api/products/${id}`, { method: "DELETE" });
  loadProducts(); toast("🗑️ محصول حذف شد");
}

// ---------------- تنظیمات ----------------
async function fillSettings() {
  const s = (await api("/api/state")).settings;
  $("#set-name").value = s.shop_name || "";
  $("#set-handle").value = s.shop_handle || "";
  $("#set-tagline").value = s.shop_tagline || "";
  $("#set-phone").value = s.shop_phone || "";
  $("#set-cta").value = s.cta || "";
  $("#set-color1").value = s.color1 || "#7C3AED";
  $("#set-color2").value = s.color2 || "#4F46E5";
  $("#set-accent").value = s.accent || "#FBBF24";
  $("#set-posttime").value = s.post_time || "20:00";
  $("#set-storytime").value = s.story_time || "12:00";
  $("#set-storytime2").value = s.story_time_2 || "21:00";
  $("#set-auto-post").checked = s.auto_generate_posts === "1";
  $("#set-auto-story").checked = s.auto_publish_stories === "1";
  $("#set-news-fetch").checked = s.news_auto_fetch === "1";
  $("#set-news-instant").checked = s.news_breaking_instant === "1";
  $("#set-pagetype").value = s.page_type === "news" ? "news" : "shop";
  $("#set-token").value = s.ig_access_token || "";
  $("#set-igid").value = s.ig_user_id || "";
  $("#set-baseurl").value = s.public_base_url || "";

  const ok = !!(s.ig_access_token && s.ig_user_id);
  $("#ig-status").className = "ig-status " + (ok ? "ok" : "no");
  $("#ig-status").innerHTML = ok
    ? "✅ اتصال برقرار است — انتشار خودکار و آنالیز فعال است."
    : "⚠️ هنوز متصل نیستی. با راهنمای پایین، دسترسی متا را بساز و توکن را وارد کن.";

  $("#guide-body").innerHTML = GUIDE_HTML;
}

async function saveSettings() {
  const body = {
    shop_name: $("#set-name").value,
    shop_handle: $("#set-handle").value,
    shop_tagline: $("#set-tagline").value,
    shop_phone: $("#set-phone").value,
    cta: $("#set-cta").value,
    color1: $("#set-color1").value,
    color2: $("#set-color2").value,
    accent: $("#set-accent").value,
    post_time: $("#set-posttime").value,
    story_time: $("#set-storytime").value,
    story_time_2: $("#set-storytime2").value,
    auto_generate_posts: $("#set-auto-post").checked ? "1" : "0",
    auto_publish_stories: $("#set-auto-story").checked ? "1" : "0",
    news_auto_fetch: $("#set-news-fetch").checked ? "1" : "0",
    news_breaking_instant: $("#set-news-instant").checked ? "1" : "0",
    page_type: $("#set-pagetype").value || "shop",
    ig_access_token: $("#set-token").value.trim(),
    ig_user_id: $("#set-igid").value.trim(),
    public_base_url: $("#set-baseurl").value.trim(),
  };
  try {
    await api("/api/settings", { method: "POST", body });
    toast("💾 تنظیمات ذخیره شد");
    fillSettings(); loadState();
  } catch (e) { toast(e.message, true); }
}

async function testIG() {
  try {
    const r = await api("/api/ig/test", {
      method: "POST",
      body: { access_token: $("#set-token").value.trim(), ig_user_id: $("#set-igid").value.trim() },
    });
    toast("🎉 اتصال برقرار شد! پیج: @" + r.info.username);
    fillSettings(); loadState();
  } catch (e) { toast(e.message, true); }
}

async function discoverIG() {
  try {
    const r = await api("/api/ig/discover", {
      method: "POST", body: { access_token: $("#set-token").value.trim() },
    });
    $("#ig-discover-list").innerHTML = r.accounts.map((a) => `
      <div class="item"><div class="grow">
        <div class="t">${esc(a.page_name)}</div>
        <div class="s" dir="ltr">IG: ${a.ig_id}</div>
      </div>
      <button class="btn small primary" onclick="selectIG('${a.ig_id}')">استفاده از این اکانت</button></div>`).join("");
  } catch (e) { toast(e.message, true); }
}
function selectIG(igId) {
  $("#set-igid").value = igId;
  toast("✅ شناسه اکانت پر شد — حالا «تست و ذخیره اتصال» را بزن");
}

async function checkPublic() {
  const r = await api("/api/ig/check_public", { method: "POST", body: {} });
  toast(r.message, !r.ok);
}

// ---------------- راهنمای API ----------------
const GUIDE_HTML = `
<ol>
  <li><b>تبدیل اکانت به بیزینس/کریتور:</b> در اپلیکیشن اینستاگرام: تنظیمات ← نوع حساب ← «حساب حرفه‌ای» را انتخاب کن و دسته کسب‌وکارت را مشخص کن.</li>
  <li><b>اتصال به فیسبوک‌پیج:</b> در تنظیمات اینستاگرام ← حساب ← «صفحه‌های فیسبوک متصل»، یک پیج انتخاب/ایجاد کن. (برای پیج فروشگاهت یک فیسبوک‌پیج ساده بساز.)</li>
  <li><b>ساخت اپ متا:</b> وارد <code>developers.facebook.com</code> شو ← «My Apps» ← «Create App» ← نوع <b>Business</b> ← نام دلخواه.</li>
  <li><b>افزودن محصول:</b> در داشبورد اپ ← «Add Product» ← <b>Instagram</b> را اضافه کن (با Facebook Login).</li>
  <li><b>گرفتن توکن:</b> در <code>developers.facebook.com/tools/explorer</code>:
    <ul>
      <li>اپ خودت را از منوی بالا انتخاب کن</li>
      <li>از منوی «User or Page» گزینه <b>Instagram Graph API</b> (یا صفحه‌ی متصل) را انتخاب کن</li>
      <li>پرمیشن‌های <code>instagram_basic</code>، <code>instagram_content_publish</code> و <code>instagram_manage_insights</code> و <code>pages_show_list</code> را اضافه کن</li>
      <li>دکمه <b>Generate Access Token</b> را بزن و توکن را کپی کن</li>
    </ul>
  </li>
  <li><b>پیدا کردن شناسه اکانت:</b> توکن را در کادر بالا بچسبان و دکمه «🔍 پیدا کردن خودکار اکانت» را بزن؛ سیستم شناسه <code>1784...</code> را برایت پیدا می‌کند. سپس «تست و ذخیره» را بزن.</li>
  <li><b>توکن بلندمدت:</b> توکن اکسپلورر کوتاه‌مدت است. برای تبدیل به ۶۰ روزه: در تنظیمات اپ ← Roles، «Test Users» یا حالت توسعه را طبق مستندات متا فعال کن، یا توکن را هر چند وقت یک‌بار تازه کن.</li>
</ol>
<h3>نکات مهم</h3>
<ul>
  <li>برای انتشار خودکار، سرور باید از اینترنت قابل دسترسی باشد (تصویر پست باید URL عمومی داشته باشد). اگر سرورت عمومی نیست، از دکمه «⬇️ بسته» استفاده کن و دستی منتشر کن.</li>
  <li>محدودیت API اینستاگرام: حداکثر ۲۵ پست در روز از طریق API.</li>
  <li>استوری‌های API بدون استیکر/لینک هستند؛ برای استوری کامل‌تر، تصویر را دانلود و دستی با استیکر منتشر کن.</li>
  <li>اگر به فیسبوک/متا دسترسی نداری (تحریم/فیلتر)، از حالت «آماده انتشار دستی» استفاده کن — همه محتوا و زمان‌بندی سر جای خودش است.</li>
</ul>`;

// ---------------- شروع ----------------
loadState();
loadProductSelects();
applyPageMode();
