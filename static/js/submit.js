const form = document.getElementById("feedbackForm");
const ratingInput = document.getElementById("rating");
const stars = [...document.querySelectorAll("#stars button")];

stars.forEach(b => b.addEventListener("click", () => {
  ratingInput.value = b.dataset.v;
  stars.forEach(s => s.classList.toggle("on", +s.dataset.v <= +b.dataset.v));
}));

api("/api/products").then(ps => {
  const sel = document.getElementById("productSelect");
  ps.forEach(p => sel.insertAdjacentHTML("beforeend", `<option value="${p.id}">${esc(p.name)}</option>`));
});

const preview = document.getElementById("livePreview");
form.message.addEventListener("input", debounce(async (e) => {
  if (e.target.value.trim().length < 5) { preview.textContent = "Live sentiment: —"; return; }
  const r = await api("/api/analyze", { method: "POST", body: { text: e.target.value } });
  preview.innerHTML = `Live sentiment: <span class="badge ${r.label}">${r.label}</span> (${r.score})`;
}));

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errBox = document.getElementById("formErrors");
  errBox.textContent = "";
  const body = Object.fromEntries(new FormData(form));
  body.product_id = body.product_id ? +body.product_id : null;
  if (!body.rating) { errBox.textContent = "Please choose a rating."; return; }
  try {
    const fb = await api("/api/feedback", { method: "POST", body });
    const r = document.getElementById("result");
    r.classList.remove("hidden");
    r.innerHTML = `<strong>Thank you, ${esc(fb.name)}!</strong><br>
      Detected sentiment: <span class="badge ${fb.sentiment}">${fb.sentiment}</span>
      (score ${fb.sentiment_score})`;
    form.reset(); stars.forEach(s => s.classList.remove("on")); ratingInput.value = "";
    preview.textContent = "Live sentiment: —";
    toast("Feedback submitted");
  } catch (err) {
    errBox.textContent = err.data?.errors ? Object.values(err.data.errors).join(" ") : err.message;
  }
});
