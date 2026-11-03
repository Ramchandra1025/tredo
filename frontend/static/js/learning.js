const escapeLesson = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
async function loadLessons(){
 const params=new URLSearchParams(location.search);const category=params.get("category");
 const res=await fetch("/api/lessons"+(category?"?category="+encodeURIComponent(category):""));
 if(res.status===401){location.href="/login.html";return}
 const d=await res.json();
 if(!res.ok){document.getElementById("lessonList").textContent=d.error||"Couldn't load lessons.";return}
 const groups={};d.lessons.forEach(l=>(groups[l.category]??=[]).push(l));
 document.getElementById("lessonList").innerHTML=Object.entries(groups).map(([cat,lessons])=>`<section><h2>${escapeLesson(cat)}</h2>${lessons.map(l=>{
   const locked=l.state==="locked";const status=l.state==="completed"?"COMPLETED":locked?"LOCKED":"READY";
   const card=`<small>LEVEL ${l.level} · ${status}</small><h3>${escapeLesson(l.title)}</h3><span class="muted">${l.mastered_questions||0}/6 mastered · ${l.estimated_minutes} min</span>`;
   return locked?`<div class="lesson-card locked-card" aria-disabled="true">${card}<span class="muted">🔒 Complete the previous level to unlock.</span></div>`:`<a class="lesson-card" href="/lesson.html?id=${l.id}">${card}<span class="muted">${l.state==="completed"?"Review lesson →":"Start level →"}</span></a>`;
 }).join("")}</section>`).join("")||"<p class=\"muted\">Choose a learning path in your profile to get started.</p>";
}
loadLessons();
