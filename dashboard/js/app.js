/**
 * ChainSure SaaS — Dashboard Application Logic
 * Handles navigation, API calls, and UI updates.
 */

const API_BASE = "http://localhost:8000/api";
let API_KEY = "";

// ──────────────────────────────────────────────
//  Navigation
// ──────────────────────────────────────────────

const sections = ["overview", "tenants", "policies", "claims", "pool"];
const titles = {
  overview: "Platform Overview",
  tenants: "Insurance Partners",
  policies: "Policies",
  claims: "Claims Management",
  pool: "Liquidity Pool",
};

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    const section = item.dataset.section;

    // Update active nav
    document
      .querySelectorAll(".nav-item")
      .forEach((n) => n.classList.remove("active"));
    item.classList.add("active");

    // Show section
    sections.forEach((s) => {
      const el = document.getElementById(`section-${s}`);
      if (el) el.classList.toggle("hidden", s !== section);
    });

    // Update title
    document.getElementById("page-title").textContent = titles[section] || "";
  });
});

// ──────────────────────────────────────────────
//  Modal
// ──────────────────────────────────────────────

const modal = document.getElementById("modal-overlay");

function openModal() {
  modal.classList.remove("hidden");
}
function closeModal() {
  modal.classList.add("hidden");
}

document.getElementById("btn-add-tenant").addEventListener("click", openModal);
document
  .getElementById("btn-add-tenant-2")
  ?.addEventListener("click", openModal);
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);

modal.addEventListener("click", (e) => {
  if (e.target === modal) closeModal();
});

// ──────────────────────────────────────────────
//  Tenant Form
// ──────────────────────────────────────────────

document.getElementById("tenant-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const tenant = {
    tenant_id: document.getElementById("input-tenant-id").value,
    name: document.getElementById("input-tenant-name").value,
    contact_email: document.getElementById("input-tenant-email").value,
    whatsapp_numbers: [],
  };

  try {
    const res = await fetch(`${API_BASE}/tenants/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(tenant),
    });

    const data = await res.json();

    if (data.success) {
      closeModal();
      addTenantRow(data.data);
      updateStats();
      addActivity(
        `🏢 Tenant "${tenant.name}" registered`,
        `ID: ${tenant.tenant_id}`,
      );
      e.target.reset();
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (err) {
    // Offline mode — add locally
    closeModal();
    addTenantRow(tenant);
    addActivity(
      `🏢 Tenant "${tenant.name}" registered (offline)`,
      `ID: ${tenant.tenant_id}`,
    );
    e.target.reset();
  }
});

// ──────────────────────────────────────────────
//  UI Helpers
// ──────────────────────────────────────────────

function addTenantRow(tenant) {
  const tbody = document.getElementById("tenants-tbody");

  // Remove empty state
  const emptyRow = tbody.querySelector(".empty-state");
  if (emptyRow) emptyRow.closest("tr").remove();

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><code>${tenant.tenant_id}</code></td>
    <td>${tenant.name}</td>
    <td>${tenant.contact_email}</td>
    <td><span class="status status-active">Active</span></td>
    <td>${tenant.contracts ? "Deployed" : "Pending"}</td>
    <td>
      <button class="btn btn-sm btn-secondary" onclick="deployContracts('${tenant.tenant_id}')">Deploy</button>
    </td>
  `;
  tbody.appendChild(tr);

  // Update counter
  const stat = document.getElementById("stat-tenants");
  stat.textContent = parseInt(stat.textContent) + 1;
}

function addActivity(title, description) {
  const list = document.getElementById("activity-list");
  const item = document.createElement("div");
  item.className = "activity-item";
  item.innerHTML = `
    <span class="activity-icon">🔔</span>
    <div class="activity-content">
      <strong>${title}</strong>
      <p>${description}</p>
    </div>
  `;
  list.prepend(item);
}

function updateStats() {
  // In production, fetch from /api/analytics/overview
}

async function deployContracts(tenantId) {
  addActivity(
    `🚀 Deploying contracts for ${tenantId}`,
    "PolicyNFT, ClaimsContract, LiquidityPool deploying to Base...",
  );
  alert(
    `Contract deployment for "${tenantId}" would be triggered via the API.\nIn production, this calls TenantFactory.deployTenantContracts().`,
  );
}

// ──────────────────────────────────────────────
//  Init
// ──────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      addActivity("✅ API Connected", "Backend is healthy and responding");
    }
  } catch {
    addActivity(
      "⚠️ API Offline",
      "Running in demo mode. Start the API server to connect.",
    );
  }
}

init();
