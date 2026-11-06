const COLORS = { positive: "#22c55e", neutral: "#94a3b8", negative: "#ef4444" };
Chart.defaults.color = "#8b94a3"; Chart.defaults.borderColor = "#262c36";
const charts = {};
let page = 1;

function upsert(id, config) {
  if (charts[id]) { charts[id].data = config.data; charts[id].update(); }
  else charts[id] = new Chart(document.getElementById(id), config);
}

async function loadStats() {
  const s = await api("/api/stats");
  kTotal.textContent = s.total;
  kRating.textContent = s.avg_rating;
  kScore.textContent = s.avg_sentiment;
  kPos.textContent = s.total ? Math.round(s.by_sentiment.positive / s.total * 100) + "%" : "0%";

  upsert("sentChart", { type: "doughnut", data: {
    labels: Object.keys(s.by_sentiment),
    datasets: [{ data: Object.values(s.by_sentiment), backgroundColor: Object.keys(s.by_sentiment).map(k => COLORS[k]) }] } });
  upsert("ratingChart", { type: "bar", data: {
    labels: Object.keys(s.by_rating).map(r => r + "★"),
    datasets: [{ label: "Count", data: Object.values(s.by_rating), backgroundColor: "#f5a524" }] },
    options: { plugins: { legend: { display: false } } } });
  upsert("catChart", { type: "polarArea", data: {
    labels: Object.keys(s.by_category),
    datasets: [{ data: Object.values(s.by_category),
      backgroundColor: ["#f5a52499", "#3b82f699", "#22c55e99", "#ef444499", "#a3a3a399"] }] } });
  upsert("trendChart", { type: "line", data: { labels: s.trend.labels,
    datasets: ["positive", "neutral", "negative"].map(k => ({ label: k, tension: .3,
      data: s.trend.sentiment.map(d => d[k]), borderColor: COLORS[k], backgroundColor: COLORS[k] })) } });
}

async function loadTable() {
  const params = new URLSearchParams({ page, per_page: 10 });
  if (search.value) params.set("q", search.value);
  if (filterSent.value) params.set("sentiment", filterSent.value);
  const r = await api("/api/feedback?" + params);
  fbBody.innerHTML = r.items.map(f => `<tr>
    <td>${new Date(f.created_at).toLocaleDateString()}</td><td>${esc(f.name)}</td><td>${esc(f.category)}</td>
    <td>${"★".repeat(f.rating)}</td><td class="msg">${esc(f.message)}</td>
    <td><span class="badge ${f.sentiment}">${f.sentiment}</span></td>
    <td><button class="btn sm ghost" onclick="editFb(${f.id})">Edit</button>
        <button class="btn sm danger" onclick="delFb(${f.id})">Delete</button></td></tr>`).join("")
    || `<tr><td colspan="7" class="muted">No feedback yet.</td></tr>`;
  pageInfo.textContent = `Page ${r.page} of ${r.pages || 1}`;
  prev.disabled = page <= 1; next.disabled = page >= r.pages;
}

async function editFb(id) {
  const f = await api(`/api/feedback/${id}`);
  const message = prompt("Edit message (sentiment will be re-analysed):", f.message);
  if (message === null) return;
  try { await api(`/api/feedback/${id}`, { method: "PUT", body: { message } }); toast("Updated"); refresh(); }
  catch (e) { toast(Object.values(e.data?.errors || {}).join(" ") || e.message); }
}
async function delFb(id) {
  if (!confirm("Delete this feedback?")) return;
  await api(`/api/feedback/${id}`, { method: "DELETE" }); toast("Deleted"); refresh();
}
const refresh = () => { loadStats(); loadTable(); };

search.addEventListener("input", debounce(() => { page = 1; loadTable(); }));
filterSent.addEventListener("change", () => { page = 1; loadTable(); });
prev.onclick = () => { page--; loadTable(); };
next.onclick = () => { page++; loadTable(); };
refresh();
setInterval(loadStats, 15000); // auto-refresh charts
