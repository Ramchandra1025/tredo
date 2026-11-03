const lessonId = new URLSearchParams(location.search).get("id");
const questionForm = document.getElementById("answerForm");
const optionsHost = document.getElementById("answerOptions");
const feedbackHost = document.getElementById("answerFeedback");
const checkButton = document.getElementById("checkAnswerBtn");
const continueButton = document.createElement("button");
continueButton.type = "button";
continueButton.id = "continueButton";
continueButton.className = "btn continue-button";
continueButton.textContent = "Continue →";
continueButton.hidden = true;
document.querySelector(".question-actions").append(continueButton);

let levelData = null;
let currentQuestion = null;
let hasMasteredCurrent = false;
let hintedQuestion = null;
let lastEngagement = Date.now();
let lastSample = Date.now();

function setError(message) {
  document.getElementById("lessonError").textContent = message || "";
}

function drawLives(count) {
  document.getElementById("lessonLives").textContent = Number(count ?? 5);
}

function drawProgress(data) {
  const mastered = data.mastered_questions || 0;
  const total = data.total_questions || 6;
  const percent = Math.min(100, Math.round(mastered / total * 100));
  document.getElementById("progressFill").style.width = `${percent}%`;
  document.getElementById("progressFill").setAttribute("aria-valuenow", percent);
  document.getElementById("questionCount").textContent = `${mastered} / ${total} mastered`;
  document.getElementById("progressPercent").textContent = `${percent}%`;
}

function buildQuestion(question) {
  currentQuestion = question;
  hasMasteredCurrent = false;
  hintedQuestion = null;
  feedbackHost.hidden = true;
  feedbackHost.replaceChildren();
  continueButton.hidden = true;
  checkButton.disabled = true;
  checkButton.hidden = false;
  checkButton.textContent = question.attempts ? "Try again" : "Check answer";
  document.getElementById("activeQuestionNumber").textContent = question.number;
  document.getElementById("questionText").textContent = question.text;
  optionsHost.replaceChildren();
  question.options.forEach(option => {
    const label = document.createElement("label");
    label.className = "answer-option";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "answer";
    input.value = option.key;
    input.addEventListener("change", () => {
      checkButton.disabled = false;
      feedbackHost.hidden = true;
      optionsHost.querySelectorAll(".correct-choice,.wrong-choice").forEach(node => node.classList.remove("correct-choice", "wrong-choice"));
    });
    const key = document.createElement("span");
    key.className = "answer-key";
    key.textContent = option.key;
    const text = document.createElement("span");
    text.className = "answer-copy";
    text.textContent = option.text;
    label.append(input, key, text);
    optionsHost.append(label);
  });
  document.getElementById("hintBtn").disabled = false;
  document.getElementById("hintBtn").innerHTML = "✦ Hint <span>3 coins</span>";
  document.getElementById("hintMessage").hidden = true;
}

function showFeedback({correct, answerText, explanation, lifeLost, remainingLives}) {
  feedbackHost.replaceChildren();
  feedbackHost.hidden = false;
  feedbackHost.className = `answer-feedback ${correct ? "success" : "mistake"}`;
  const title = document.createElement("strong");
  title.textContent = correct ? "That's right!" : "Not quite — here's the idea.";
  const detail = document.createElement("p");
  detail.textContent = correct ? explanation : `Correct answer: ${answerText}. ${explanation}`;
  feedbackHost.append(title, detail);
  if (!correct) {
    const lifeNote = document.createElement("small");
    lifeNote.textContent = lifeLost ? "One life used. You can retry this question without losing another." : "You can retry this question; no more lives will be used for it.";
    feedbackHost.append(lifeNote);
    drawLives(remainingLives);
  }
}

function showCompletedReview() {
  const card = document.getElementById("questionCard");
  card.hidden = true;
  const review = document.getElementById("levelReview");
  review.hidden = false;
  review.innerHTML = `<div class="review-stamp" aria-hidden="true">✓</div><div class="eyebrow">LEVEL COMPLETED · ${levelData.stars || 1} STAR${levelData.stars === 1 ? "" : "S"}</div><h2>Review this lesson</h2><p></p><p class="muted review-progress">You mastered ${levelData.mastered_questions} of ${levelData.total_questions} questions · ${levelData.accuracy_percent}% first-attempt accuracy.</p><a class="btn" href="/dashboard.html">Back to your trail</a>`;
  review.querySelector("p").textContent = levelData.level.content;
}

async function loadLevel() {
  if (!lessonId || !/^\d+$/.test(lessonId)) { location.href = "/dashboard.html"; return; }
  const response = await fetch(`/api/levels/${encodeURIComponent(lessonId)}`);
  if (response.status === 401) { location.href = "/login.html"; return; }
  const data = await response.json();
  if (!response.ok) {
    setError(data.error || "This level isn't available yet.");
    if (data.locked || response.status === 403) setTimeout(() => { location.href = "/dashboard.html"; }, 1500);
    return;
  }
  levelData = data;
  const level = data.level;
  document.title = `${level.title} · TRADO`;
  document.getElementById("lessonMeta").textContent = `${level.category.toUpperCase()} · LEVEL ${level.level} · ${level.world_title.toUpperCase()}`;
  document.getElementById("lessonTitle").textContent = level.title;
  document.getElementById("lessonContent").textContent = level.content;
  document.getElementById("mentorMessage").textContent = level.description;
  drawProgress(data);
  drawLives(data.remaining_lives);
  if (data.completion_status === "completed") {
    showCompletedReview();
    document.getElementById("hintBtn").disabled = true;
    return;
  }
  if (!data.question || data.total_questions !== 6) {
    setError("This level is missing its six-question lesson. Please refresh or contact the TRADO administrator.");
    return;
  }
  buildQuestion(data.question);
}

questionForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (!currentQuestion || hasMasteredCurrent) return;
  const selected = optionsHost.querySelector('input[name="answer"]:checked');
  if (!selected) return;
  checkButton.disabled = true;
  setError("");
  try {
    const response = await fetch(`/api/levels/${encodeURIComponent(lessonId)}/answer`, {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({answer:selected.value, question_id:currentQuestion.id})
    });
    const data = await response.json();
    if (response.status === 401) { location.href = "/login.html"; return; }
    if (!response.ok) throw new Error(data.error || "Couldn't check that answer.");
    if (!data.correct) {
      const selectedOption = optionsHost.querySelector(`input[value="${CSS.escape(selected.value)}"]`)?.closest(".answer-option");
      const correctOption = optionsHost.querySelector(`input[value="${CSS.escape(data.correct_answer)}"]`)?.closest(".answer-option");
      selectedOption?.classList.add("wrong-choice");
      correctOption?.classList.add("correct-choice");
      showFeedback({correct:false, answerText:data.correct_answer_text, explanation:data.explanation, lifeLost:data.life_lost, remainingLives:data.remaining_lives});
      optionsHost.querySelectorAll("input").forEach(input => { input.checked = false; });
      checkButton.textContent = "Try again";
      checkButton.disabled = true;
      return;
    }
    hasMasteredCurrent = true;
    levelData = data.progress;
    drawProgress(data.progress);
    drawLives(data.remaining_lives);
    optionsHost.querySelectorAll("input").forEach(input => { input.disabled = true; });
    showFeedback({correct:true, explanation:data.explanation});
    checkButton.hidden = true;
    if (data.completed) {
      showCompletion(data.completion);
      return;
    }
    continueButton.hidden = false;
  } catch (error) {
    setError(error.message);
    checkButton.disabled = false;
  }
});

continueButton.addEventListener("click", () => {
  if (!levelData?.question) {
    setError("Your progress is saved. Reload the level to continue.");
    return;
  }
  document.getElementById("mentorMessage").textContent = "Nice work. Take this idea with you to the next question.";
  buildQuestion(levelData.question);
  document.getElementById("questionCard").scrollIntoView({behavior:"smooth", block:"center"});
});

document.getElementById("hintBtn").addEventListener("click", async event => {
  if (!currentQuestion) return;
  const button = event.currentTarget;
  button.disabled = true;
  const message = document.getElementById("hintMessage");
  try {
    const response = await fetch(`/api/levels/${encodeURIComponent(lessonId)}/hint`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({question_id:currentQuestion.id})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Couldn't open a hint.");
    message.textContent = data.hint;
    message.hidden = false;
    button.innerHTML = data.coins_spent ? `✦ Hint used <span>balance ${data.coins}</span>` : `✦ Hint <span>balance ${data.coins}</span>`;
    hintedQuestion = currentQuestion.id;
    if (!data.coins_spent) button.disabled = false;
  } catch (error) {
    message.textContent = error.message;
    message.hidden = false;
    button.disabled = false;
  }
});

function showCompletion(completion) {
  document.getElementById("completionTitle").textContent = levelData.level.title;
  document.getElementById("completionStars").textContent = `${"★".repeat(completion.stars || 1)}${"☆".repeat(3 - (completion.stars || 1))}`;
  document.getElementById("completionXp").textContent = `+${completion.xp || 0}`;
  document.getElementById("completionCoins").textContent = `+${completion.coins || 0}`;
  document.getElementById("completionAccuracy").textContent = `${completion.accuracy_percent || 0}%`;
  document.getElementById("completionAchievements").textContent = completion.achievements?.length
    ? `Achievement unlocked: ${completion.achievements.map(item => item.title).join(", ")}` : "All six questions mastered. Your progress is saved.";
  document.getElementById("completionDialog").showModal();
  document.getElementById("completionDialog").classList.add("celebrate");
}

document.getElementById("nextLevelBtn").addEventListener("click", async () => {
  const category = levelData?.level?.category;
  const url = new URL("/api/dashboard", location.origin);
  if (category) url.searchParams.set("category", category);
  const response = await fetch(url);
  const data = await response.json();
  const next = data.roadmap?.find(level => level.state === "current");
  location.href = next ? `/lesson.html?id=${next.id}` : "/dashboard.html";
});

document.getElementById("exitLesson").addEventListener("click", () => { location.href = "/dashboard.html"; });

function markEngaged() { lastEngagement = Date.now(); }
for (const eventName of ["pointerdown", "keydown", "touchstart", "scroll"]) document.addEventListener(eventName, markEngaged, {passive:true});
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") lastSample = Date.now(); });
async function recordLessonTime() {
  const now = Date.now();
  if (document.visibilityState !== "visible" || now - lastEngagement > 75000) { lastSample = now; return; }
  const seconds = Math.min(45, Math.floor((now - lastSample) / 1000));
  lastSample = now;
  if (!seconds) return;
  const eventId = globalThis.crypto?.randomUUID?.() || `lesson-${now}-${Math.random().toString(36).slice(2, 12)}`;
  try {
    await fetch("/api/activity", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({event_id:eventId, seconds})});
  } catch { /* Progress answers are saved independently of timer pings. */ }
}

document.getElementById("lessonContent").addEventListener("click", markEngaged);
loadLevel().catch(error => setError(error.message));
setInterval(recordLessonTime, 30000);
