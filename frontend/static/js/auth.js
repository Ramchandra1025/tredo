async function sendAuth(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed. Please try again.");
  return data;
}

document.querySelectorAll("[data-toggle-password]").forEach(button => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.togglePassword);
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    button.textContent = showing ? "Show" : "Hide";
    button.setAttribute("aria-label", `${showing ? "Show" : "Hide"} ${input.id === "confirmPassword" ? "confirmation password" : "password"}`);
  });
});

const registerForm = document.getElementById("registerForm");
const loginForm = document.getElementById("loginForm");
const form = registerForm || loginForm;

if (form) form.addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.getElementById("message");
  const submit = form.querySelector('button[type="submit"]');
  message.textContent = "Please wait…";
  submit.disabled = true;
  try {
    const payload = registerForm
      ? {
          name: document.getElementById("name").value,
          email: document.getElementById("email").value,
          password: document.getElementById("password").value,
          confirm_password: document.getElementById("confirmPassword").value,
          terms_accepted: document.getElementById("termsAccepted").checked
        }
      : {
          email: document.getElementById("email").value,
          password: document.getElementById("password").value,
          remember: document.getElementById("remember").checked
        };
    const data = await sendAuth(registerForm ? "/api/register" : "/api/login", payload);
    location.href = data.user?.onboarding_complete ? "/dashboard.html" : "/onboarding.html";
  } catch (error) {
    message.textContent = error.message;
    submit.disabled = false;
  }
});

document.getElementById("forgotPassword")?.addEventListener("click", () => {
  document.getElementById("message").textContent = "Password reset email is not configured for this project yet. Please contact your TRADO administrator.";
});
