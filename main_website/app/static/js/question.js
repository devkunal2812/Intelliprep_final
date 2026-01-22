
document.addEventListener('DOMContentLoaded', () => {
    const container = document.querySelector('.test-container');
    if (!container) return;

    const sessionId = container.dataset.sessionId;
    let startTime = Date.now();
    let questionCount = 0;

    // Timer
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            timerElement.textContent =
                `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }, 1000);
    }

    async function fetchQuestion() {
        try {
            const resp = await fetch(`/api/next_question/${sessionId}`);
            const data = await resp.json();

            if (data.complete) {
                window.location.href = `/test/complete/${sessionId}`;
                return;
            }

            const q = data.question;
            const area = document.getElementById("question-area");
            questionCount++;

            // Update progress
            const progress = document.getElementById('progress');
            if (progress) {
                progress.style.width = (questionCount * 10) + '%';
            }

            area.innerHTML = `
                <div class="difficulty-badge">${q.difficulty}</div>
                <span class="domain-badge">${q.domain}</span>
                <h3>Question ${questionCount}</h3>
                <h3>${q.text}</h3>
            `;

            const form = document.createElement("form");
            form.id = "answer-form";
            form.style.marginTop = "24px";

            const optionsContainer = document.createElement("div");
            optionsContainer.className = "options-container";

            q.options.forEach((opt, idx) => {
                const label = document.createElement("label");
                label.className = "option-label";
                label.innerHTML = `
                    <input type="radio" name="option" value="${idx}" required>
                    <span class="option-text">${opt}</span>
                `;
                optionsContainer.appendChild(label);
            });

            form.appendChild(optionsContainer);

            const submit = document.createElement("button");
            submit.type = "submit";
            submit.className = "submit-button";
            submit.textContent = "Submit Answer";
            form.appendChild(submit);

            const timeStart = Date.now();

            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                const fd = new FormData(form);
                const selected = fd.get("option");
                const timeTaken = (Date.now() - timeStart) / 1000.0;
                const username = new URLSearchParams(window.location.search).get("user") || "guest";

                const payload = {
                    session_id: parseInt(sessionId), // Ensure it's an integer if backend expects it
                    username: username,
                    question_id: q.id,
                    selected_option: parseInt(selected),
                    time_taken: timeTaken
                };

                try {
                    const resp2 = await fetch('/api/submit_answer', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    const result = await resp2.json();

                    // Show feedback
                    const feedbackClass = result.correct ? 'correct' : 'incorrect';
                    const feedbackIcon = result.correct ? '<i class="fas fa-check"></i>' : '<i class="fas fa-times"></i>';
                    const feedbackText = result.correct ? ' Correct!' : ' Incorrect';
                    area.innerHTML = `<div class="feedback ${feedbackClass}">${feedbackIcon}${feedbackText}</div>`;

                    setTimeout(fetchQuestion, 1500);
                } catch (err) {
                    console.error("Error submitting answer:", err);
                    area.innerHTML = `<div class="feedback incorrect">Error submitting answer. Please try again.</div>`;
                }
            });

            area.appendChild(form);
        } catch (err) {
            console.error("Error fetching question:", err);
            document.getElementById("question-area").innerHTML = `<div class="loading">Error loading question. Please refresh.</div>`;
        }
    }

    // Start fetching
    fetchQuestion();
});
