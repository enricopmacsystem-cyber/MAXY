import {
  authHeaders,
  clearAuth,
  fetchCurrentUser,
  getStoredAuth,
  login,
  logout,
} from "./auth.js";
import { initChat } from "./chat.js";

const loginOverlay = document.getElementById("login-overlay");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const appShell = document.getElementById("app-shell");
const userLabel = document.getElementById("user-label");
const logoutBtn = document.getElementById("logout-btn");

async function checkAuthRequired() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    return Boolean(data.auth_required);
  } catch {
    return false;
  }
}

function showLogin(message = "") {
  loginOverlay.classList.remove("hidden");
  appShell.classList.add("hidden");
  if (message) {
    loginError.textContent = message;
    loginError.classList.remove("hidden");
  } else {
    loginError.classList.add("hidden");
  }
}

function showApp(user) {
  loginOverlay.classList.add("hidden");
  appShell.classList.remove("hidden");
  const display = user?.user?.display_name || user?.user?.username || "Utente";
  userLabel.textContent = display;
}

async function bootstrap() {
  const authRequired = await checkAuthRequired();

  if (!authRequired) {
    showApp({ user: { display_name: "Modalità sviluppo" } });
    initChat({ authRequired: false });
    logoutBtn.classList.add("hidden");
    return;
  }

  logoutBtn.classList.remove("hidden");
  const stored = getStoredAuth();
  if (stored?.access_token) {
    const session = await fetchCurrentUser();
    if (session) {
      showApp(session);
      initChat({ authRequired: true });
      return;
    }
  }

  showLogin();
  initChat({ authRequired: true, disabled: true });
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.classList.add("hidden");

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;

  try {
    const tokens = await login(username, password);
    const session = await fetchCurrentUser();
    showApp(session || { user: tokens.user });
    initChat({ authRequired: true });
  } catch (error) {
    showLogin(error.message);
  }
});

logoutBtn.addEventListener("click", async () => {
  await logout();
  clearAuth();
  showLogin("Sessione terminata.");
  initChat({ authRequired: true, disabled: true });
});

bootstrap();

export { authHeaders };
