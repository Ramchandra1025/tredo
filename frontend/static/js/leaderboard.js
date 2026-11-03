async function loadBoard() {
  const host = document.getElementById("leaderboard");
  try {
    const response = await fetch("/api/leaderboard");
    if (response.status === 401) { location.href = "/login.html"; return; }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Couldn't load the leaderboard.");
    if (!data.leaderboard.length) { host.textContent = "No learners yet."; return; }
    const rows = data.leaderboard.map((learner, index) => {
      const row = document.createElement("p");
      const name = document.createElement("b");
      name.textContent = `#${index + 1}  ${learner.name}`;
      const xp = document.createElement("span");
      xp.textContent = `${Number(learner.xp).toLocaleString()} XP`;
      xp.style.cssFloat = "right";
      xp.style.color = "var(--accent)";
      row.append(name, xp);
      return row;
    });
    host.replaceChildren(...rows);
  } catch (error) { host.textContent = error.message; }
}
loadBoard();
