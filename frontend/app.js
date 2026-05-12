const API = '';  // same origin

// ── Navigation ────────────────────────────────────────────────────────────────

const PAGE_TITLES = {
  dashboard: 'Dashboard', quotes: 'Quotations', orders: 'Orders & Invoices',
  customers: 'Customers', products: 'Products / Inventory', 'ai-tool': 'AI Quote Generator'
};

function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');
  document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
  document.getElementById('page-title').textContent = PAGE_TITLES[page] || page;

  const loaders = { dashboard: loadDashboard, quotes: loadQuotes, orders: loadOrders,
                    customers: loadCustomers, products: loadProducts, 'ai-tool': loadAIPage };
  loaders[page]?.();
}

document.querySelectorAll('[data-page]').forEach(el => {
  el.addEventListener('click', e => { e.preventDefault(); navigateTo(el.dataset.page); });
});

function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const mc = document.getElementById('main-content');
  sb.classList.toggle('collapsed');
  mc.classList.toggle('expanded');
}

// ── API Helpers ───────────────────────────────────────────────────────────────

async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (e) {
    showToast(e.message, 'danger');
    throw e;
  }
}

function formatINR(amount) {
  if (amount === undefined || amount === null) return '—';
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  return `₹${Number(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function showToast(message, type = 'success') {
  const id = `toast-${Date.now()}`;
  const icons = { success: 'check-circle-fill', danger: 'exclamation-triangle-fill', info: 'info-circle-fill' };
  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
      <div class="d-flex">
        <div class="toast-body"><i class="bi bi-${icons[type] || 'info-circle-fill'} me-2"></i>${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  document.getElementById('toast-container').insertAdjacentHTML('beforeend', html);
  const toastEl = document.getElementById(id);
  new bootstrap.Toast(toastEl, { delay: 4000 }).show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// ── Status Badge ──────────────────────────────────────────────────────────────

const STATUS_ICONS = {
  draft: '📝', pending_approval: '⏳', approved: '✅', sent: '📤',
  negotiating: '🔄', accepted: '🤝', converted: '📦', rejected: '❌',
  paid: '✅', unpaid: '❌', pending_payment: '⏳'
};

function statusBadge(status) {
  const icon = STATUS_ICONS[status] || '•';
  return `<span class="status-badge status-${status}">${icon} ${status.replace(/_/g, ' ')}</span>`;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

async function loadDashboard() {
  const [stats, quotes] = await Promise.all([
    apiFetch('/api/stats').catch(() => null),
    apiFetch('/api/quotations?limit=6').catch(() => [])
  ]);

  if (stats) {
    document.getElementById('stat-quotes').textContent = stats.total_quotes;
    document.getElementById('stat-pending').textContent = stats.pending_approval;
    document.getElementById('stat-revenue').textContent = formatINR(stats.total_revenue);
    document.getElementById('stat-customers').textContent = stats.total_customers;
    document.getElementById('stat-pending-value').textContent = formatINR(stats.pending_value);

    const badge = document.getElementById('pending-badge');
    if (stats.pending_approval > 0) {
      badge.textContent = stats.pending_approval;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }

    const breakdown = document.getElementById('status-breakdown');
    const total = stats.total_quotes || 1;
    const colors = {
      draft: '#94a3b8', pending_approval: '#f59e0b', approved: '#10b981',
      sent: '#3b82f6', accepted: '#059669', converted: '#8b5cf6', rejected: '#ef4444'
    };
    breakdown.innerHTML = Object.entries(stats.quote_status_breakdown || {}).map(([status, count]) => `
      <div class="status-bar-row">
        <span style="width:110px;color:var(--muted);font-size:.8rem">${status.replace(/_/g,' ')}</span>
        <div class="status-bar">
          <div class="status-bar-fill" style="width:${(count/total*100).toFixed(1)}%;background:${colors[status]||'#94a3b8'}"></div>
        </div>
        <span style="width:28px;text-align:right;font-weight:600;font-size:.85rem">${count}</span>
      </div>`).join('');
  }

  const list = document.getElementById('recent-quotes-list');
  if (!quotes.length) {
    list.innerHTML = '<div class="text-center text-muted py-4">No quotations yet</div>';
    return;
  }
  list.innerHTML = quotes.map(q => `
    <div class="quote-list-item" onclick="viewQuote(${q.id})">
      <div>
        <div class="fw-semibold">${q.quote_number}</div>
        <div class="text-muted small">${q.customer_name} · ${q.item_count} item(s)</div>
      </div>
      <div class="text-end">
        <div class="fw-bold text-primary">${formatINR(q.total)}</div>
        ${statusBadge(q.status)}
      </div>
    </div>`).join('');
}

// ── Quotations ────────────────────────────────────────────────────────────────

async function loadQuotes() {
  const status = document.getElementById('quote-filter-status').value;
  const url = `/api/quotations${status ? `?status=${status}` : ''}`;
  const quotes = await apiFetch(url).catch(() => []);

  const tbody = document.getElementById('quotes-tbody');
  if (!quotes.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No quotations found</td></tr>`;
    return;
  }
  tbody.innerHTML = quotes.map(q => `
    <tr>
      <td><a href="#" onclick="viewQuote(${q.id});return false" class="fw-semibold text-primary">${q.quote_number}</a></td>
      <td>${q.customer_name}</td>
      <td>${q.item_count}</td>
      <td class="fw-bold">${formatINR(q.total)}</td>
      <td>${statusBadge(q.status)}</td>
      <td>${fmtDate(q.created_at)}</td>
      <td>
        <div class="d-flex gap-1">
          <button class="btn btn-xs btn-outline-secondary" onclick="viewQuote(${q.id})" title="View">
            <i class="bi bi-eye"></i>
          </button>
          <a class="btn btn-xs btn-outline-danger" href="${API}/api/quotations/${q.id}/pdf" target="_blank" title="PDF">
            <i class="bi bi-file-pdf"></i>
          </a>
          ${q.status === 'pending_approval' ? `
          <button class="btn btn-xs btn-success" onclick="approveQuote(${q.id})" title="Approve">
            <i class="bi bi-check-lg"></i>
          </button>` : ''}
          ${q.status === 'accepted' ? `
          <button class="btn btn-xs btn-primary" onclick="convertToOrder(${q.id})" title="Convert to Order">
            <i class="bi bi-bag-plus"></i>
          </button>` : ''}
        </div>
      </td>
    </tr>`).join('');
}

async function viewQuote(quoteId) {
  const q = await apiFetch(`/api/quotations/${quoteId}`).catch(() => null);
  if (!q) return;

  const itemsHtml = q.items.map((item, i) => `
    <tr>
      <td>${i+1}</td>
      <td>${item.description}</td>
      <td>${item.hsn_code || '—'}</td>
      <td>${item.quantity} ${item.unit}</td>
      <td>${formatINR(item.unit_price)}</td>
      <td class="fw-semibold">${formatINR(item.line_total)}</td>
    </tr>`).join('');

  const body = `
    <div class="row g-3 mb-3">
      <div class="col-md-6">
        <div class="quote-detail-label">Customer</div>
        <div class="fw-semibold">${q.customer.name}</div>
        <div class="text-muted small">${q.customer.company || ''} ${q.customer.phone || ''}</div>
        ${q.customer.gstin ? `<div class="text-muted small">GSTIN: ${q.customer.gstin}</div>` : ''}
      </div>
      <div class="col-md-6 text-md-end">
        <div class="quote-detail-label">Quote Details</div>
        <div class="fw-semibold">${q.quote_number}</div>
        <div class="text-muted small">Created: ${fmtDate(q.created_at)}</div>
        <div class="text-muted small">Valid Until: ${fmtDate(q.valid_until)}</div>
        <div class="mt-1">${statusBadge(q.status)}</div>
      </div>
    </div>

    <table class="table table-bordered table-sm mb-3">
      <thead><tr><th>#</th><th>Description</th><th>HSN</th><th>Qty/Unit</th><th>Rate</th><th>Amount</th></tr></thead>
      <tbody>${itemsHtml}</tbody>
    </table>

    <div class="row">
      <div class="col-md-6">
        ${q.notes ? `<div class="quote-detail-section"><div class="quote-detail-label">Notes</div><div>${q.notes}</div></div>` : ''}
        ${q.ai_notes ? `
        <div class="ai-suggestion-box">
          <div class="fw-semibold mb-1"><i class="bi bi-robot me-1"></i>AI Insight</div>
          ${q.ai_notes}
        </div>` : ''}
        <div class="mt-2">
          <span class="text-muted small">Payment: ${q.payment_terms}</span><br/>
          <span class="text-muted small">Delivery: ${q.delivery_terms}</span>
        </div>
      </div>
      <div class="col-md-6">
        <table class="table table-sm ms-auto" style="max-width:260px">
          <tr><td class="text-muted">Subtotal</td><td class="text-end">${formatINR(q.subtotal)}</td></tr>
          ${q.discount_percent > 0 ? `<tr><td class="text-muted">Discount (${q.discount_percent}%)</td><td class="text-end text-danger">-${formatINR(q.discount_amount)}</td></tr>` : ''}
          <tr><td class="text-muted">GST (${q.tax_percent}%)</td><td class="text-end">${formatINR(q.tax_amount)}</td></tr>
          <tr class="table-active"><td class="fw-bold">TOTAL</td><td class="text-end quote-total-row">${formatINR(q.total)}</td></tr>
        </table>
      </div>
    </div>`;

  const footerBtns = [];
  footerBtns.push(`<a class="btn btn-outline-secondary" href="${API}/api/quotations/${q.id}/pdf" target="_blank"><i class="bi bi-file-pdf me-1"></i>Download PDF</a>`);
  if (q.status === 'draft' || q.status === 'pending_approval') {
    footerBtns.push(`<button class="btn btn-success" onclick="approveQuote(${q.id})"><i class="bi bi-check-lg me-1"></i>Approve & Send</button>`);
    footerBtns.push(`<button class="btn btn-danger" onclick="rejectQuote(${q.id})"><i class="bi bi-x-lg me-1"></i>Reject</button>`);
  }
  if (q.status === 'approved') {
    footerBtns.push(`<button class="btn btn-primary" onclick="sendQuote(${q.id})"><i class="bi bi-send me-1"></i>Send to Customer</button>`);
  }
  if (q.status === 'accepted') {
    footerBtns.push(`<button class="btn btn-primary" onclick="convertToOrder(${q.id})"><i class="bi bi-bag-plus me-1"></i>Convert to Order</button>`);
  }

  document.getElementById('quoteModalTitle').innerHTML = `<i class="bi bi-file-earmark-text me-2"></i>${q.quote_number}`;
  document.getElementById('quoteModalBody').innerHTML = body;
  document.getElementById('quoteModalFooter').innerHTML =
    `<button class="btn btn-secondary me-auto" data-bs-dismiss="modal">Close</button>` + footerBtns.join('');

  new bootstrap.Modal(document.getElementById('quoteModal')).show();
}

async function approveQuote(id) {
  await apiFetch(`/api/quotations/${id}/approve`, { method: 'POST' });
  await apiFetch(`/api/quotations/${id}/send`, { method: 'POST' });
  showToast('Quote approved and sent to customer!');
  bootstrap.Modal.getInstance(document.getElementById('quoteModal'))?.hide();
  refreshAll();
}

async function rejectQuote(id) {
  if (!confirm('Reject this quotation?')) return;
  await apiFetch(`/api/quotations/${id}/reject`, { method: 'POST' });
  showToast('Quotation rejected', 'info');
  bootstrap.Modal.getInstance(document.getElementById('quoteModal'))?.hide();
  refreshAll();
}

async function sendQuote(id) {
  await apiFetch(`/api/quotations/${id}/send`, { method: 'POST' });
  showToast('Quote sent to customer');
  bootstrap.Modal.getInstance(document.getElementById('quoteModal'))?.hide();
  refreshAll();
}

async function convertToOrder(id) {
  const order = await apiFetch(`/api/quotations/${id}/convert-to-order`, { method: 'POST' });
  showToast(`Order ${order.order_number} created! Invoice: ${order.invoice_number}`);
  bootstrap.Modal.getInstance(document.getElementById('quoteModal'))?.hide();
  navigateTo('orders');
}

function openNewQuoteModal() {
  navigateTo('ai-tool');
}

// ── Orders ────────────────────────────────────────────────────────────────────

async function loadOrders() {
  const orders = await apiFetch('/api/orders').catch(() => []);
  const tbody = document.getElementById('orders-tbody');
  if (!orders.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No orders yet</td></tr>`;
    return;
  }
  tbody.innerHTML = orders.map(o => `
    <tr>
      <td class="fw-semibold">${o.order_number}</td>
      <td>${o.invoice_number || '—'}</td>
      <td>${o.customer_name}</td>
      <td class="fw-bold">${formatINR(o.total)}</td>
      <td>${statusBadge(o.status)}</td>
      <td>${statusBadge(o.payment_status)}</td>
      <td>
        <a class="btn btn-xs btn-outline-danger" href="${API}/api/orders/${o.id}/invoice-pdf" target="_blank" title="Invoice PDF">
          <i class="bi bi-file-earmark-pdf"></i>
        </a>
        ${o.payment_status === 'unpaid' ? `
        <button class="btn btn-xs btn-success ms-1" onclick="markPaid(${o.id})" title="Mark as Paid">
          <i class="bi bi-currency-rupee"></i>
        </button>` : ''}
      </td>
    </tr>`).join('');
}

async function markPaid(orderId) {
  await apiFetch(`/api/orders/${orderId}/status?status=processing&payment_status=paid`, { method: 'PUT' });
  showToast('Payment recorded!');
  loadOrders();
}

// ── Customers ─────────────────────────────────────────────────────────────────

async function loadCustomers() {
  const customers = await apiFetch('/api/customers').catch(() => []);
  const tbody = document.getElementById('customers-tbody');
  if (!customers.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No customers yet</td></tr>`;
    return;
  }
  tbody.innerHTML = customers.map(c => `
    <tr>
      <td><div class="fw-semibold">${c.name}</div>
          ${c.telegram_id ? `<small class="text-muted"><i class="bi bi-telegram"></i> ${c.telegram_id}</small>` : ''}</td>
      <td>${c.company || '—'}</td>
      <td>${c.phone || '—'}</td>
      <td><code>${c.gstin || '—'}</code></td>
      <td>
        <button class="btn btn-xs btn-outline-primary" onclick="viewCustomerQuotes(${c.id}, '${c.name}')">
          <i class="bi bi-file-earmark-text"></i> Quotes
        </button>
      </td>
    </tr>`).join('');
}

function openNewCustomerModal() {
  ['cust-name','cust-company','cust-phone','cust-email','cust-address','cust-gstin'].forEach(id => {
    document.getElementById(id).value = '';
  });
  new bootstrap.Modal(document.getElementById('customerModal')).show();
}

async function saveCustomer() {
  const name = document.getElementById('cust-name').value.trim();
  if (!name) { showToast('Name is required', 'danger'); return; }
  await apiFetch('/api/customers', {
    method: 'POST',
    body: JSON.stringify({
      name, company: document.getElementById('cust-company').value,
      phone: document.getElementById('cust-phone').value,
      email: document.getElementById('cust-email').value,
      address: document.getElementById('cust-address').value,
      gstin: document.getElementById('cust-gstin').value,
    })
  });
  showToast('Customer saved!');
  bootstrap.Modal.getInstance(document.getElementById('customerModal')).hide();
  loadCustomers();
  loadAIPage();
}

async function viewCustomerQuotes(customerId, customerName) {
  const quotes = await apiFetch(`/api/quotations?customer_id=${customerId}`).catch(() => []);
  // Switch to quotes tab with customer filter
  navigateTo('quotes');
}

// ── Products ──────────────────────────────────────────────────────────────────

async function loadProducts() {
  const products = await apiFetch('/api/products').catch(() => []);
  const tbody = document.getElementById('products-tbody');
  if (!products.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No products yet</td></tr>`;
    return;
  }
  tbody.innerHTML = products.map(p => `
    <tr>
      <td><code>${p.sku}</code></td>
      <td><div class="fw-semibold">${p.name}</div>
          <small class="text-muted">${p.description || ''}</small></td>
      <td>${p.unit}</td>
      <td>${formatINR(p.base_price)}</td>
      <td>${p.stock_quantity} ${p.unit}</td>
      <td>
        <span class="${p.available_quantity > 0 ? 'text-success fw-semibold' : 'text-danger'}">
          ${p.available_quantity} ${p.unit}
        </span>
      </td>
      <td>
        <button class="btn btn-xs btn-outline-primary" onclick="editStock(${p.id}, ${p.stock_quantity}, '${p.name}')">
          <i class="bi bi-pencil"></i>
        </button>
      </td>
    </tr>`).join('');
}

function openNewProductModal() {
  ['prod-sku','prod-name','prod-price','prod-min-price','prod-stock','prod-hsn','prod-desc'].forEach(id => {
    document.getElementById(id).value = '';
  });
  new bootstrap.Modal(document.getElementById('productModal')).show();
}

async function saveProduct() {
  const sku = document.getElementById('prod-sku').value.trim();
  const name = document.getElementById('prod-name').value.trim();
  const base_price = parseFloat(document.getElementById('prod-price').value);
  if (!sku || !name || isNaN(base_price)) {
    showToast('SKU, Name, and Price are required', 'danger'); return;
  }
  await apiFetch('/api/products', {
    method: 'POST',
    body: JSON.stringify({
      sku, name, base_price,
      unit: document.getElementById('prod-unit').value,
      min_price: parseFloat(document.getElementById('prod-min-price').value) || null,
      stock_quantity: parseFloat(document.getElementById('prod-stock').value) || 0,
      hsn_code: document.getElementById('prod-hsn').value,
      gst_percent: parseFloat(document.getElementById('prod-gst').value),
      description: document.getElementById('prod-desc').value,
    })
  });
  showToast('Product saved!');
  bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
  loadProducts();
}

async function editStock(productId, currentStock, name) {
  const qty = prompt(`Update stock for ${name}\nCurrent: ${currentStock}\nNew quantity:`, currentStock);
  if (qty === null) return;
  await apiFetch(`/api/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify({ stock_quantity: parseFloat(qty) })
  });
  showToast(`Stock updated for ${name}`);
  loadProducts();
}

// ── AI Quote Tool ─────────────────────────────────────────────────────────────

async function loadAIPage() {
  const customers = await apiFetch('/api/customers').catch(() => []);
  const sel = document.getElementById('ai-customer-select');
  sel.innerHTML = '<option value="">Select customer...</option>' +
    customers.map(c => `<option value="${c.id}">${c.name} ${c.company ? '— ' + c.company : ''}</option>`).join('');
}

async function runAIQuote() {
  const customerId = document.getElementById('ai-customer-select').value;
  const conversation = document.getElementById('ai-conversation-input').value.trim();

  if (!customerId) { showToast('Please select a customer', 'danger'); return; }
  if (!conversation) { showToast('Please enter a conversation', 'danger'); return; }

  const btn = document.getElementById('ai-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>AI is analyzing...';

  const panel = document.getElementById('ai-result-panel');
  panel.innerHTML = `<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>`;

  try {
    const result = await apiFetch('/api/ai/generate-quote', {
      method: 'POST',
      body: JSON.stringify({ conversation_text: conversation, customer_id: parseInt(customerId) })
    });

    panel.innerHTML = `
      <div class="d-flex align-items-center justify-content-between mb-3">
        <div>
          <div class="fw-bold text-success"><i class="bi bi-check-circle me-1"></i>Quote Generated!</div>
          <div class="text-muted small">${result.quote_number} · Confidence: ${Math.round(result.confidence * 100)}%</div>
        </div>
        <div class="text-end">
          <div class="h4 text-primary mb-0">${formatINR(result.total)}</div>
          <div class="text-muted small">Estimated Total</div>
        </div>
      </div>
      ${result.ai_suggestions ? `
      <div class="ai-suggestion-box mb-3">
        <div class="fw-semibold mb-1"><i class="bi bi-lightbulb me-1"></i>AI Insights</div>
        ${result.ai_suggestions}
      </div>` : ''}
      <div class="d-flex gap-2 mt-3">
        <a href="${API}/api/quotations/${result.quote_id}/pdf" target="_blank" class="btn btn-outline-secondary btn-sm">
          <i class="bi bi-file-pdf me-1"></i>Preview PDF
        </a>
        <button class="btn btn-success btn-sm" onclick="approveQuote(${result.quote_id})">
          <i class="bi bi-check-lg me-1"></i>Approve & Send
        </button>
        <button class="btn btn-outline-primary btn-sm" onclick="viewQuote(${result.quote_id})">
          <i class="bi bi-eye me-1"></i>Review / Edit
        </button>
      </div>`;

    showToast(`Quote ${result.quote_number} created successfully!`);
  } catch (e) {
    panel.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-magic"></i> Generate Quote with AI';
  }
}

// ── Init & Refresh ────────────────────────────────────────────────────────────

function refreshAll() {
  document.getElementById('last-refresh').textContent =
    'Updated ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  const activePage = document.querySelector('.page.active')?.id?.replace('page-', '');
  if (activePage) navigateTo(activePage);
}

// Auto-refresh pending count every 30 seconds
setInterval(async () => {
  const stats = await apiFetch('/api/stats').catch(() => null);
  if (!stats) return;
  const badge = document.getElementById('pending-badge');
  if (stats.pending_approval > 0) {
    badge.textContent = stats.pending_approval;
    badge.style.display = '';
    document.getElementById('stat-pending').textContent = stats.pending_approval;
  } else {
    badge.style.display = 'none';
  }
}, 30000);

// Boot
navigateTo('dashboard');
