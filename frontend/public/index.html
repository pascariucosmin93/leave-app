<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🌴 Leave Management</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="style.css" rel="stylesheet">
</head>
<body class="bg-light app-shell">

<!-- Login Card -->
<main class="auth-wrapper">
  <div id="loginCard" class="auth-card card shadow p-4">
    <div class="auth-header mb-4">
      <div class="auth-brand">
        <span class="brand-icon">🌴</span>
        <h3 class="brand-title mb-0">Leave Management App</h3>
      </div>
      <button id="toggleDark" class="btn btn-sm btn-outline-secondary rounded-pill">🌙</button>
    </div>

    <!-- Login normal -->
    <form id="loginForm" class="auth-form" onsubmit="login(); return false;">
      <label class="form-label visually-hidden" for="loginEmail">Email</label>
      <input id="loginEmail" type="email" class="form-control" placeholder="Email" required>

      <label class="form-label visually-hidden" for="loginPassword">Password</label>
      <input id="loginPassword" type="password" class="form-control" placeholder="Password" required>

      <button type="submit" class="btn btn-success w-100">Login</button>
      <button type="button" id="forgotLink" class="btn btn-link w-100 forgot-btn mt-2">🔑 Forgot your password?</button>
      <button type="button" onclick="showAdminLogin()" class="btn btn-outline-dark w-100">Admin Login</button>
      <button type="button" onclick="showRegister()" class="btn btn-primary w-100">✍️ Create Account</button>
    </form>

    <!-- Login admin -->
    <form id="adminLoginForm" class="auth-form d-none" onsubmit="adminLogin(); return false;">
      <h5 class="form-title">🔑 Admin Login</h5>
      <label class="form-label visually-hidden" for="adminUser">Username</label>
      <input id="adminUser" type="text" class="form-control" placeholder="Username" required>

      <label class="form-label visually-hidden" for="adminPass">Password</label>
      <input id="adminPass" type="password" class="form-control" placeholder="Password" required>
      <button type="submit" class="btn btn-dark w-100">Enter Admin Area</button>
      <button type="button" onclick="showLogin()" class="btn btn-outline-secondary w-100">⬅ Back</button>
    </form>

    <!-- Register -->
    <form id="registerForm" class="auth-form d-none" onsubmit="register(); return false;">
      <h5 class="form-title">✍️ Create Account</h5>
      <label class="form-label visually-hidden" for="regName">Name</label>
      <input id="regName" type="text" class="form-control" placeholder="Name" required>

      <label class="form-label visually-hidden" for="regEmail">Email</label>
      <input id="regEmail" type="email" class="form-control" placeholder="Email" required>

      <label class="form-label visually-hidden" for="regDepartment">Department</label>
      <select id="regDepartment" class="form-select" required>
        <option value="" disabled>Select department</option>
      </select>

      <label class="form-label visually-hidden" for="regPassword">Password</label>
      <input id="regPassword" type="password" class="form-control" placeholder="Password" required>
      <button type="submit" class="btn btn-primary w-100">Register</button>
      <button type="button" onclick="showLogin()" class="btn btn-outline-secondary w-100">⬅ Back</button>
    </form>
  </div>
</main>

<!-- User panel -->
<div id="userPanel" class="container d-none">
  <div class="user-dashboard card shadow p-4">
    <header class="dashboard-header">
      <div>
        <h4 id="welcomeUser" class="mb-1"></h4>
        <p class="text-muted mb-0" id="userDepartment"></p>
      </div>
    </header>
    <div id="balance" class="alert alert-info mb-4"></div>
    <div class="dashboard-layout">
      <div class="dashboard-form">
        <h5 class="mb-3">Submit a Request</h5>
        <input id="leaveStart" type="date" class="form-control mb-2">
        <input id="leaveEnd" type="date" class="form-control mb-2">
        <select id="leaveReason" class="form-select mb-3"></select>
        <button id="leaveSubmitBtn" onclick="newLeave()" class="btn btn-primary w-100">Submit Request</button>
      </div>
      <div class="leave-list-wrapper">
        <div class="d-flex justify-content-between align-items-center mb-3">
          <h5 class="mb-0">My Requests</h5>
        </div>
        <ul id="myLeaves" class="list-group"></ul>
      </div>
    </div>
    <footer class="dashboard-footer">
      <p class="text-muted small mb-3">Finished? You can log out at any time.</p>
      <button class="btn btn-outline-secondary logout-btn" onclick="logout()">Logout</button>
    </footer>
  </div>
</div>

<!-- Admin panel -->
<div id="adminPanel" class="container d-none">
  <div class="card shadow p-4">
    <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-2">
      <h4 class="mb-0">User Requests</h4>
      <div class="d-flex align-items-center gap-2">
        <span id="discordStatus" class="badge bg-success">Discord notifications enabled</span>
        <button id="discordToggleBtn" class="btn btn-outline-warning btn-sm" onclick="toggleDiscordNotifications()">
          🔕 Disable Discord notifications
        </button>
      </div>
    </div>
    <div id="bulkControls" class="d-flex flex-wrap justify-content-end gap-2 mt-3">
      <button class="btn btn-success btn-sm" onclick="bulkUpdateLeaves('approved')">✅ Approve All</button>
      <button class="btn btn-danger btn-sm" onclick="bulkUpdateLeaves('rejected')">🚫 Reject All</button>
    </div>
    <div id="allLeaves" class="list-group mt-3"></div>
    <button class="btn btn-secondary mt-3" onclick="logout()">Logout</button>
  </div>
</div>

<script src="script.js?v=12"></script>
<script>
  // 🌙 Dark Mode toggle
  document.getElementById("toggleDark").addEventListener("click", function() {
    document.body.classList.toggle("dark-mode");
    this.textContent = document.body.classList.contains("dark-mode") ? "☀️" : "🌙";
  });

  
</script>
</body>
</html>
