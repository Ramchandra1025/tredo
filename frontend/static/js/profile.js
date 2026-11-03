const escapeProfileText = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
let profileData = null;

function drawAvatarChoices(avatars, selectedId) {
  const host = document.getElementById("avatarChoices");
  host.innerHTML = avatars.map(avatar => `
    <label class="avatar-choice ${avatar.id === selectedId ? "selected" : ""}">
      <input type="radio" name="avatar" value="${escapeProfileText(avatar.id)}" ${avatar.id === selectedId ? "checked" : ""}>
      <span class="avatar-choice-art">${window.tradoAvatarMarkup(avatar.id)}</span>
      <span class="avatar-choice-copy"><strong>${escapeProfileText(avatar.name)}</strong><small>${escapeProfileText(avatar.role)}</small></span>
      <span class="avatar-choice-check" aria-hidden="true">✓</span>
    </label>`).join("");
  host.querySelectorAll('input[name="avatar"]').forEach(input => input.addEventListener("change", () => {
    host.querySelectorAll(".avatar-choice").forEach(card => card.classList.toggle("selected", card.contains(input)));
    drawProfilePreview();
  }));
}

function drawProfilePreview() {
  const avatarId = document.querySelector('input[name="avatar"]:checked')?.value || profileData?.user.avatar_id || "candela";
  document.getElementById("profileAvatarPreview").innerHTML = window.tradoAvatarMarkup(avatarId, "avatar-art profile-preview-art");
  document.getElementById("profilePreviewName").textContent = document.getElementById("profileName").value.trim() || "Trader";
}

async function loadProfile() {
  const response = await fetch("/api/profile");
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Couldn't load your profile.");
  profileData = data;
  if (!data.user.onboarding_complete) { location.href = "/onboarding.html"; return; }

  document.getElementById("profileName").value = data.user.name;
  document.getElementById("profileEmail").textContent = data.user.email;
  document.getElementById("profileTraderType").innerHTML = data.trader_types.map(type =>
    `<option value="${escapeProfileText(type.id)}">${escapeProfileText(type.label)}</option>`
  ).join("");
  document.getElementById("profileTraderType").value = data.user.trader_type;
  document.getElementById("profileDailyGoal").value = data.user.daily_goal_minutes;
  drawAvatarChoices(data.avatars, data.user.avatar_id);
  drawProfilePreview();

  document.getElementById("profileLevels").textContent = `${data.completed_levels} / ${data.total_levels}`;
  document.getElementById("profileXp").textContent = Number(data.user.xp).toLocaleString();
  document.getElementById("profileCoins").textContent = Number(data.user.coins).toLocaleString();
  document.getElementById("profileStreak").textContent = Number(data.user.current_streak).toLocaleString();
  document.getElementById("profileCurrentLevels").innerHTML = data.current_levels.length
    ? data.current_levels.map(level => `<span><strong>${escapeProfileText(level.category)}</strong> · Level ${Number(level.level)} — ${escapeProfileText(level.title)}</span>`).join("")
    : '<span class="muted">All selected paths are complete. Choose a new path to continue learning.</span>';
  const percent = data.total_levels ? Math.round(data.completed_levels / data.total_levels * 100) : 0;
  document.getElementById("profileProgressFill").style.width = `${percent}%`;
  document.getElementById("profileProgressNote").textContent = `${percent}% of your selected learning paths completed.`;
  document.getElementById("profilePaths").innerHTML = data.selected_categories.length
    ? data.selected_categories.map(category => `<span class="profile-path-chip">${escapeProfileText(category)}</span>`).join("")
    : '<span class="muted">No learning paths selected.</span>';
  document.getElementById("profileAchievements").innerHTML = data.achievements.length
    ? data.achievements.map(item => `<div class="achievement-row"><span class="achievement-icon" aria-hidden="true">${escapeProfileText(item.icon)}</span><div><strong>${escapeProfileText(item.title)}</strong><small>${escapeProfileText(item.description)}</small></div><span class="achievement-check" aria-label="Unlocked">✓</span></div>`).join("")
    : '<p class="muted empty-copy">Finish a level to earn your first achievement.</p>';
}

document.getElementById("profileName").addEventListener("input", drawProfilePreview);
document.getElementById("profileForm").addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.getElementById("profileMessage");
  const button = document.getElementById("saveProfile");
  const avatarId = document.querySelector('input[name="avatar"]:checked')?.value;
  button.disabled = true;
  message.textContent = "Saving your profile…";
  try {
    const response = await fetch("/api/profile", {
      method: "PUT",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        name: document.getElementById("profileName").value,
        trader_type: document.getElementById("profileTraderType").value,
        avatar_id: avatarId,
        daily_goal_minutes: Number(document.getElementById("profileDailyGoal").value)
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Couldn't save your profile.");
    profileData.user = {...profileData.user, ...data.user};
    document.getElementById("profileEmail").textContent = data.user.email;
    message.textContent = "Profile saved. Your dashboard is updated.";
    drawProfilePreview();
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

document.getElementById("profileLogout").addEventListener("click", async () => {
  await fetch("/api/logout", {method:"POST"});
  location.href = "/";
});

loadProfile().catch(error => { document.getElementById("profileMessage").textContent = error.message; });
