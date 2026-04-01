const DEPARTMENTS = [
  "Human Resources",
  "Finance",
  "Information Technology",
  "Marketing",
  "Sales",
  "Operations",
  "Customer Support",
  "Legal",
  "Procurement",
  "Research & Development"
];

const LEAVE_REASON_OPTIONS = [
  { label: "Annual leave", type: "normal", allocation: 21, recommended: 20 },
  { label: "Unpaid leave", type: "special", allocation: 30 },
  { label: "Employee's wedding", type: "special", allocation: 5 },
  { label: "Child's wedding", type: "special", allocation: 2 },
  { label: "Birth of a child", type: "special", allocation: 5 },
  { label: "Paternity leave", type: "special", allocation: 10 },
  { label: "Care for a sick child", type: "special", allocation: 5 },
  { label: "Family bereavement (spouse, child, parents, in-laws)", type: "special", allocation: 3 },
  { label: "Family bereavement (grandparents, siblings)", type: "special", allocation: 1 },
  { label: "Blood donation", type: "special", allocation: 1 },
];

const LEAVE_REASON_MAP = LEAVE_REASON_OPTIONS.reduce((acc, item) => {
  acc[item.label] = item;
  return acc;
}, {});

// Centralize API base path for flexibility (Ingress or separate host)
// Build absolute API base to avoid relative path issues under subpaths
const BASE_API = (function() {
  const base = '/api';
  // If app is served under a subpath, ensure we always hit absolute path
  return window.location.origin + base;
})();

let currentUser = null;
let currentBalance = { normal_days: 0, special_days: 0, allowances: {} };
let requestWithinAllowance = true;
let discordNotificationsEnabled = true;

function populateDepartments() {
  const select = document.getElementById("regDepartment");
  if (!select) return;
  select.innerHTML = '<option value="" disabled selected>Select department</option>';
  DEPARTMENTS.forEach(dep => {
    const opt = document.createElement("option");
    opt.value = dep;
    opt.textContent = dep;
    select.appendChild(opt);
  });
}

populateDepartments();

function populateLeaveReasons() {
  const select = document.getElementById("leaveReason");
  if (!select) return;
  select.innerHTML = '<option value="" disabled selected>Select a leave reason</option>';
  LEAVE_REASON_OPTIONS.forEach(reason => {
    const opt = document.createElement("option");
    opt.value = reason.label;
    opt.textContent = reason.label;
    select.appendChild(opt);
  });
}

populateLeaveReasons();

const leaveReasonSelect = document.getElementById("leaveReason");
const submitButton = document.getElementById("leaveSubmitBtn");
if (leaveReasonSelect) {
  leaveReasonSelect.addEventListener("change", event => {
    updateBalanceBanner(event.target.value);
  });
}

["leaveStart", "leaveEnd"].forEach(id => {
  const input = document.getElementById(id);
  if (input) {
    input.addEventListener("change", () => {
      updateBalanceBanner(leaveReasonSelect ? leaveReasonSelect.value : "");
    });
  }
});

function formatDays(value) {
  if (value === null || value === undefined) return "unlimited";
  return `${value} ${value === 1 ? "day" : "days"}`;
}

function getRequestedDays() {
  const startEl = document.getElementById("leaveStart");
  const endEl = document.getElementById("leaveEnd");
  if (!startEl || !endEl || !startEl.value || !endEl.value) {
    return null;
  }

  const start = new Date(startEl.value);
  const end = new Date(endEl.value);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return null;
  }

  const diffMs = end.getTime() - start.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1;
  if (diffDays <= 0) {
    return null;
  }
  return diffDays;
}

function updateBalanceBanner(selectedReason) {
  const banner = document.getElementById("balance");
  if (!banner) return;

  if (!selectedReason || !LEAVE_REASON_MAP[selectedReason]) {
    banner.className = "alert alert-info";
    banner.innerText = "Select a leave reason to see the available days.";
    requestWithinAllowance = false;
    if (submitButton) submitButton.disabled = true;
    return;
  }

  const meta = LEAVE_REASON_MAP[selectedReason];
  const allowance = currentBalance.allowances[selectedReason];
  const available = allowance && allowance.remaining !== undefined ? allowance.remaining : meta.allocation;
  const recommended = meta.recommended ?? (allowance && allowance.total !== undefined ? allowance.total : meta.allocation ?? null);
  const requested = getRequestedDays();

  let message = `${selectedReason}: ${formatDays(available)} remaining`;
  if (recommended && (available === null || available === undefined || recommended !== available)) {
    message += ` • annual cap: ${formatDays(recommended)}`;
  }

  let cssClass = "alert alert-info";
  requestWithinAllowance = true;

  if (requested) {
    if (available === null || available === undefined) {
      cssClass = "alert alert-success";
      message += ` • requesting ${formatDays(requested)}`;
    } else {
      const remaining = available - requested;
      if (remaining >= 0) {
        cssClass = "alert alert-success";
        message += ` • ${formatDays(remaining)} remain after this request`;
      } else {
        cssClass = "alert alert-warning";
        message += ` • short by ${formatDays(Math.abs(remaining))}`;
        requestWithinAllowance = false;
      }
    }
  } else if (recommended) {
    message += ` • annual cap: ${formatDays(recommended)}`;
  }

  banner.className = cssClass;
  banner.innerText = message;

  if (submitButton) {
    submitButton.disabled = !requestWithinAllowance;
  }
}

function showRegister() {
  document.getElementById("loginForm").classList.add("d-none");
  document.getElementById("adminLoginForm").classList.add("d-none");
  document.getElementById("registerForm").classList.remove("d-none");
  document.body.classList.remove("user-mode");
}

function showLogin() {
  document.getElementById("registerForm").classList.add("d-none");
  document.getElementById("adminLoginForm").classList.add("d-none");
  document.getElementById("loginForm").classList.remove("d-none");
  document.body.classList.remove("user-mode");
}

function showAdminLogin() {
  document.getElementById("loginForm").classList.add("d-none");
  document.getElementById("registerForm").classList.add("d-none");
  document.getElementById("adminLoginForm").classList.remove("d-none");
  document.body.classList.remove("user-mode");
}

function showUser() {
  document.getElementById("loginCard").classList.add("d-none");
  document.getElementById("userPanel").classList.remove("d-none");
  document.body.classList.add("user-mode");
  document.getElementById("welcomeUser").innerText = `Hello, ${currentUser.name}!`;
  const deptEl = document.getElementById("userDepartment");
  if (deptEl) {
    deptEl.innerText = `Department: ${currentUser.department || "General"}`;
  }
}

function showAdmin() {
  const loginCard = document.getElementById("loginCard");
  if (loginCard) {
    loginCard.classList.add("d-none");
  }

  const adminPanel = document.getElementById("adminPanel");
  if (adminPanel) {
    adminPanel.classList.remove("d-none");
  }

  const adminApp = document.getElementById("adminApp");
  const adminLoginBox = document.getElementById("adminLoginBox");
  if (adminApp) {
    adminApp.classList.remove("d-none");
  }
  if (adminLoginBox) {
    adminLoginBox.classList.add("d-none");
  }
  document.body.classList.add("user-mode");
}

function logout() {
  location.reload();
}

// --- AUTH ---
async function register() {
  const name = document.getElementById("regName").value;
  const email = document.getElementById("regEmail").value;
  const pass = document.getElementById("regPassword").value;
  const department = document.getElementById("regDepartment").value;

  if (!department) {
    alert("Select a department.");
    return;
  }

  const res = await fetch(`${BASE_API}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password: pass, department })
  });
  const d = await res.json();
  alert(d.msg || d.error);
}

async function login() {
  const email = document.getElementById("loginEmail").value;
  const pass = document.getElementById("loginPassword").value;

  const res = await fetch(`${BASE_API}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: pass })
  });
  const d = await res.json();

  if (d.msg === "ok") {
    currentUser = d;
    if (d.admin) {
      showAdmin();
      loadAllLeaves();
      loadDiscordNotificationsSetting();
    } else {
      showUser();
      loadBalance();
      loadMyLeaves();
    }
  } else {
    alert(d.error || "Invalid login!");
  }
}

// ---- Password reset ----
document.addEventListener('DOMContentLoaded', () => {
  const forgot = document.getElementById('forgotLink');
  if (forgot) {
    forgot.addEventListener('click', async (e) => {
      e.preventDefault();
      const email = prompt('Enter the email address for password reset:');
      if (!email) return;
      try {
        const res = await fetch(`${BASE_API}/password/reset/request`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, return_link: true })
        });
        const data = await res.json();
        if (data.reset_link) {
          window.location.href = data.reset_link;
          return;
        }
        alert(data.msg || 'If the email exists, you will receive a link on Discord.');
      } catch (err) {
        alert('Failed to submit the reset request.');
      }
    });
  }
});

async function adminLogin() {
  const email = document.getElementById("adminUser").value;
  const pass = document.getElementById("adminPass").value;

  const res = await fetch(`${BASE_API}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: pass })
  });
  const d = await res.json();

  if (d.msg === "ok" && d.admin) {
    currentUser = d;
    showAdmin();
    loadAllLeaves();
    loadDiscordNotificationsSetting();
  } else {
    alert("Admin login failed!");
  }
}

// --- USER ---
async function loadBalance() {
  const r = await fetch(`${BASE_API}/balance/${encodeURIComponent(currentUser.user_id)}`);
  const d = await r.json();
  currentBalance = {
    normal_days: d.normal_days ?? 0,
    special_days: d.special_days ?? 0,
    allowances: d.allowances || {}
  };

  LEAVE_REASON_OPTIONS.forEach(option => {
    const existing = currentBalance.allowances[option.label] || {};
    if (existing.remaining === undefined || existing.remaining === null) {
      existing.remaining = option.allocation ?? null;
    }
    if (existing.total === undefined || existing.total === null) {
      existing.total = option.allocation ?? null;
    }
    currentBalance.allowances[option.label] = existing;
  });

  updateBalanceBanner(leaveReasonSelect ? leaveReasonSelect.value : "");
}

async function loadMyLeaves() {
  const r = await fetch(`${BASE_API}/leaves/${encodeURIComponent(currentUser.user_id)}`);
  const d = await r.json();
  let list = document.getElementById("myLeaves");
  if (!list) {
    // Fallback: create the container if it is missing.
    const wrapper = document.querySelector(".leave-list-wrapper") || document.getElementById("userPanel");
    list = document.createElement("ul");
    list.id = "myLeaves";
    list.className = "list-group";
    if (wrapper) wrapper.appendChild(list);
    else document.body.appendChild(list);
  }
  list.innerHTML = "";
  if (!Array.isArray(d) || d.length === 0) {
    const empty = document.createElement("li");
    empty.className = "list-group-item text-muted";
    empty.textContent = "You do not have any leave requests yet.";
    list.appendChild(empty);
    console.debug("loadMyLeaves: 0 items");
    return;
  }
  console.debug(`loadMyLeaves: ${d.length} items`);
  d.forEach(l => {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between align-items-start gap-2";
    const badgeClass = l.status && l.status.toLowerCase() === 'approved' ? 'success' : (l.status && l.status.toLowerCase() === 'rejected' ? 'danger' : 'warning');
    const submitted = l.created_at ? new Date(l.created_at) : null;
    const submittedAt = submitted ? submitted.toLocaleString('en-GB', { hour12: false }) : null;
    li.innerHTML = `
      <div>
        <div><strong>${l.start} → ${l.end}</strong></div>
        <div class="small text-muted">Type: ${l.type} • Reason: ${l.reason || 'n/a'} • ${l.days} days</div>
        ${submittedAt ? `<div class="small">Submitted at: ${submittedAt}</div>` : ''}
      </div>
      <span class="badge bg-${badgeClass} align-self-center text-uppercase">${l.status}</span>
    `;
    list.appendChild(li);
  });
}

async function newLeave() {
  const start = document.getElementById("leaveStart").value;
  const end = document.getElementById("leaveEnd").value;
  const reason = document.getElementById("leaveReason").value;

  if (!start || !end) {
    alert("Fill in the leave period.");
    return;
  }

  if (new Date(end) < new Date(start)) {
    alert("The end date must be after the start date.");
    return;
  }

  if (!reason) {
    alert("Select a leave reason.");
    return;
  }

  if (!requestWithinAllowance) {
    alert("The selected interval exceeds the available days for the chosen reason.");
    return;
  }

  const res = await fetch(`${BASE_API}/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: currentUser.user_id,
      start,
      end,
      reason,
      type: LEAVE_REASON_MAP[reason]?.type || "special"
    })
  });

  const d = await res.json();

  if (res.ok) {
    alert(d.msg || "Request submitted!");
    loadMyLeaves();
    loadBalance();
  } else {
    alert(d.error || "Unknown error while submitting the request!");
  }
}

// --- ADMIN ---
async function loadAllLeaves() {
  ensureBulkControls();
  const r = await fetch(`${BASE_API}/admin/leaves`);
  const d = await r.json();
  let list = document.getElementById("allLeaves") || document.getElementById("adminLeaves");
  if (!list) {
    // Fallback: create the container if it is missing.
    const card = document.querySelector("#adminApp .card") || document.getElementById("adminPanel") || document.body;
    list = document.createElement("div");
    list.id = "allLeaves";
    list.className = "list-group mt-3";
    card.appendChild(list);
  }
  list.innerHTML = "";
  if (!Array.isArray(d) || d.length === 0) {
    const empty = document.createElement("div");
    empty.className = "list-group-item text-muted text-center";
    empty.textContent = "There are no pending requests.";
    list.appendChild(empty);
    console.debug("loadAllLeaves: 0 items");
    return;
  }
  console.debug(`loadAllLeaves: ${d.length} items`);
  d.forEach(l => {
    const div = document.createElement("div");
    div.className = "list-group-item d-flex justify-content-between align-items-center";
    div.innerHTML = `
      <div><b>${l.name}</b> (${l.email})<br>Department: ${l.department || "General"}<br>${l.start}→${l.end} (${l.type}, ${l.days} days)<br><span class="badge bg-info text-dark mt-1">${l.reason || 'n/a'}</span></div>
      <div>
        <button class="btn btn-success btn-sm" onclick="updateLeave(${l.id}, 'approved')">Approve</button>
        <button class="btn btn-danger btn-sm" onclick="updateLeave(${l.id}, 'rejected')">Reject</button>
      </div>`;
    list.appendChild(div);
  });
}

async function updateLeave(id, action) {
  await fetch(`${BASE_API}/admin/leaves/${encodeURIComponent(id)}/${encodeURIComponent(action)}`, { method: "POST" });
  loadAllLeaves();
}

async function bulkUpdateLeaves(action) {
  const validActions = { approved: "approve", rejected: "reject" };
  if (!(action in validActions)) {
    console.error("Unknown bulk action", action);
    return;
  }

  const confirmMsg = `Are you sure you want to ${validActions[action]} all pending requests?`;
  if (!confirm(confirmMsg)) {
    return;
  }

  try {
    const res = await fetch(`${BASE_API}/admin/leaves/bulk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Could not update the requests.");
      return;
    }

    alert(data.msg || `${data.processed || 0} requests updated.`);
    loadAllLeaves();
  } catch (err) {
    console.error("Failed to update requests in bulk", err);
    alert("An error occurred while processing the requests.");
  }
}

function ensureBulkControls() {
  let container = document.getElementById("bulkControls");
  if (container) {
    return;
  }

  const list = document.getElementById("adminLeaves") || document.getElementById("allLeaves");
  if (!list) {
    return;
  }

  const card = list.closest(".card") || document.querySelector("#adminApp .card") || document.querySelector("#adminPanel .card");
  if (!card) {
    return;
  }

  container = document.createElement("div");
  container.id = "bulkControls";
  container.className = "d-flex flex-wrap justify-content-end gap-2 mt-3";
  container.innerHTML = `
    <button class="btn btn-success btn-sm" onclick="bulkUpdateLeaves('approved')">✅ Approve All</button>
    <button class="btn btn-danger btn-sm" onclick="bulkUpdateLeaves('rejected')">🚫 Reject All</button>
  `;

  card.insertBefore(container, list);
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("adminApp")) {
    ensureBulkControls();
  }
});

function updateDiscordToggleUI() {
  const statusBadge = document.getElementById("discordStatus");
  const toggleBtn = document.getElementById("discordToggleBtn");
  if (!statusBadge || !toggleBtn) return;

  if (discordNotificationsEnabled) {
    statusBadge.className = "badge bg-success";
    statusBadge.textContent = "Discord notifications enabled";
    toggleBtn.className = "btn btn-outline-warning btn-sm";
    toggleBtn.textContent = "🔕 Disable Discord notifications";
  } else {
    statusBadge.className = "badge bg-secondary";
    statusBadge.textContent = "Discord notifications disabled";
    toggleBtn.className = "btn btn-outline-success btn-sm";
    toggleBtn.textContent = "🔔 Enable Discord notifications";
  }
}

async function loadDiscordNotificationsSetting() {
  try {
    const res = await fetch(`${BASE_API}/admin/notifications/discord`);
    if (res.ok) {
      const data = await res.json();
      discordNotificationsEnabled = Boolean(data.enabled);
    }
  } catch (err) {
    console.error("Could not load the Discord notification status", err);
  } finally {
    updateDiscordToggleUI();
  }
}

async function toggleDiscordNotifications() {
  const toggleBtn = document.getElementById("discordToggleBtn");
  const nextState = !discordNotificationsEnabled;
  if (toggleBtn) {
    toggleBtn.disabled = true;
  }

  try {
    const res = await fetch(`${BASE_API}/admin/notifications/discord`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: nextState })
    });
    if (res.ok) {
      const data = await res.json();
      discordNotificationsEnabled = Boolean(data.enabled);
    } else {
      const data = await res.json().catch(() => ({}));
      alert(data.error || "Could not update Discord notifications.");
    }
  } catch (err) {
    console.error("Could not update Discord notifications", err);
    alert("Failed to connect to the server.");
  } finally {
    if (toggleBtn) {
      toggleBtn.disabled = false;
    }
    updateDiscordToggleUI();
  }
}
