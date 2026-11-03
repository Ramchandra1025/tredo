const categoryHost = document.getElementById("onboardingCategories");
const onboardingForm = document.getElementById("onboardingForm");
const onboardingMessage = document.getElementById("onboardingMessage");
const escapeText = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));

async function loadPreferences() {
  const response = await fetch("/api/onboarding");
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Couldn't load your learning paths.");
  const selected = new Set(data.selected_categories || []);
  categoryHost.innerHTML = data.categories.map(category => `
    <label class="onboarding-card ${selected.has(category.name) ? "selected" : ""}">
      <input type="checkbox" name="category" value="${escapeText(category.name)}" ${selected.has(category.name) ? "checked" : ""}>
      <span class="onboarding-icon" aria-hidden="true">${escapeText(category.icon)}</span>
      <span class="onboarding-card-copy"><strong>${escapeText(category.name)} trading</strong><small>${escapeText(category.description)}</small></span>
      <span class="selection-check" aria-hidden="true">✓</span>
    </label>`).join("");
  categoryHost.querySelectorAll('input[name="category"]').forEach(input => {
    input.addEventListener("change", () => input.closest(".onboarding-card").classList.toggle("selected", input.checked));
  });
  document.getElementById("dailyGoal").value = data.settings.daily_goal_minutes || 10;
}

onboardingForm.addEventListener("submit", async event => {
  event.preventDefault();
  const selected = [...categoryHost.querySelectorAll('input[name="category"]:checked')].map(input => input.value);
  if (!selected.length) {
    onboardingMessage.textContent = "Choose at least one path to build your learning trail.";
    return;
  }
  const button = onboardingForm.querySelector('button[type="submit"]');
  button.disabled = true;
  onboardingMessage.textContent = "Saving your preferences…";
  try {
    const response = await fetch("/api/onboarding", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        categories: selected,
        daily_goal_minutes: Number(document.getElementById("dailyGoal").value),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Couldn't save your preferences.");
    location.href = "/dashboard.html";
  } catch (error) {
    onboardingMessage.textContent = error.message;
    button.disabled = false;
  }
});

loadPreferences().catch(error => { onboardingMessage.textContent = error.message; });
