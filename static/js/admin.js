async function loadProducts() {
  const ps = await api("/api/products");
  prodBody.innerHTML = ps.map(p => `<tr>
    <td>${esc(p.name)}</td><td>$${p.price.toFixed(2)}</td>
    <td><input type="number" min="0" value="${p.stock}" style="width:80px" onchange="setStock(${p.id}, this.value)"></td>
    <td>${p.available ? '<span class="badge positive">In stock</span>' : '<span class="badge negative">Out of stock</span>'}</td>
    <td><button class="btn sm danger" onclick="delProduct(${p.id})">Delete</button></td></tr>`).join("");
  orderProduct.innerHTML = ps.map(p => `<option value="${p.id}" ${p.available ? "" : "disabled"}>${esc(p.name)} (${p.stock})</option>`).join("");
}
async function loadOrders() {
  const os = await api("/api/orders");
  orderBody.innerHTML = os.map(o => `<tr>
    <td>${o.id}</td><td>${esc(o.customer_name)}</td><td>${esc(o.product_name)}</td><td>${o.quantity}</td>
    <td><span class="badge ${o.status}">${o.status}</span></td>
    <td>${o.status !== "Delivered" ? `<button class="btn sm" onclick="advance(${o.id})">Advance →</button>` : ""}
        ${o.status === "Placed" ? `<button class="btn sm danger" onclick="cancelOrder(${o.id})">Cancel</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="6" class="muted">No orders.</td></tr>`;
}
const wrap = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message); } finally { loadProducts(); loadOrders(); } };
const setStock = wrap((id, v) => api(`/api/products/${id}`, { method: "PUT", body: { stock: +v } }));
const delProduct = wrap(id => confirm("Delete product?") && api(`/api/products/${id}`, { method: "DELETE" }));
const advance = wrap(id => api(`/api/orders/${id}/advance`, { method: "PATCH" }));
const cancelOrder = wrap(id => api(`/api/orders/${id}`, { method: "DELETE" }).then(() => toast("Cancelled, stock restored")));

productForm.onsubmit = wrap(async (e) => {
  e.preventDefault();
  await api("/api/products", { method: "POST", body: Object.fromEntries(new FormData(productForm)) });
  productForm.reset(); toast("Product added");
});
orderForm.onsubmit = wrap(async (e) => {
  e.preventDefault();
  const b = Object.fromEntries(new FormData(orderForm));
  await api("/api/orders", { method: "POST", body: { ...b, product_id: +b.product_id, quantity: +b.quantity } });
  toast("Order placed");
});
loadProducts(); loadOrders();
