
    const pageData = document.getElementById("pageData");
    const playerId = pageData?.dataset.playerId;
    const apiBase = pageData?.dataset.apiBase || "";

    const badgeList = document.getElementById("badgeList");
    const attemptsTable = document.getElementById("attemptsTable");
    const completionStatus = document.getElementById("completionStatus");

    const finalAttempts = document.getElementById("finalAttempts");
    const finalBadge = document.getElementById("finalBadge");
    const completedAt = document.getElementById("completedAt");
    const finalCorrect = document.getElementById("finalCorrect");

    const finalAnswerInput = document.getElementById("finalAnswer");
    const finalAttemptsInput = document.getElementById("finalAttemptsInput");
    const finalBadgeInput = document.getElementById("finalBadgeInput");
    const checkAnswerBtn = document.getElementById("checkAnswer");
    const saveCompletionBtn = document.getElementById("saveCompletion");
    const checkStatus = document.getElementById("checkStatus");
    const generateGuideBtn = document.getElementById("generateGuide");
    const playGuideBtn = document.getElementById("playGuide");
    const guidePanel = document.getElementById("guidePanel");
    const guideStatus = document.getElementById("guideStatus");
    const guideProgress = document.getElementById("guideProgress");
    const guideVideoOutput = document.getElementById("guideVideoOutput");
    const guideVideoPlayer = document.getElementById("guideVideoPlayer");
    const downloadVideo = document.getElementById("downloadVideo");
    const videoFallback = document.getElementById("videoFallback");
    const chatBox = document.getElementById("chatBox");
    const chatInput = document.getElementById("chatInput");
    const chatSend = document.getElementById("chatSend");
    const chatTyping = document.getElementById("chatTyping");
    const chatHistory = [];
    let guideSteps = [];
    let guideDurations = [];
    let guideVideo = null;
    let guideUiSteps = [];
    let guideVideoNotice = "";
    let guideVideoBlobUrl = "";

    function appendChatVideo(url) {
        if (!chatBox || !url) return;
        const wrapper = document.createElement("div");
        wrapper.className = "chat-message";
        wrapper.innerHTML = `
            <div class="chat-ai">AI</div>
            <video controls style="max-width:100%; border-radius:10px; margin-top:6px;">
                <source src="${url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        `;
        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function setGuideVideoUrl(url) {
        if (!url) return;
        if (guideVideoBlobUrl) {
            URL.revokeObjectURL(guideVideoBlobUrl);
            guideVideoBlobUrl = "";
        }
        if (guideVideoPlayer) {
            guideVideoPlayer.src = url;
        }
        if (downloadVideo) {
            downloadVideo.href = url;
        }
        if (guideVideoOutput) {
            guideVideoOutput.style.display = "block";
        }
        if (videoFallback) {
            videoFallback.style.display = "none";
        }
    }

    function formatTimestamp(ts) {
        if (!ts) return "-";
        const date = new Date(ts);
        return date.toLocaleString();
    }

    async function safeFetch(path, options = {}) {
        try {
            const response = await fetch(`${apiBase}${path}`, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response;
        } catch (error) {
            console.error("Backend request failed:", error);
            return null;
        }
    }

    function renderScore(data) {
        const earnedBadges = data.earned_badges || [];
        badgeList.innerHTML = earnedBadges.length
            ? earnedBadges.map(b => `<span class="badge-pill">🏅 ${b.badge_name}</span>`).join("")
            : "No badges earned yet.";

        attemptsTable.innerHTML = earnedBadges.length
            ? earnedBadges.map(b => `
                <tr>
                    <td>${b.badge_name || "-"}</td>
                    <td>${b.attempts}</td>
                    <td>${formatTimestamp(b.timestamp)}</td>
                </tr>
            `).join("")
            : '<tr><td colspan="3">No attempts logged yet.</td></tr>';

        const finalData = data.final || {};
        finalAttempts.textContent = finalData.final_attempts ?? "-";
        finalBadge.textContent = finalData.final_badge?.badge_name || "-";
        completedAt.textContent = formatTimestamp(finalData.completed_at);
        finalCorrect.textContent = typeof finalData.final_correct === "boolean"
            ? (finalData.final_correct ? "Yes" : "No")
            : "-";

        if (finalAttemptsInput && finalData.final_attempts !== null && finalData.final_attempts !== undefined) {
            finalAttemptsInput.value = finalData.final_attempts;
        }
        if (finalBadgeInput && finalData.final_badge?.badge_name) {
            finalBadgeInput.value = finalData.final_badge.badge_name;
        }

        if (data.completion_status) {
            completionStatus.textContent = "Completed";
            completionStatus.classList.remove("status-bad");
            completionStatus.classList.add("status-ok");
        } else {
            completionStatus.textContent = "Not Completed";
            completionStatus.classList.remove("status-ok");
            completionStatus.classList.add("status-bad");
        }
    }

    async function loadScore() {
        if (!playerId) {
            badgeList.textContent = "Missing player id";
            attemptsTable.innerHTML = '<tr><td colspan="3">Missing player id</td></tr>';
            return;
        }
        const response = await safeFetch(`/player/${playerId}/score`);
        if (!response) {
            badgeList.textContent = "Backend unavailable";
            attemptsTable.innerHTML = '<tr><td colspan="3">Backend unavailable</td></tr>';
            return;
        }
        const data = await response.json();
        if (data.success) {
            renderScore(data);
        }
    }

    checkAnswerBtn.addEventListener("click", async () => {
        checkStatus.textContent = "Checking...";
        const response = await safeFetch(`/player/${playerId}/final-check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer: finalAnswerInput.value })
        });
        if (!response) {
            checkStatus.textContent = "Backend unavailable";
            return;
        }
        const data = await response.json();
        if (data.correct) {
            checkStatus.textContent = "✅ Correct answer";
            const badgeResponse = await safeFetch(`/player/${playerId}/final-badge`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            if (!badgeResponse) {
                checkStatus.textContent = "✅ Correct answer (badge pending)";
            }
        } else {
            checkStatus.textContent = "❌ Incorrect answer";
            if (Array.isArray(data.steps) && data.steps.length) {
                guideSteps = data.steps;
                guideVideo = null;
                guideUiSteps = [];
                guideVideoNotice = "";
                renderGuideSteps(guideSteps, "Fix Steps");
            }
        }
        await loadScore();
    });

    function renderGuideSteps(steps, title = "Walkthrough") {
        if (!guidePanel) return;
        if (!steps || !steps.length) {
            guidePanel.innerHTML = "<div class=\"text-muted\">No steps available yet.</div>";
            return;
        }
        const videoNoticeHtml = guideVideoNotice
            ? `<div class=\"text-warning mt-2\" style=\"font-size: 13px;\">${guideVideoNotice}</div>`
            : "";
        const videoHtml = guideVideo && Array.isArray(guideVideo.scenes) && guideVideo.scenes.length
            ? `
                <div class=\"mt-3\"><strong>${guideVideo.title || "Step-by-step Video"}</strong></div>
                <div class=\"guide-video\">
                    ${guideVideo.scenes.map((scene, idx) => `
                        <div class=\"video-scene\" data-scene=\"${idx}\">
                            <div><strong>${scene.title || `Scene ${idx + 1}`}</strong></div>
                            <div class=\"text-muted\" style=\"font-size: 13px;\">${scene.on_screen || scene.narration || ""}</div>
                        </div>
                    `).join("")}
                </div>
            `
            : "";
        const uiStepsHtml = Array.isArray(guideUiSteps) && guideUiSteps.length
            ? `
                <div class=\"guide-ui-steps\">
                    <div class=\"mb-1\"><strong>UI Step-by-Step</strong></div>
                    <ol class=\"mb-0\">
                        ${guideUiSteps.map(step => `<li>${step}</li>`).join("")}
                    </ol>
                </div>
            `
            : "";
        guidePanel.innerHTML = `
            <div class=\"guide-progress\"><div id=\"guideProgress\"></div></div>
            <div class=\"mb-2\"><strong>${title}</strong></div>
            ${steps.map((step, index) => `
                <div class=\"guide-step\" data-step=\"${index}\">
                    ${index + 1}. ${step}
                </div>
            `).join("")}
            ${uiStepsHtml}
            ${videoNoticeHtml}
            ${videoHtml}
        `;
    }

    function resetVideoOutput() {
        if (guideVideoBlobUrl) {
            URL.revokeObjectURL(guideVideoBlobUrl);
            guideVideoBlobUrl = "";
        }
        if (guideVideoPlayer) {
            guideVideoPlayer.src = "";
        }
        if (downloadVideo) {
            downloadVideo.href = "#";
        }
        if (videoFallback) {
            videoFallback.textContent = "";
            videoFallback.style.display = "none";
        }
        if (guideVideoOutput) {
            guideVideoOutput.style.display = "none";
        }
    }

    function drawScene(ctx, width, height, scene, progress) {
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "#0b1020";
        ctx.fillRect(0, 0, width, height);

        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(40, 40, Math.max(0, (width - 80) * progress), 8);

        ctx.fillStyle = "#e2e8f0";
        ctx.font = "bold 28px sans-serif";
        ctx.fillText(scene.title || "Step", 40, 100);

        ctx.fillStyle = "#cbd5f5";
        ctx.font = "20px sans-serif";
        const text = scene.onScreen || scene.narration || "";
        const maxWidth = width - 80;
        const words = text.split(" ");
        let line = "";
        let y = 150;
        words.forEach(word => {
            const testLine = line + word + " ";
            const metrics = ctx.measureText(testLine);
            if (metrics.width > maxWidth && line) {
                ctx.fillText(line.trim(), 40, y);
                line = word + " ";
                y += 28;
            } else {
                line = testLine;
            }
        });
        if (line) ctx.fillText(line.trim(), 40, y);

        ctx.fillStyle = "rgba(56, 189, 248, 0.2)";
        ctx.fillRect(40, height - 80, width - 80, 40);
        ctx.fillStyle = "#e2e8f0";
        ctx.font = "16px sans-serif";
        ctx.fillText("AI Walkthrough Video", 50, height - 53);
    }

    async function generateVideoFromScenes(scenes) {
        if (!window.MediaRecorder) {
            guideStatus.textContent = "Video generation not supported in this browser";
            if (guideVideoOutput) guideVideoOutput.style.display = "block";
            if (videoFallback) {
                videoFallback.textContent = "Your browser does not support MediaRecorder. Use the step list instead.";
                videoFallback.style.display = "block";
            }
            return;
        }
        resetVideoOutput();

        if (guideVideoOutput) {
            guideVideoOutput.style.display = "block";
        }
        if (videoFallback) {
            videoFallback.textContent = "Generating video...";
            videoFallback.style.display = "block";
        }

        const canvas = document.createElement("canvas");
        const width = 960;
        const height = 540;
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");

        const stream = canvas.captureStream(30);
        const preferredTypes = [
            "video/webm;codecs=vp9",
            "video/webm;codecs=vp8",
            "video/webm"
        ];
        const mimeType = preferredTypes.find(type => MediaRecorder.isTypeSupported(type)) || "";
        let recorder;
        try {
            recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        } catch (error) {
            guideStatus.textContent = "Unable to start video recording";
            if (videoFallback) {
                videoFallback.textContent = "Video recording failed to initialize in this browser.";
                videoFallback.style.display = "block";
            }
            return;
        }
        const chunks = [];
        recorder.ondataavailable = event => {
            if (event.data && event.data.size > 0) chunks.push(event.data);
        };

        recorder.start();
        for (let i = 0; i < scenes.length; i += 1) {
            const scene = scenes[i];
            const durationMs = (guideDurations[i] || 8) * 1000;
            const start = performance.now();
            let elapsed = 0;
            while (elapsed < durationMs) {
                const progress = Math.min(1, elapsed / durationMs);
                drawScene(ctx, width, height, scene, progress);
                await new Promise(resolve => requestAnimationFrame(resolve));
                elapsed = performance.now() - start;
            }
        }
        recorder.stop();

        await new Promise(resolve => {
            recorder.onstop = resolve;
        });

        const blob = new Blob(chunks, { type: "video/webm" });
        if (!blob.size) {
            guideStatus.textContent = "Video generation failed";
            if (videoFallback) {
                videoFallback.textContent = "No video data was produced. Try another browser.";
                videoFallback.style.display = "block";
            }
            return;
        }
        guideVideoBlobUrl = URL.createObjectURL(blob);
        if (guideVideoPlayer) {
            guideVideoPlayer.src = guideVideoBlobUrl;
        }
        if (downloadVideo) {
            downloadVideo.href = guideVideoBlobUrl;
        }
        if (guideVideoOutput) {
            guideVideoOutput.style.display = "block";
        }
        if (videoFallback) {
            videoFallback.style.display = "none";
        }
    }

    generateGuideBtn.addEventListener("click", async () => {
        guideStatus.textContent = "Generating...";
        const response = await safeFetch(`/player/${playerId}/guidance`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer: finalAnswerInput.value })
        });
        if (!response) {
            guideStatus.textContent = "Backend unavailable";
            return;
        }
        const data = await response.json();
        if (data.success) {
            guideSteps = data.steps || [];
            guideDurations = Array.isArray(data.durations) ? data.durations : [];
            guideVideo = data.video || null;
            guideUiSteps = Array.isArray(data.ui_steps) ? data.ui_steps : [];
            guideVideoNotice = data.video_notice || "";
            renderGuideSteps(guideSteps, data.title || "Walkthrough");
            if (data.video_url) {
                setGuideVideoUrl(data.video_url);
            } else if (guideVideo && Array.isArray(guideVideo.scenes) && guideVideo.scenes.length) {
                await generateVideoFromScenes(guideVideo.scenes);
            }
            guideStatus.textContent = "";
        } else {
            guideStatus.textContent = data.message || "Unable to generate";
        }
    });

    playGuideBtn.addEventListener("click", () => {
        const hasVideo = guideVideo && Array.isArray(guideVideo.scenes) && guideVideo.scenes.length;
        if (!guideSteps.length && !hasVideo) {
            guideStatus.textContent = "Generate a walkthrough video first";
            return;
        }
        guideStatus.textContent = "Playing...";
        const stepElements = hasVideo
            ? Array.from(document.querySelectorAll(".video-scene"))
            : Array.from(document.querySelectorAll(".guide-step"));
        const progressEl = document.getElementById("guideProgress");
        const playItems = hasVideo
            ? guideVideo.scenes.map(scene => ({
                narration: scene.narration || scene.on_screen || "",
                onScreen: scene.on_screen || scene.narration || ""
            }))
            : guideSteps.map(step => ({ narration: step, onScreen: step }));
        let index = 0;

        function speakNext() {
            if (index >= playItems.length) {
                guideStatus.textContent = "Finished";
                return;
            }
            stepElements.forEach(el => el.classList.remove("active"));
            const activeEl = stepElements[index];
            if (activeEl) activeEl.classList.add("active");

            const durationMs = (guideDurations[index] || 8) * 1000;
            if (progressEl) {
                const percent = Math.min(100, Math.round(((index + 1) / playItems.length) * 100));
                progressEl.style.width = `${percent}%`;
            }

            const utterance = new SpeechSynthesisUtterance(playItems[index].narration);
            utterance.onend = () => {
                index += 1;
                speakNext();
            };
            speechSynthesis.cancel();
            speechSynthesis.speak(utterance);

            setTimeout(() => {
                if (!speechSynthesis.speaking) {
                    index += 1;
                    speakNext();
                }
            }, durationMs);
        }

        speakNext();
    });

    function appendChatMessage(role, text) {
        if (!chatBox) return;
        const wrapper = document.createElement("div");
        wrapper.className = "chat-message";
        const labelClass = role === "user" ? "chat-user" : "chat-ai";
        const label = role === "user" ? "You" : "AI";
        wrapper.innerHTML = `<div class=\"${labelClass}\">${label}</div><div>${text}</div>`;
        chatBox.appendChild(wrapper);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendChatMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        appendChatMessage("user", message);
        chatHistory.push({ role: "user", content: message });
        chatInput.value = "";
        if (chatTyping) chatTyping.style.display = "block";
        if (chatSend) chatSend.disabled = true;

        const response = await safeFetch(`/player/${playerId}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, history: chatHistory })
        });
        if (!response) {
            appendChatMessage("assistant", "Backend unavailable");
            if (chatTyping) chatTyping.style.display = "none";
            if (chatSend) chatSend.disabled = false;
            return;
        }
        const data = await response.json();
        const reply = data.reply || data.message || "No response";
        appendChatMessage("assistant", reply);
        chatHistory.push({ role: "assistant", content: reply });
        if (data.video_url) {
            appendChatVideo(data.video_url);
        }
        if (data.guidance && data.guidance.success) {
            guideSteps = data.guidance.steps || [];
            guideDurations = Array.isArray(data.guidance.durations) ? data.guidance.durations : [];
            guideVideo = data.guidance.video || null;
            guideUiSteps = Array.isArray(data.guidance.ui_steps) ? data.guidance.ui_steps : [];
            guideVideoNotice = data.guidance.video_notice || "";
            renderGuideSteps(guideSteps, data.guidance.title || "Walkthrough");
            if (data.guidance.video_url) {
                setGuideVideoUrl(data.guidance.video_url);
            } else if (guideVideo && Array.isArray(guideVideo.scenes) && guideVideo.scenes.length) {
                await generateVideoFromScenes(guideVideo.scenes);
            }
        }
        if (chatTyping) chatTyping.style.display = "none";
        if (chatSend) chatSend.disabled = false;
    }

    chatSend.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendChatMessage();
        }
    });

    saveCompletionBtn.addEventListener("click", async () => {
        checkStatus.textContent = "Saving...";
        const attemptsValue = Number(finalAttemptsInput.value);
        const badgeName = finalBadgeInput.value.trim();
        if (!Number.isFinite(attemptsValue)) {
            checkStatus.textContent = "Enter a valid attempts count";
            return;
        }
        if (!badgeName) {
            checkStatus.textContent = "Enter a badge name";
            return;
        }
        const response = await safeFetch(`/player/${playerId}/complete`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                attempts: attemptsValue,
                badge_name: badgeName,
                timestamp: new Date().toISOString()
            })
        });
        if (!response) {
            checkStatus.textContent = "Backend unavailable";
            return;
        }
        const data = await response.json();
        if (data.success) {
            checkStatus.textContent = "✅ Completion saved";
        } else {
            checkStatus.textContent = data.message || "Error saving completion";
        }
        await loadScore();
    });

    loadScore();
