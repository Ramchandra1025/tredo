const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const categoryHost = document.getElementById("categories");
const roadmapHost = document.getElementById("roadmap");
const settingsDialog = document.getElementById("settingsDialog");
const notificationsDialog = document.getElementById("notificationsDialog");
let dashboardData = null;
let activeCategory = null;
let lastEngagement = Date.now();
let lastSample = Date.now();

function drawLives(amount) {
  const full = Math.max(0, Math.min(5, Number(amount) || 0));
  document.getElementById("lives").innerHTML = Array.from({length: 5}, (_, index) =>
    `<span class="${index < full ? "heart-full" : "heart-empty"}" aria-hidden="true">♥</span>`
  ).join(" ");
  document.getElementById("livesNote").textContent = full ? `${full} ready to learn` : "Your next life is recovering";
}

function drawCategoryTabs(categories, selected) {
  categoryHost.innerHTML = categories.map(category => `
    <button type="button" role="tab" aria-selected="${category.name === selected}" class="path-tab ${category.name === selected ? "active" : ""}" data-category="${escapeHtml(category.name)}">
      <span aria-hidden="true">${escapeHtml(category.icon)}</span><span>${escapeHtml(category.name)}</span>
    </button>`).join("");
  categoryHost.querySelectorAll("[data-category]").forEach(button => button.addEventListener("click", () => loadDashboard(button.dataset.category)));
}

function drawRoadmap(levels, category) {
  const empty = document.getElementById("roadmapEmpty");
  if (!levels.length) {
    roadmapHost.innerHTML = "";
    roadmapHost.hidden = true;
    empty.hidden = false;
    return;
  }
  roadmapHost.hidden = false;
  empty.hidden = true;
  const points = levels.map((_, index) => {
    const template = [[50, 7], [65, 27], [35, 47], [65, 67], [50, 87]];
    if (index < template.length && levels.length === 5) return template[index];
    const wave = Math.sin(index * 1.4) * 17;
    return [50 + wave, 7 + index * (86 / Math.max(1, levels.length - 1))];
  });
  const pathPoints = points.map(([x, y]) => `${(x * 10).toFixed(0)} ${((y / 100) * 1000).toFixed(0)}`);
  let path = pathPoints.length ? `M ${pathPoints[0]}` : "";
  for (let i = 1; i < pathPoints.length; i++) {
    const [x0, y0] = points[i - 1].map((value, axis) => axis === 0 ? value * 10 : value * 10);
    const [x1, y1] = points[i].map((value, axis) => axis === 0 ? value * 10 : value * 10);
    const midY = (y0 + y1) / 2;
    path += ` C ${x0} ${midY} ${x1} ${midY} ${x1} ${y1}`;
  }
  const nodes = levels.map((level, index) => {
    const [x, y] = points[index];
    const state = level.state || "locked";
    const symbol = state === "completed" ? "✓" : state === "current" ? "▶" : "⌑";
    const status = state === "completed" ? `Completed · ${level.stars || 1} stars` : state === "current" ? "Ready to play" : "Complete the level before this one";
    const stars = state === "completed" ? `<span class="node-stars" aria-label="${level.stars || 1} stars">${"★".repeat(level.stars || 1)}${"☆".repeat(3 - (level.stars || 1))}</span>` : "";
    return `<div class="road-stop ${state}" style="left:${x}%;top:${y}%">
      <button class="level-node ${state}" type="button" ${state === "locked" ? "disabled" : `data-level="${level.id}"`}
        aria-label="Level ${level.level}, ${escapeHtml(level.title)}. ${status}${state === "locked" ? ". Locked" : ". Open level"}">
        <span class="node-symbol" aria-hidden="true">${symbol}</span><span class="node-number">${String(level.level).padStart(2, "0")}</span>
      </button>
      <div class="node-caption"><span class="node-world">WORLD ${level.world_order} · ${escapeHtml(level.world_title)}</span><span class="node-state">${status}</span><strong>${escapeHtml(level.title)}</strong>${stars}<small>${level.mastered_questions || 0}/${level.total_questions || 6} questions · ${level.estimated_minutes || 5} min</small>
        ${state === "locked" ? `<small class="unlock-note">🔒 Unlocks after level ${Math.max(1, level.level - 1)}</small>` : ""}
      </div>
    </div>`;
  }).join("");
  roadmapHost.innerHTML = `<svg class="road-path" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true"><path class="road-shadow" d="${path}"/><path class="road-center" d="${path}"/></svg>${nodes}`;
  roadmapHost.querySelectorAll("[data-level]").forEach(button => button.addEventListener("click", () => {
    location.href = `/lesson.html?id=${encodeURIComponent(button.dataset.level)}`;
  }));
  document.getElementById("categoryEyebrow").textContent = `${category} TRADING`;
  const firstOpen = levels.find(item => item.state === "current");
  const title = firstOpen?.world_title || levels[levels.length - 1]?.world_title || "Your learning trail";
  document.getElementById("roadmapTitle").textContent = title;
  const unlocked = levels.filter(item => item.state !== "locked").length;
  document.getElementById("roadmapSub").textContent = `${unlocked} of ${levels.length} levels open · ${firstOpen ? `Next up: ${firstOpen.title}` : "Path complete — review any level"}`;
}

function drawAchievements(items) {
  const host = document.getElementById("achievements");
  if (!items.length) {
    host.innerHTML = '<p class="muted empty-copy">Your first milestone is waiting at the end of level one.</p>';
    return;
  }
  host.innerHTML = items.map(item => `<div class="achievement-row"><span class="achievement-icon" aria-hidden="true">${escapeHtml(item.icon)}</span><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.description)}</small></div><span class="achievement-check" aria-label="Unlocked">✓</span></div>`).join("");
}

function drawRecent(items) {
  const host = document.getElementById("recent");
  if (!items.length) {
    host.innerHTML = '<p class="muted empty-copy">Your completed levels will show up here.</p>';
    return;
  }
  host.innerHTML = items.map(item => `<div class="recent-row"><span class="recent-check" aria-hidden="true">✓</span><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.category)} · ${item.score}% first-try accuracy</small></div><span class="recent-xp">+50 XP</span></div>`).join("");
}

function drawDaily(data) {
  const goal = Number(data.daily_goal_minutes || 10);
  const activity = data.daily_activity || {};
  document.getElementById("goalLabel").textContent = `${goal} MIN`;
  document.getElementById("activeMinutes").textContent = Number(activity.active_minutes || 0).toFixed(1).replace(/\.0$/, "");
  document.getElementById("goalProgress").style.width = `${Math.max(0, Math.min(100, activity.goal_percent || 0))}%`;
  document.getElementById("goalStatus").textContent = activity.goal_percent >= 100 ? "Daily goal complete · nice work!" : `${Math.max(0, goal - Math.floor(activity.active_seconds / 60))} min left to today's goal`;
}

async function loadDashboard(category) {
  const url = new URL("/api/dashboard", location.origin);
  if (category) url.searchParams.set("category", category);
  const response = await fetch(url);
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Couldn't load your learning trail.");
  if (!data.user.onboarding_complete) { location.href = "/onboarding.html"; return; }
  dashboardData = data;
  activeCategory = data.active_category;
  document.getElementById("userName").textContent = data.user.name;
  document.getElementById("navUserName").textContent = data.user.name.split(" ")[0];
  document.querySelector(".profile-dot").textContent = data.user.name.trim().charAt(0).toUpperCase() || "T";
  document.getElementById("xp").textContent = Number(data.user.xp).toLocaleString();
  document.getElementById("coins").textContent = Number(data.user.coins).toLocaleString();
  document.getElementById("streak").textContent = data.user.current_streak;
  document.getElementById("levelsDone").textContent = `${data.completed} level${data.completed === 1 ? "" : "s"} completed`;
  drawLives(data.user.remaining_lives);
  drawCategoryTabs(data.categories, activeCategory);
  drawRoadmap(data.roadmap || [], activeCategory || "Learning");
  drawDaily(data);
  drawAchievements(data.achievements || []);
  drawRecent(data.recent || []);
  document.getElementById("notificationCount").textContent = data.unread_notifications || "";
}

async function loadSettings() {
  const response = await fetch("/api/onboarding");
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  const selected = new Set(data.selected_categories || []);
  document.getElementById("settingsCategories").innerHTML = data.categories.map(category => `
    <label class="settings-category"><input type="checkbox" name="settings-category" value="${escapeHtml(category.name)}" ${selected.has(category.name) ? "checked" : ""}>
      <span aria-hidden="true">${escapeHtml(category.icon)}</span><strong>${escapeHtml(category.name)}</strong></label>`).join("");
  document.getElementById("dailyGoalSelect").value = data.settings.daily_goal_minutes || 10;
  document.getElementById("profileSummary").textContent = `${dashboardData?.user.email || ""} · ${dashboardData?.completed || 0} levels completed · ${dashboardData?.user.longest_streak || 0} day longest streak`;
}

document.getElementById("settingsBtn").addEventListener("click", async () => {
  try { await loadSettings(); settingsDialog.showModal(); }
  catch (error) { document.getElementById("settingsMessage").textContent = error.message; }
});
document.getElementById("dockProfile").addEventListener("click", () => document.getElementById("settingsBtn").click());
document.getElementById("settingsForm").addEventListener("submit", async event => {
  event.preventDefault();
  const categories = [...document.querySelectorAll('input[name="settings-category"]:checked')].map(input => input.value);
  const message = document.getElementById("settingsMessage");
  if (!categories.length) { message.textContent = "Keep at least one learning path selected."; return; }
  const button = event.currentTarget.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const response = await fetch("/api/settings", {
      method: "PUT", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({categories, daily_goal_minutes:Number(document.getElementById("dailyGoalSelect").value), timezone:Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Couldn't save settings.");
    settingsDialog.close();
    await loadDashboard(activeCategory && categories.includes(activeCategory) ? activeCategory : categories[0]);
  } catch (error) { message.textContent = error.message; }
  finally { button.disabled = false; }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await fetch("/api/logout", {method:"POST"});
  location.href = "/";
});

async function loadNotifications() {
  const response = await fetch("/api/notifications");
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  const host = document.getElementById("notificationList");
  host.innerHTML = data.notifications.length ? data.notifications.map(item => `
    <button class="notification-row ${item.is_read ? "read" : "unread"}" type="button" data-notification="${item.id}">
      <span class="notification-dot" aria-hidden="true"></span><span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.message)}</small><time>${escapeHtml(item.created_at)}</time></span>
    </button>`).join("") : '<p class="muted empty-copy">No messages yet. Level unlocks and milestones will appear here.</p>';
  host.querySelectorAll("[data-notification]").forEach(button => button.addEventListener("click", async () => {
    await fetch(`/api/notifications/${button.dataset.notification}/read`, {method:"POST"});
    await loadNotifications();
    await loadDashboard(activeCategory);
  }));
  document.getElementById("notificationCount").textContent = data.unread_count || "";
}
document.getElementById("notificationsBtn").addEventListener("click", async () => {
  await loadNotifications();
  notificationsDialog.showModal();
});
document.getElementById("readAllBtn").addEventListener("click", async () => {
  await fetch("/api/notifications/read-all", {method:"POST"});
  await loadNotifications();
  await loadDashboard(activeCategory);
});

document.querySelectorAll(".close-dialog").forEach(button => button.addEventListener("click", event => {
  event.preventDefault();
  button.closest("dialog").close();
}));

function markEngaged() { lastEngagement = Date.now(); }
for (const eventName of ["pointerdown", "keydown", "touchstart", "scroll"]) {
  document.addEventListener(eventName, markEngaged, {passive:true});
}
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") lastSample = Date.now(); });

async function sendActiveTime() {
  const now = Date.now();
  if (document.visibilityState !== "visible" || now - lastEngagement > 75000) {
    lastSample = now;
    return;
  }
  const seconds = Math.min(45, Math.floor((now - lastSample) / 1000));
  lastSample = now;
  if (!seconds) return;
  const eventId = globalThis.crypto?.randomUUID?.() || `active-${now}-${Math.random().toString(36).slice(2, 12)}`;
  try {
    const response = await fetch("/api/activity", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({event_id:eventId, seconds})
    });
    if (response.status === 401) return;
    const data = await response.json();
    if (response.ok && dashboardData) {
      dashboardData.daily_activity.active_seconds = data.active_seconds;
      dashboardData.daily_activity.active_minutes = data.active_minutes;
      dashboardData.daily_activity.goal_percent = Math.min(100, Math.round(data.active_seconds / (data.daily_goal_minutes * 60) * 100));
      dashboardData.user.current_streak = data.current_streak;
      document.getElementById("streak").textContent = data.current_streak;
      drawDaily(dashboardData);
      if (data.goal_complete) {
        document.getElementById("goalStatus").textContent = "Daily goal complete · +10 XP and +10 coins!";
        loadDashboard(activeCategory);
      }
    }
  } catch { /* Time pings are best effort; learning progress is saved separately. */ }
}

loadDashboard().catch(error => {
  document.getElementById("roadmapTitle").textContent = "Couldn't load your trail";
  document.getElementById("roadmapSub").textContent = error.message;
});
setInterval(sendActiveTime, 30000);
