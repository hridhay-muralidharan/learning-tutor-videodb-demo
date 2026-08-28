const data = window.COURSE_DATA;
const storageKey = `study_state:${data.course.title}`;
const defaultPreferences = {
  goal: "exam_readiness",
  supportLevel: "balanced",
  sessionLength: "standard",
  practiceOrder: "learn_then_practice",
  sourceDetail: "essential",
  ...(data.personalization?.defaults || {}),
};

const state = loadState();
state.lessons = state.lessons || {};
state.notes = state.notes || {};
state.textbookHighlights = state.textbookHighlights || {};
state.textbookNotes = state.textbookNotes || {};
state.textbookPage = state.textbookPage || {};
state.practice = state.practice || {};
state.videoPlayback = state.videoPlayback || {};
state.preferences = { ...defaultPreferences, ...(state.preferences || {}) };

const runtimePlayback = {};

let activeLessonId = state.activeLessonId || data.lessons[0]?.id;
let activeView = "dashboard";

const views = {
  dashboard: document.getElementById("dashboardView"),
  lesson: document.getElementById("lessonView"),
  practice: document.getElementById("practiceView"),
  review: document.getElementById("reviewView"),
  profile: document.getElementById("profileView"),
  sources: document.getElementById("sourcesView"),
};

const sourceLabels = {
  source_backed: "Source-backed",
  demo_placeholder: "Demo placeholder",
  needs_processing: "Needs processing",
  unavailable: "Source unavailable",
};

function loadState() {
  try {
    return JSON.parse(localStorage.getItem(storageKey)) || {};
  } catch (_error) {
    return {};
  }
}

function saveState() {
  state.activeLessonId = activeLessonId;
  localStorage.setItem(storageKey, JSON.stringify(state));
}

function lessonState(lessonId) {
  if (!state.lessons[lessonId]) {
    state.lessons[lessonId] = {
      mastery: "not_started",
      attempts: 0,
      lastPracticed: null,
      reviewReason: "",
    };
  }
  return state.lessons[lessonId];
}

function practiceState(questionId) {
  if (!state.practice[questionId]) {
    state.practice[questionId] = { attempted: false, hintOpen: false };
  }
  return state.practice[questionId];
}

function activeLesson() {
  return data.lessons.find((lesson) => lesson.id === activeLessonId) || data.lessons[0];
}

function showView(view) {
  activeView = view;
  Object.entries(views).forEach(([key, element]) => {
    element.classList.toggle("view-hidden", key !== view);
  });
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  saveState();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setLesson(lessonId, view = "lesson") {
  activeLessonId = lessonId;
  if (view === "lesson") {
    const item = lessonState(lessonId);
    if (item.mastery === "not_started") item.mastery = "seen";
  }
  saveState();
  render();
  showView(view);
}

function updateMastery(lessonId, mastery) {
  if (!hasAttemptedPractice(activeLesson())) return;
  const item = lessonState(lessonId);
  item.mastery = mastery;
  item.attempts += ["practiced", "review_needed", "mastered"].includes(mastery) ? 1 : 0;
  item.lastPracticed = new Date().toISOString();
  item.reviewReason = mastery === "review_needed"
    ? "You marked this class for revision after the test sheet."
    : "";
  saveState();
  render();
}

function markQuestionAttempted(questionId) {
  const item = practiceState(questionId);
  item.attempted = true;
  saveState();
  renderPractice();
}

function toggleQuestionHint(questionId) {
  const item = practiceState(questionId);
  item.hintOpen = !item.hintOpen;
  saveState();
  renderPractice();
}

function playVideoClip(lessonId, videoIndex) {
  state.videoPlayback[lessonId] = {
    activeIndex: Number(videoIndex) || 0,
    lastPlayed: new Date().toISOString(),
  };
  runtimePlayback[lessonId] = { loaded: true };
  saveState();
  renderLesson();
}

function setTextbookPage(lessonId, pageIndex) {
  state.textbookPage[lessonId] = pageIndex;
  saveState();
  renderLesson();
}

function toggleTextbookHighlight(sectionId, blockIndex) {
  const key = safeId(sectionId);
  state.textbookHighlights[key] = state.textbookHighlights[key] || [];
  const current = new Set(state.textbookHighlights[key]);
  if (current.has(blockIndex)) current.delete(blockIndex);
  else current.add(blockIndex);
  state.textbookHighlights[key] = [...current].sort((a, b) => a - b);
  saveState();
  renderLesson();
}

function render() {
  renderProgress();
  renderDashboard();
  renderLesson();
  renderPractice();
  renderReview();
  renderProfile();
  renderSources();
  showView(activeView);
}

function renderProgress() {
  const mastered = data.lessons.filter((lesson) => lessonState(lesson.id).mastery === "mastered").length;
  const percent = data.lessons.length ? Math.round((mastered / data.lessons.length) * 100) : 0;
  document.getElementById("courseProgressBar").style.width = `${percent}%`;
  document.getElementById("courseProgressText").textContent = `${percent}% mastered`;
}

function renderDashboard() {
  const lesson = nextLesson();
  const plan = planForPreferences();
  const learningReviewCount = learningReviewLessons().length;
  const setupCount = sourceSetupLessons().length;
  if (!lesson) {
    views.dashboard.innerHTML = emptyState("No class scheduled", "Add lesson anchors to the course folder and regenerate the app.");
    return;
  }
  views.dashboard.innerHTML = `
    <div class="dashboard-layout">
      <section class="pathway-context" aria-labelledby="pathwayContextTitle">
        <div>
          <p class="kicker">From curriculum to capability</p>
          <h2 id="pathwayContextTitle">A study app is one building block in a longer pathway.</h2>
        </div>
        <p>Keep the approved course as the anchor. Add aspiration, applied work, experience, and the outcome-specific gate that the learner is preparing for.</p>
        <div class="pathway-steps" aria-label="Pathway model">
          <span><b>01</b> foundations</span>
          <span><b>02</b> pathway practice</span>
          <span><b>03</b> credible evidence</span>
          <span><b>04</b> outcome gate</span>
        </div>
      </section>
      <section class="start-panel" aria-labelledby="startTitle">
        <p class="kicker">Today's class</p>
        <h2 id="startTitle">${escapeHtml(lesson.title)}</h2>
        <p class="recommendation-reason">${escapeHtml(plan.reason)}</p>
        <p class="lead">${escapeHtml(plan.dashboardHint)}</p>
        <ol class="session-steps">
          ${sessionSteps().map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
        </ol>
        <div class="action-row">
          <button class="button primary" type="button" data-action="${plan.primaryAction}">${escapeHtml(plan.primaryLabel)}</button>
          <button class="button secondary" type="button" data-action="profile">Set routine</button>
        </div>
        ${demoBanner()}
      </section>

      <aside class="today-panel" aria-label="Class plan">
        <h3>Class plan</h3>
        <dl class="stats-grid">
          <div><dt>Begin with</dt><dd>${escapeHtml(plan.primaryLabel)}</dd></div>
          <div><dt>Revision</dt><dd>${learningReviewCount ? `${learningReviewCount} pending` : "Clear"}</dd></div>
          <div><dt>Class material</dt><dd>${setupCount ? "Check references" : "Ready"}</dd></div>
          <div><dt>Routine</dt><dd>${escapeHtml(shortProfileLabel())}</dd></div>
        </dl>
      </aside>

      <section class="path-panel" aria-labelledby="pathTitle">
        <div class="section-heading compact">
          <p class="kicker">Course notebook</p>
          <h3 id="pathTitle">Open another class when you want to revise or move ahead</h3>
        </div>
        <div class="lesson-path">
          ${data.lessons.map((item) => lessonPathItem(item)).join("")}
        </div>
      </section>
    </div>
  `;
  bindActions(views.dashboard);
}

function renderLesson() {
  const lesson = activeLesson();
  const prefs = state.preferences;
  const sourceStatus = overallSourceState(lesson);
  const prompts = promptsForPreferences(lesson);
  const questions = practiceQuestionsForLesson(lesson).slice(0, questionLimitForPreferences());
  const attemptedVisible = questions.some((question, index) => {
    const id = safeId(question.question_id || `question_${index}`);
    return practiceState(id).attempted;
  });
  views.lesson.innerHTML = `
    <div class="lesson-workbench">
      <section class="lesson-hero" aria-labelledby="lessonTitle">
        <nav class="crumbs" aria-label="Lesson position">
          <button class="text-button" type="button" data-action="dashboard">Start</button>
          <span>${escapeHtml(lesson.module)}</span>
        </nav>
        <div class="lesson-hero-grid">
          <div>
            <p class="kicker">Class ${escapeHtml(String(lesson.order).padStart(2, "0"))}</p>
            <h2 id="lessonTitle">${escapeHtml(lesson.title)}</h2>
            <p class="lesson-summary">${escapeHtml(classroomIntro(lesson))}</p>
          </div>
          <div class="lesson-proof-strip" aria-label="Evidence available">
            <span>Textbook pages ${escapeHtml(String(lesson.textbook_evidence?.length || 0))}</span>
            <span>Board clips ${escapeHtml(String(lesson.video_evidence?.length || 0))}</span>
            <span>Test questions ${escapeHtml(String(lesson.question_evidence?.length || 0))}</span>
          </div>
        </div>
        ${sourceStatus.state !== "source_backed" ? inlineNotice(sourceStatus.message) : ""}
      </section>

      <div class="session-grid">
        <main class="session-main">
          ${videoSession(lesson)}

          <section class="textbook-panel" aria-labelledby="textbookTitle">
            <div class="session-section-heading">
              <span class="step-label">Textbook</span>
              <h3 id="textbookTitle">Read this after the board explanation</h3>
              <p>Underline the sentence that explains the rule. Copy only the part you would want in your notebook.</p>
            </div>
            ${textbookReader(lesson)}
          </section>

          <section class="prompt-panel" aria-labelledby="promptsTitle">
            <div class="session-section-heading">
              <span class="step-label">Notebook check</span>
              <h3 id="promptsTitle">Write this in your own words</h3>
            </div>
            <div class="prompt-list">
              ${prompts.map((prompt) => `<p>${escapeHtml(prompt)}</p>`).join("")}
            </div>
            ${prefs.supportLevel === "guided" ? guidedPromptList(lesson) : ""}
          </section>

          <section class="practice-panel" aria-labelledby="lessonPracticeTitle">
            <div class="session-section-heading">
              <span class="step-label">Test paper</span>
              <h3 id="lessonPracticeTitle">Now solve these GATE questions</h3>
              <p>${escapeHtml(practiceHintForPreferences())}</p>
            </div>
            ${questionSourceState(lesson).state !== "source_backed" ? inlineNotice(questionSourceState(lesson).message) : ""}
            ${questions.map((question, index) => questionCard(question, index)).join("")}
            <section class="confidence-panel compact-confidence" aria-labelledby="lessonConfidenceTitle">
              <h3 id="lessonConfidenceTitle">Tell the teacher what to revise</h3>
              <p>${attemptedVisible ? "Mark how this class went after you have tried the test sheet." : "Solve at least one question first. Then mark whether this class needs revision."}</p>
              <div class="confidence-grid">
                <button class="button" type="button" data-confidence="review_needed" ${attemptedVisible ? "" : "disabled"}>Revise again</button>
                <button class="button" type="button" data-confidence="practiced" ${attemptedVisible ? "" : "disabled"}>Needs practice</button>
                <button class="button primary" type="button" data-confidence="mastered" ${attemptedVisible ? "" : "disabled"}>Clear for now</button>
              </div>
            </section>
          </section>
        </main>

        <aside class="session-sidebar" aria-label="Lesson workspace">
          <section class="notes-card">
            <label for="lessonNotes">Notebook</label>
            <textarea id="lessonNotes" rows="10" placeholder="Write the rule, exception, reaction pattern, or mistake you want to remember.">${escapeHtml(state.notes[lesson.id] || "")}</textarea>
            <button class="button small" type="button" id="saveNotes">Save notebook</button>
            <p class="microcopy" id="notesStatus" role="status"></p>
          </section>
          <section class="lesson-map-card">
            <h3>Teacher's order</h3>
            ${loopStep("Listen at the board", hasVideoEvidence(lesson), hasVideoEvidence(lesson) ? "Teaching clip ready" : "Board clip pending")}
            ${loopStep("Open the textbook", hasTextbookEvidence(lesson), hasTextbookEvidence(lesson) ? "Chapter section ready" : "Textbook pending")}
            ${loopStep("Write notes", true, "Use your own words")}
            ${loopStep("Solve test paper", hasQuestionEvidence(lesson), questionSourceState(lesson).label)}
            <div class="action-row sidebar-actions">
              <button class="button secondary" type="button" data-action="sources">References</button>
              <button class="button secondary" type="button" data-action="next">Next class</button>
            </div>
          </section>
        </aside>
      </div>
    </div>
  `;
  bindActions(views.lesson);
  views.lesson.querySelectorAll("[data-play-video]").forEach((button) => {
    button.addEventListener("click", () => playVideoClip(lesson.id, button.dataset.playVideo));
  });
  views.lesson.querySelectorAll("[data-textbook-page]").forEach((button) => {
    button.addEventListener("click", () => setTextbookPage(lesson.id, Number(button.dataset.textbookPage)));
  });
  views.lesson.querySelectorAll("[data-highlight-block]").forEach((button) => {
    button.addEventListener("click", () => toggleTextbookHighlight(button.dataset.sectionId, Number(button.dataset.highlightBlock)));
  });
  views.lesson.querySelectorAll("[data-save-section-note]").forEach((button) => {
    button.addEventListener("click", () => {
      const sectionId = button.dataset.saveSectionNote;
      const input = views.lesson.querySelector(`[data-section-note="${sectionId}"]`);
      const status = views.lesson.querySelector(`[data-section-note-status="${sectionId}"]`);
      state.textbookNotes[sectionId] = input.value;
      saveState();
      status.textContent = "Section note saved.";
    });
  });
  views.lesson.querySelectorAll("[data-attempt-question]").forEach((button) => {
    button.addEventListener("click", () => markQuestionAttempted(button.dataset.attemptQuestion));
  });
  views.lesson.querySelectorAll("[data-hint-question]").forEach((button) => {
    button.addEventListener("click", () => toggleQuestionHint(button.dataset.hintQuestion));
  });
  views.lesson.querySelectorAll("[data-confidence]").forEach((button) => {
    button.addEventListener("click", () => updateMastery(lesson.id, button.dataset.confidence));
  });
  views.lesson.querySelector("#saveNotes").addEventListener("click", () => {
    state.notes[lesson.id] = views.lesson.querySelector("#lessonNotes").value;
    saveState();
    views.lesson.querySelector("#notesStatus").textContent = "Notebook saved on this browser.";
  });
}

function renderPractice() {
  const lesson = activeLesson();
  const questions = practiceQuestionsForLesson(lesson);
  const visibleQuestions = questions.slice(0, questionLimitForPreferences());
  const attemptedVisible = visibleQuestions.some((question, index) => {
    const id = safeId(question.question_id || `question_${index}`);
    return practiceState(id).attempted;
  });
  views.practice.innerHTML = `
    <div class="practice-layout">
      <section class="study-panel" aria-labelledby="practiceTitle">
        <p class="kicker">Test paper</p>
        <h2 id="practiceTitle">${escapeHtml(lesson.title)}</h2>
        <p class="lead">${escapeHtml(practiceHintForPreferences())}</p>
        ${questionSourceState(lesson).state !== "source_backed" ? inlineNotice(questionSourceState(lesson).message) : ""}
        ${visibleQuestions.map((question, index) => questionCard(question, index)).join("")}
        <section class="confidence-panel" aria-labelledby="confidenceTitle">
          <h3 id="confidenceTitle">Hand in your self-check</h3>
          <p>${attemptedVisible ? "Tell the teacher whether this class should come back in revision." : "Attempt one question first. Then mark the class honestly."}</p>
          <div class="confidence-grid">
            <button class="button" type="button" data-confidence="review_needed" ${attemptedVisible ? "" : "disabled"}>Revise again</button>
            <button class="button" type="button" data-confidence="practiced" ${attemptedVisible ? "" : "disabled"}>Needs practice</button>
            <button class="button primary" type="button" data-confidence="mastered" ${attemptedVisible ? "" : "disabled"}>Clear for now</button>
          </div>
        </section>
      </section>
    </div>
  `;
  views.practice.querySelectorAll("[data-attempt-question]").forEach((button) => {
    button.addEventListener("click", () => markQuestionAttempted(button.dataset.attemptQuestion));
  });
  views.practice.querySelectorAll("[data-hint-question]").forEach((button) => {
    button.addEventListener("click", () => toggleQuestionHint(button.dataset.hintQuestion));
  });
  views.practice.querySelectorAll("[data-confidence]").forEach((button) => {
    button.addEventListener("click", () => updateMastery(lesson.id, button.dataset.confidence));
  });
}

function renderReview() {
  const learning = learningReviewLessons();
  const setup = sourceSetupLessons();
  views.review.innerHTML = `
    <div class="single-column">
      <div class="section-heading">
        <p class="kicker">Revision</p>
        <h2>Return to classes that need another pass</h2>
        <p class="lead">Anything you mark after the test paper comes here. Treat it like the teacher asking you to revise before moving on.</p>
      </div>

      <section class="review-section" aria-labelledby="learningReviewTitle">
        <div class="section-heading compact">
          <h3 id="learningReviewTitle">Revision list</h3>
        </div>
        <div class="lesson-list">
          ${learning.length ? learning.map((lesson) => reviewCard(lesson, learningReviewReason(lesson), "Revise class")).join("") : emptyState("No revision pending", "Mark a class for revision after the test paper and it will appear here.")}
        </div>
      </section>

      <section class="review-section" aria-labelledby="setupReviewTitle">
        <div class="section-heading compact">
          <h3 id="setupReviewTitle">Reference watchlist</h3>
        </div>
        <div class="lesson-list">
          ${setup.length ? setup.map((lesson) => reviewCard(lesson, sourceSetupReason(lesson), "Check references", "sources")).join("") : emptyState("References ready", "Every class has linked textbook, board, and test material.")}
        </div>
      </section>
    </div>
  `;
  views.review.querySelectorAll("[data-lesson-id]").forEach((button) => {
    setButtonLessonHandler(button);
  });
}

function renderProfile() {
  const prefs = state.preferences;
  views.profile.innerHTML = `
    <div class="single-column">
      <div class="section-heading">
        <p class="kicker">Routine</p>
        <h2>Tell the teacher how to run today's class</h2>
        <p class="lead">Choose the pace and order. The syllabus and references stay fixed; only the classroom routine changes.</p>
      </div>
      <form class="profile-form" id="profileForm">
        ${preferenceGroup("goal", "Class goal", prefs.goal, [
          ["exam_readiness", "Exam readiness", "Spend more time on test paper and revision."],
          ["concept_depth", "Concept depth", "Spend more time with the board and textbook."],
          ["catch_up", "Catch up", "Keep the class short and direct."]
        ])}
        ${preferenceGroup("supportLevel", "Teacher support", prefs.supportLevel, [
          ["guided", "Guided", "Break the class into smaller instructions."],
          ["balanced", "Balanced", "Use the normal board, textbook, notebook, test order."],
          ["independent", "Independent", "Move faster toward the test paper."]
        ])}
        ${preferenceGroup("sessionLength", "Class length", prefs.sessionLength, [
          ["short", "Short", "One board segment and one question."],
          ["standard", "Standard", "Board, textbook, notebook, and test sheet."],
          ["deep", "Deep", "More textbook reading and notebook work."]
        ])}
        ${preferenceGroup("practiceOrder", "Class order", prefs.practiceOrder, [
          ["learn_then_practice", "Board first", "Listen, read, write notes, then solve."],
          ["practice_first", "Test first", "Try a question first, then return to the board."],
          ["review_first", "Revision first", "Start with a class you previously marked for revision."]
        ])}
        ${preferenceGroup("sourceDetail", "Reference detail", prefs.sourceDetail, [
          ["essential", "Essential", "Show only the reference needed for class."],
          ["full", "Full", "Show fuller textbook and citation context."]
        ])}
        <div class="profile-impact">
          <h3>How class changes</h3>
          <p>${escapeHtml(profileImpactText())}</p>
          <button class="button secondary" type="button" data-action="reset-profile">Reset defaults</button>
        </div>
      </form>
    </div>
  `;
  views.profile.querySelectorAll("[data-pref]").forEach((input) => {
    input.addEventListener("change", () => {
      state.preferences[input.dataset.pref] = input.value;
      saveState();
      render();
    });
  });
  bindActions(views.profile);
}

function renderSources() {
  const lesson = activeLesson();
  views.sources.innerHTML = `
    <div class="study-layout">
      <section class="study-panel" aria-labelledby="sourcesTitle">
        <p class="kicker">References</p>
        <h2 id="sourcesTitle">${escapeHtml(lesson.title)}</h2>
        <p class="lead">Use this like the back of the classroom handout: syllabus line, textbook section, board clip, and test paper reference.</p>
        ${overallSourceState(lesson).state !== "source_backed" ? demoBanner() : ""}
        <div class="source-stack">
          ${sourceSection("Syllabus", [{
            text_preview: lesson.syllabus_anchor,
            citation_label: "Course syllabus anchor",
            source_state: "source_backed",
          }], "Syllabus anchor missing.", "syllabus")}
          ${sourceSection("Textbook", lesson.textbook_evidence, "Textbook section is not ready yet.", "textbook")}
          ${sourceSection("Video", lesson.video_evidence, "Board clip is not ready yet.", "video")}
          ${sourceSection("Practice", lesson.question_evidence, "Practice questions are not linked yet.", "questions")}
        </div>
      </section>
      <aside class="next-panel" aria-label="Course reference map">
        <h3>Reference map</h3>
        ${data.lessons.map((item) => `
          <button class="source-row" type="button" data-lesson-id="${escapeHtml(item.id)}" data-target-view="sources">
            <span>${escapeHtml(item.title)}</span>
            <strong>${escapeHtml(overallSourceState(item).label)}</strong>
          </button>
        `).join("")}
      </aside>
    </div>
  `;
  views.sources.querySelectorAll("[data-lesson-id]").forEach((button) => {
    setButtonLessonHandler(button);
  });
}

function demoBanner() {
  const allSourcesReady = data.lessons.every((lesson) => (
    lesson.readiness?.source_integrity_state === "source_backed"
  ));
  const allVideosReady = data.lessons.every((lesson) => (
    lesson.readiness?.source_states?.video?.state === "source_backed"
  ));
  const message = allSourcesReady
    ? "Class material is ready: syllabus, textbook, board clips, and test questions are linked."
    : allVideosReady
      ? "Board clips are ready. Any reference that still needs setup is marked clearly."
      : "Some class material still needs setup before it should be used as a complete classroom pack.";
  return `
    <div class="demo-banner" role="status">
      <strong>Class material</strong>
      <span>${escapeHtml(message)}</span>
    </div>
  `;
}

function inlineNotice(message) {
  return `<div class="inline-notice" role="status">${escapeHtml(message)}</div>`;
}

function lessonPathItem(lesson) {
  const mastery = lessonState(lesson.id).mastery;
  const sourceState = overallSourceState(lesson);
  return `
    <button class="path-item ${lesson.id === activeLessonId ? "active" : ""}" type="button" data-lesson-id="${escapeHtml(lesson.id)}">
      <span class="path-index">${lesson.order}</span>
      <span>
        <strong>${escapeHtml(lesson.title)}</strong>
        <small>${escapeHtml(labelForState(mastery))} · ${escapeHtml(referenceLabel(sourceState))}</small>
      </span>
    </button>
  `;
}

function questionCard(question, index) {
  const id = safeId(question.question_id || `question_${index}`);
  const item = practiceState(id);
  const placeholder = isPlaceholderItem(question) || question.source_state === "demo_placeholder";
  return `
    <article class="question-card">
      <div class="question-topline">
        <span class="step-label">Question ${index + 1}</span>
        <span class="source-marker ${placeholder ? "demo_placeholder" : "source_backed"}">${placeholder ? "Reference pending" : "Official question"}</span>
      </div>
      <p>${escapeHtml(question.prompt_preview || question.prompt || "Question is not linked yet.")}</p>
      ${item.hintOpen ? `<div class="hint-panel">Go back to the board first. Name the rule before you look for the answer.</div>` : ""}
      <div class="action-row compact-actions">
        <button class="button primary" type="button" data-attempt-question="${id}">${item.attempted ? "Answer marked" : "I solved this"}</button>
        <button class="button secondary" type="button" data-hint-question="${id}">${item.hintOpen ? "Hide hint" : "Teacher hint"}</button>
      </div>
      ${item.attempted ? practiceFeedback(question, placeholder) : `<p class="microcopy">Solve it in your notebook before marking it here.</p>`}
    </article>
  `;
}

function practiceFeedback(question, placeholder) {
  const text = question.answer_preview
    || (placeholder
      ? "The full solution reference is not linked yet. Do not guess the explanation."
      : "Check the reference line and compare it with your notebook work.");
  return `
    <div class="answer-panel visible">
      <h4>Teacher note</h4>
      <p>${escapeHtml(text)}</p>
      <p class="citation">${escapeHtml(question.citation_label || "Question reference not linked yet.")}${evidenceMeta(question) ? ` · ${escapeHtml(evidenceMeta(question))}` : ""}</p>
    </div>
  `;
}

function reviewCard(lesson, reason, label, targetView = "lesson") {
  return `
    <article class="review-card">
      <div>
        <h3>${escapeHtml(lesson.title)}</h3>
        <p>${escapeHtml(reason)}</p>
      </div>
      <button class="button" type="button" data-lesson-id="${escapeHtml(lesson.id)}" data-target-view="${escapeHtml(targetView)}">${escapeHtml(label)}</button>
    </article>
  `;
}

function sourceSection(label, items, missingText, sourceKey) {
  const stateForBucket = sourceBucketState(activeLesson(), sourceKey);
  if (!items.length) {
    return `
      <section class="source-section">
        <div class="source-section-title">
          <h3>${escapeHtml(label)}</h3>
          ${stateBadge({ state: "needs_processing", label: "Needs processing" })}
        </div>
        <p class="muted">${escapeHtml(missingText)}</p>
      </section>
    `;
  }
  return `
    <section class="source-section">
      <div class="source-section-title">
        <h3>${escapeHtml(label)}</h3>
        ${stateBadge(stateForBucket)}
      </div>
      ${items.map((item, index) => sourceCard(item, label, index, stateForBucket)).join("")}
    </section>
  `;
}

function sourceCard(item, label, index, bucketState) {
  const detail = state.preferences.sourceDetail === "full";
  const body = item.text_preview || item.prompt_preview || item.transcript_preview || item.note || bucketState.message || "Linked class reference.";
  const citation = item.citation_label || (bucketState.state === "source_backed" ? "Processed course source" : bucketState.label);
  const meta = evidenceMeta(item);
  return `
    <article class="source-card">
      <div class="source-card-head">
        <span class="source-marker ${escapeHtml(bucketState.state)}">${escapeHtml(bucketState.label)}</span>
        <h4>${escapeHtml(`${label} reference ${index + 1}`)}</h4>
      </div>
      <p>${escapeHtml(detail ? body : compactText(body))}</p>
      <p class="citation">${escapeHtml(citation)}${meta ? ` · ${escapeHtml(meta)}` : ""}${item.timestamp_label && bucketState.state === "source_backed" ? ` · ${escapeHtml(item.timestamp_label)}` : ""}</p>
    </article>
  `;
}

function videoSession(lesson) {
  const videos = (lesson.video_evidence || []).filter((video) => (
    video.evidence_mode === "videodb_spoken_word_search"
    && video.timestamp_start !== null
    && video.timestamp_start !== undefined
  ));
  if (!videos.length) {
    return `
      <section class="video-session" aria-labelledby="videoTitle">
        <div class="session-section-heading">
          <span class="step-label">Blackboard</span>
          <h3 id="videoTitle">The teacher has not reached the board yet</h3>
          <p>VideoDB has not returned a lesson-matched teaching moment for this class yet.</p>
        </div>
      </section>
    `;
  }
  const playback = state.videoPlayback[lesson.id] || { activeIndex: 0 };
  const loaded = Boolean(runtimePlayback[lesson.id]?.loaded);
  const activeIndex = Math.min(Number(playback.activeIndex) || 0, videos.length - 1);
  const activeVideo = videos[activeIndex];
  const embedUrl = loaded ? videoEmbedUrl(activeVideo) : "";
  return `
    <section class="video-session" aria-labelledby="videoTitle">
      <div class="session-section-heading">
        <span class="step-label">Blackboard</span>
        <h3 id="videoTitle">Listen from this board moment</h3>
        <p>Play the teaching segment. Pause when the rule appears, then write it in your notebook.</p>
      </div>
      <div class="video-grid">
        <div class="video-stage ${embedUrl ? "has-embed" : ""}">
          ${embedUrl ? `
            <iframe title="${escapeHtml(activeVideo.title || "Video lesson")}" src="${escapeHtml(embedUrl)}" allow="encrypted-media; picture-in-picture" allowfullscreen></iframe>
          ` : `
            <button class="video-placeholder" type="button" data-play-video="${activeIndex}" aria-label="Load board clip from ${escapeHtml(activeVideo.timestamp_label || timeLabel(activeVideo.timestamp_start))}">
              <span class="play-symbol" aria-hidden="true"></span>
              <p>${escapeHtml(activeVideo.title || "Video lesson")}</p>
              <small>${escapeHtml(activeVideo.timestamp_label || timeLabel(activeVideo.timestamp_start))} · VideoDB match ${escapeHtml(activeVideo.video_id || "linked")}</small>
            </button>
          `}
        </div>
        <aside class="timestamp-panel" aria-label="Board moments to watch">
          <div class="timestamp-panel-head">
            <h4>Board moments</h4>
            <span>${escapeHtml(String(videos.length))} clip${videos.length === 1 ? "" : "s"}</span>
          </div>
          <div class="timestamp-list">
            ${videos.map((video, index) => timestampCard(video, index, index === activeIndex && loaded)).join("")}
          </div>
        </aside>
      </div>
    </section>
  `;
}

function timestampCard(video, index, active) {
  const url = timestampedVideoUrl(video);
  const detail = compactText(video.transcript_preview || "VideoDB matched this board moment to the lesson.");
  return `
    <article class="timestamp-card ${active ? "active" : ""}">
      <button class="timestamp-play" type="button" data-play-video="${index}">
        <span>${escapeHtml(video.timestamp_label || timeLabel(video.timestamp_start))}</span>
        <strong>${active ? "Loaded" : "Load"}</strong>
      </button>
      <p>${escapeHtml(detail)}</p>
      <small>VideoDB spoken-word match · ${escapeHtml(video.citation_label || video.title || "Board clip")}</small>
      ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Open board clip</a>` : ""}
    </article>
  `;
}

function textbookCard(item) {
  return `
    <article class="textbook-card">
      <div class="textbook-meta">
        <span>${escapeHtml(item.section_title || "Textbook section")}</span>
        <strong>${escapeHtml(item.page ? `p. ${item.page}` : "section reference")}</strong>
      </div>
      <p>${escapeHtml(item.text_preview || "Textbook extract is linked for this lesson.")}</p>
      <footer>
        <span>${escapeHtml(item.citation_label || "Textbook source")}</span>
        ${item.license ? `<span>${escapeHtml(item.license)}</span>` : ""}
      </footer>
    </article>
  `;
}

function textbookReader(lesson) {
  const pages = lesson.textbook_evidence || [];
  if (!pages.length) {
    return `<article class="textbook-empty">Textbook page is not ready for this class.</article>`;
  }
  const current = Math.min(Math.max(Number(state.textbookPage[lesson.id]) || 0, 0), pages.length - 1);
  const item = pages[current];
  const sectionId = item.chunk_id || item.section_title || `${lesson.id}_${current}`;
  const safeSectionId = safeId(sectionId);
  return `
    <div class="textbook-reader">
      <div class="textbook-toolbar" aria-label="Textbook navigation">
        <button class="button small" type="button" data-textbook-page="${Math.max(0, current - 1)}" ${current === 0 ? "disabled" : ""}>Previous page</button>
        <span>Page ${current + 1} of ${pages.length}</span>
        <button class="button small" type="button" data-textbook-page="${Math.min(pages.length - 1, current + 1)}" ${current === pages.length - 1 ? "disabled" : ""}>Next page</button>
      </div>
      <article class="textbook-page">
        <header class="textbook-page-head">
          <div>
            <p class="kicker">OpenStax Organic Chemistry</p>
            <h4>${escapeHtml(item.section_title || "Textbook section")}</h4>
          </div>
          <span>${escapeHtml(String(textbookBlocks(item).length))} blocks</span>
        </header>
        <div class="textbook-page-body">
          ${renderTextbookBlocks(item, safeSectionId)}
        </div>
        <footer>
          <span>${escapeHtml(item.attribution || item.citation_label || "Organic Chemistry by John McMurry, OpenStax, licensed CC BY-NC-SA 4.0.")}</span>
          <span>Access for free at OpenStax.</span>
          ${item.license ? `<span>${escapeHtml(item.license)}</span>` : ""}
          ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">Source</a>` : ""}
        </footer>
      </article>
      <section class="section-note-card">
        <label for="sectionNote_${escapeHtml(safeSectionId)}">Margin note for this textbook section</label>
        <textarea id="sectionNote_${escapeHtml(safeSectionId)}" rows="4" data-section-note="${escapeHtml(safeSectionId)}" placeholder="Write the side-note you would put in the margin of the textbook.">${escapeHtml(state.textbookNotes[safeSectionId] || "")}</textarea>
        <button class="button small" type="button" data-save-section-note="${escapeHtml(safeSectionId)}">Save section note</button>
        <p class="microcopy" data-section-note-status="${escapeHtml(safeSectionId)}" role="status"></p>
      </section>
    </div>
  `;
}

function renderTextbookBlocks(item, safeSectionId) {
  const blocks = textbookBlocks(item);
  const saved = new Set(state.textbookHighlights[safeSectionId] || []);
  const firstReadable = blocks.findIndex((block) => blockText(block).length > 0 && block.type !== "heading");
  return blocks.map((block, index) => {
    if (block.type === "heading") {
      return `<h5 class="textbook-subhead">${escapeHtml(block.text || "")}</h5>`;
    }
    const teacherMarked = index === firstReadable;
    const studentMarked = saved.has(index);
    const className = [
      "textbook-block",
      teacherMarked ? "teacher-marked" : "",
      studentMarked ? "student-marked" : "",
      block.type === "figure" ? "figure-block" : "",
      block.type === "list" ? "list-block" : "",
      block.type === "note" ? "note-block" : "",
    ].filter(Boolean).join(" ");
    const label = studentMarked ? "Remove highlight" : "Highlight";
    return `
      <article class="${className}">
        ${renderTextbookBlockBody(block)}
        <button class="highlight-control" type="button" data-section-id="${escapeHtml(safeSectionId)}" data-highlight-block="${index}">
          ${teacherMarked ? "Teacher marked" : label}
        </button>
      </article>
    `;
  }).join("");
}

function textbookBlocks(item) {
  const blocks = Array.isArray(item.content_blocks) ? item.content_blocks.filter((block) => blockText(block)) : [];
  if (blocks.length) return blocks;
  return splitSentences(item.full_text || item.text_preview || "Textbook section preview is not available.")
    .map((text) => ({ type: "paragraph", text }));
}

function renderTextbookBlockBody(block) {
  if (block.type === "figure") {
    return `
      ${block.image_url ? `<img src="${escapeHtml(block.image_url)}" alt="${escapeHtml(block.alt || block.caption || "OpenStax figure")}" loading="lazy">` : ""}
      <p>${escapeHtml(block.caption || blockText(block))}</p>
    `;
  }
  if (block.type === "list") {
    const tag = block.ordered ? "ol" : "ul";
    const items = (block.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    return `<${tag}>${items}</${tag}>`;
  }
  if (block.type === "note") {
    return `
      <strong>${escapeHtml(block.title || "Note")}</strong>
      <p>${escapeHtml(block.text || "")}</p>
    `;
  }
  return `<p>${escapeHtml(block.text || blockText(block))}</p>`;
}

function blockText(block) {
  if (!block) return "";
  if (block.text) return String(block.text).trim();
  if (block.caption) return String(block.caption).trim();
  if (Array.isArray(block.items)) return block.items.join(" ").trim();
  return "";
}

function splitSentences(text) {
  const parts = String(text || "").match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
  return parts.map((part) => part.trim()).filter(Boolean);
}

function evidenceMeta(item) {
  const parts = [];
  if (item.section_title) parts.push(item.section_title);
  if (item.year) parts.push(String(item.year));
  if (item.page) parts.push(`p. ${item.page}`);
  if (item.license) parts.push(item.license);
  return parts.join(" · ");
}

function videoEmbedUrl(video) {
  const sourceUrl = video.source_url || video.url;
  const youtubeId = youtubeVideoId(sourceUrl);
  if (!youtubeId) return "";
  const start = Math.max(0, Math.floor(Number(video.timestamp_start) || 0));
  const params = new URLSearchParams({
    start: String(start),
    rel: "0",
    modestbranding: "1",
  });
  return `https://www.youtube.com/embed/${youtubeId}?${params.toString()}`;
}

function timestampedVideoUrl(video) {
  const sourceUrl = video.source_url || video.url;
  if (!sourceUrl) return "";
  try {
    const url = new URL(sourceUrl);
    const start = Math.max(0, Math.floor(Number(video.timestamp_start) || 0));
    if (url.hostname.includes("youtube.com")) {
      url.searchParams.set("t", `${start}s`);
      return url.toString();
    }
    if (url.hostname.includes("youtu.be")) {
      url.searchParams.set("t", `${start}s`);
      return url.toString();
    }
    return url.toString();
  } catch (_error) {
    return "";
  }
}

function youtubeVideoId(sourceUrl) {
  if (!sourceUrl) return "";
  try {
    const url = new URL(sourceUrl);
    if (url.hostname.includes("youtu.be")) return url.pathname.replace("/", "");
    if (url.hostname.includes("youtube.com")) return url.searchParams.get("v") || "";
    return "";
  } catch (_error) {
    return "";
  }
}

function timeLabel(value) {
  const total = Math.max(0, Math.floor(Number(value) || 0));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function loopStep(label, available, note) {
  return `
    <div class="loop-step ${available ? "available" : "pending"}">
      <span aria-hidden="true"></span>
      <div><strong>${escapeHtml(label)}</strong><small>${escapeHtml(note)}</small></div>
    </div>
  `;
}

function preferenceGroup(name, label, selected, options) {
  return `
    <fieldset class="preference-group">
      <legend>${escapeHtml(label)}</legend>
      <div class="preference-grid">
        ${options.map(([value, optionLabel, description]) => `
          <label class="preference-option">
            <input type="radio" name="${escapeHtml(name)}" value="${escapeHtml(value)}" data-pref="${escapeHtml(name)}" ${selected === value ? "checked" : ""}>
            <span>
              <strong>${escapeHtml(optionLabel)}</strong>
              <small>${escapeHtml(description)}</small>
            </span>
          </label>
        `).join("")}
      </div>
    </fieldset>
  `;
}

function emptyState(title, text) {
  return `<article class="empty-state"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(text)}</p></article>`;
}

function stateBadge(sourceState) {
  return `<span class="status-pill ${escapeHtml(sourceState.state)}">${escapeHtml(sourceState.label)}</span>`;
}

function referenceLabel(sourceState) {
  if (sourceState.state === "source_backed") return "references ready";
  if (sourceState.state === "demo_placeholder") return "references pending";
  if (sourceState.state === "needs_processing") return "setup needed";
  return "reference unavailable";
}

function bindActions(root) {
  root.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });
  root.querySelectorAll("[data-lesson-id]").forEach((button) => {
    setButtonLessonHandler(button);
  });
}

function setButtonLessonHandler(button) {
  button.addEventListener("click", () => setLesson(button.dataset.lessonId, button.dataset.targetView || "lesson"));
}

function bindGlobalNavigation() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view));
  });
}

function runAction(action) {
  if (action === "dashboard") showView("dashboard");
  if (action === "continue") setLesson(nextLesson().id, "lesson");
  if (action === "practice") showView("practice");
  if (action === "profile") showView("profile");
  if (action === "sources") showView("sources");
  if (action === "review") showView("review");
  if (action === "next") setLesson(nextAfter(activeLessonId).id, "lesson");
  if (action === "reset-profile") {
    state.preferences = { ...defaultPreferences };
    saveState();
    render();
  }
}

function sessionSteps() {
  const prefs = state.preferences;
  if (prefs.practiceOrder === "practice_first") {
    return prefs.sessionLength === "short"
      ? ["Try one test question", "Mark whether to revise"]
      : ["Try one test question first", "Return to the board where you got stuck", "Mark whether to revise"];
  }
  if (prefs.practiceOrder === "review_first") {
    return ["Revise one old class", "Solve one test question", "Then open new material"];
  }
  if (prefs.sessionLength === "short") {
    return ["Listen to one board segment", "Write one notebook line", "Solve one question"];
  }
  if (prefs.sessionLength === "deep") {
    return ["Listen at the board", "Read the textbook", "Write notebook notes", "Solve the test sheet", "Mark revision"];
  }
  return ["Listen at the board", "Read the textbook", "Write notes", "Solve questions"];
}

function planForPreferences() {
  const prefs = state.preferences;
  const learningReviews = learningReviewLessons();
  if (prefs.practiceOrder === "practice_first") {
    return {
      primaryAction: "practice",
      primaryLabel: "Start with test",
      dashboardHint: "Try the test paper first. Then come back to the board for the part you could not solve.",
      reason: "Teacher's order today: test first, then explanation.",
    };
  }
  if (prefs.practiceOrder === "review_first" && learningReviews.length) {
    return {
      primaryAction: "review",
      primaryLabel: "Revise first",
      dashboardHint: "Start with the class you marked for revision before opening new material.",
      reason: `${learningReviews.length} class${learningReviews.length === 1 ? "" : "es"} need revision before you move on.`,
    };
  }
  return {
    primaryAction: "continue",
    primaryLabel: "Enter class",
    dashboardHint: prefs.sessionLength === "short"
      ? "Keep it short: one board segment, one notebook line, one question."
      : "Follow the classroom order: board, textbook, notebook, test paper.",
    reason: "The next class is ready.",
  };
}

function studyHeadingForPreferences() {
  if (state.preferences.supportLevel === "guided") return "Teacher-led class";
  if (state.preferences.supportLevel === "independent") return "Fast class";
  return "Class order";
}

function classroomIntro(lesson) {
  const subject = lesson.title || "this topic";
  if (state.preferences.supportLevel === "guided") {
    return `Today the teacher takes charge of ${subject}. Listen at the board first, write the rule in your notebook, then open the textbook and solve.`;
  }
  if (state.preferences.practiceOrder === "practice_first") {
    return `Start with the test paper for ${subject}. When you get stuck, return to the board and textbook with a clear doubt.`;
  }
  return `Take this like a classroom lesson on ${subject}: board explanation first, textbook support next, notebook in your own words, then GATE questions.`;
}

function studyPathForPreferences() {
  const prefs = state.preferences;
  if (prefs.supportLevel === "guided") {
    return "Listen first, pause often, write one line in your notebook, then solve.";
  }
  if (prefs.supportLevel === "independent") {
    return "Try the test paper early. Return to the board only where your reasoning breaks.";
  }
  if (prefs.goal === "catch_up") {
    return "Finish one clean class loop. Leave deep textbook reading for later.";
  }
  if (prefs.goal === "concept_depth") {
    return "Spend more time with the textbook and notebook before solving.";
  }
  return "Listen at the board, read the textbook, write notes, then solve.";
}

function guidedPromptList(lesson) {
  return `
    <ul class="support-list">
      <li>Pause the board clip when the rule is introduced.</li>
      <li>Copy the rule in your own words, not as a transcript.</li>
      <li>Use References only when you need the chapter, section, or source line.</li>
    </ul>
  `;
}

function promptsForPreferences(lesson) {
  const prompts = lesson.review_prompts || [];
  if (state.preferences.sessionLength === "short") return prompts.slice(0, 1);
  if (state.preferences.sessionLength === "deep") {
    return [...prompts, "Which textbook line would you highlight before leaving this class?"];
  }
  return prompts;
}

function practiceHintForPreferences() {
  const prefs = state.preferences;
  if (prefs.practiceOrder === "practice_first") return "Solve first. Let the wrong step tell you what to listen for at the board.";
  if (prefs.sessionLength === "short") return "Solve one question. A short class still needs an answer on paper.";
  if (prefs.sessionLength === "deep") return "Solve, then compare your notebook with the textbook reference.";
  if (prefs.goal === "concept_depth") return "After answering, write which rule from the class supported your answer.";
  return "Treat this like a classroom test sheet. Solve before checking the teacher note.";
}

function profileImpactText() {
  const prefs = state.preferences;
  const changes = [];
  if (prefs.practiceOrder === "practice_first") changes.push("Class starts with the test paper");
  if (prefs.practiceOrder === "review_first") changes.push("Revision comes before new teaching when anything is pending");
  if (prefs.sessionLength === "short") changes.push("The teacher keeps the class to one board segment and one question");
  if (prefs.sessionLength === "deep") changes.push("The teacher adds more textbook and notebook work");
  if (prefs.supportLevel === "guided") changes.push("Instructions become smaller and more explicit");
  if (prefs.supportLevel === "independent") changes.push("You move faster toward the test paper");
  if (prefs.sourceDetail === "full") changes.push("References show fuller textbook and citation context");
  return changes.length ? `${changes.join(". ")}.` : "Default class order is board, textbook, notebook, test paper.";
}

function questionLimitForPreferences() {
  if (state.preferences.sessionLength === "short") return 1;
  if (state.preferences.sessionLength === "deep") return 4;
  return 2;
}

function practiceQuestionsForLesson(lesson) {
  if (lesson.question_evidence?.length) return lesson.question_evidence;
  return [{
    question_id: `${lesson.id}_missing`,
    prompt_preview: "Questions are not linked yet.",
    citation_label: "Question reference incomplete",
    source_state: "needs_processing",
  }];
}

function hasAttemptedPractice(lesson) {
  return practiceQuestionsForLesson(lesson).some((question, index) => {
    const id = safeId(question.question_id || `question_${index}`);
    return practiceState(id).attempted;
  });
}

function overallSourceState(lesson) {
  const explicit = lesson.readiness?.source_integrity_state;
  if (explicit) {
    const state = explicit;
    return {
      state,
      label: sourceLabels[state] || labelForState(state),
      message: messageForState(state),
    };
  }
  if (hasPlaceholderEvidence(lesson)) {
    return {
      state: "demo_placeholder",
      label: "Demo placeholder",
      message: "This lesson uses bundled placeholders. Regenerate after processing the real sources.",
    };
  }
  return {
    state: lesson.readiness?.state === "ready" ? "source_backed" : "needs_processing",
    label: lesson.readiness?.state === "ready" ? "References ready" : "Needs setup",
    message: lesson.readiness?.missing_messages?.[0] || "Source setup is incomplete.",
  };
}

function sourceBucketState(lesson, key) {
  const explicit = lesson.readiness?.source_states?.[key];
  if (explicit) return explicit;
  const fallback = key === "questions" ? questionSourceState(lesson) : overallSourceState(lesson);
  return fallback;
}

function questionSourceState(lesson) {
  const explicit = lesson.readiness?.source_states?.questions;
  if (explicit) return explicit;
  if (!lesson.question_evidence?.length) {
    return { state: "needs_processing", label: "Needs setup", message: "Test questions are not linked yet." };
  }
  if (lesson.question_evidence.some(isPlaceholderItem)) {
    return { state: "demo_placeholder", label: "Reference pending", message: "Test questions use placeholder references until question-bank PDFs are indexed." };
  }
  return { state: "source_backed", label: "Questions ready", message: "Test questions are linked to processed question-bank references." };
}

function messageForState(sourceState) {
  if (sourceState === "source_backed") return "Class references are ready.";
  if (sourceState === "demo_placeholder") return "This class still uses placeholder references. Process the real textbook, question bank, and board clips before using it as a complete class.";
  if (sourceState === "needs_processing") return "Reference setup is incomplete for this class.";
  return "Class reference is unavailable.";
}

function hasQuestionEvidence(lesson) {
  return Boolean(lesson.question_evidence?.length);
}

function hasVideoEvidence(lesson) {
  return Boolean(lesson.video_evidence?.length);
}

function hasTextbookEvidence(lesson) {
  return Boolean(lesson.textbook_evidence?.length);
}

function hasPlaceholderEvidence(lesson) {
  const textbook = lesson.textbook_evidence || [];
  const questions = lesson.question_evidence || [];
  const videos = lesson.video_evidence || [];
  return [...textbook, ...questions, ...videos].some(isPlaceholderItem);
}

function isPlaceholderItem(item) {
  const searchable = [
    item.text_preview,
    item.prompt_preview,
    item.transcript_preview,
    item.note,
  ].map((value) => String(value || "").toLowerCase()).join(" ");
  return Boolean(item.artifact_only)
    || String(item.video_id || "").startsWith("bundled_")
    || searchable.includes("placeholder")
    || searchable.includes("marker");
}

function nextLesson() {
  return data.lessons.find((lesson) => lessonState(lesson.id).mastery !== "mastered") || data.lessons[0];
}

function nextAfter(lessonId) {
  const index = data.lessons.findIndex((lesson) => lesson.id === lessonId);
  return data.lessons[(index + 1) % data.lessons.length];
}

function learningReviewLessons() {
  return data.lessons.filter((lesson) => {
    const item = lessonState(lesson.id);
    return item.mastery === "review_needed" || isStalePractice(item);
  });
}

function sourceSetupLessons() {
  return data.lessons.filter((lesson) => overallSourceState(lesson).state !== "source_backed");
}

function learningReviewReason(lesson) {
  const item = lessonState(lesson.id);
  if (item.reviewReason) return item.reviewReason;
  if (isStalePractice(item)) return "This class has not been practiced recently.";
  return "This class needs another test-paper pass.";
}

function sourceSetupReason(lesson) {
  const sourceState = overallSourceState(lesson);
  return sourceState.state === "demo_placeholder"
    ? "Reference setup pending: placeholder material is present."
    : sourceState.message;
}

function isStalePractice(item) {
  if (!item.lastPracticed || item.mastery !== "practiced") return false;
  const elapsed = Date.now() - new Date(item.lastPracticed).getTime();
  return elapsed > 1000 * 60 * 60 * 24 * 7;
}

function shortProfileLabel() {
  return `${labelForState(state.preferences.goal)}, ${labelForState(state.preferences.supportLevel)}`;
}

function compactText(text) {
  const value = String(text || "");
  return value.length > 170 ? `${value.slice(0, 167)}...` : value;
}

function safeId(value) {
  return String(value).replace(/[^a-zA-Z0-9_-]/g, "_");
}

function labelForState(value) {
  return String(value || "not_started").replaceAll("_", " ");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

bindGlobalNavigation();
render();
