// Session management
let currentProblemIndex = 0;
let sessionStartTime = Date.now();
let problemStartTime = Date.now();
let reviewedProblems = TEMPLATE_DATA.reviewedProblems;
let sessionData = [];
let sessionTimeRemaining = TEMPLATE_DATA.sessionTimeRemaining;
let maxDurationSeconds = TEMPLATE_DATA.maxDurationSeconds;
let warningShown = false;
let isLoadingNextProblem = false;
let timerInterval = null;
let sessionCompleted = false;
let autoOpenProblems = true;

// Timer - Update countdown and progress
function updateTimer() {
    // Don't update timer if session is already completed
    if (sessionCompleted) {
        return;
    }

    const problemElapsed = Math.floor((Date.now() - problemStartTime) / 1000);

    // Update session time remaining
    sessionTimeRemaining--;

    if (sessionTimeRemaining <= 0) {
        // Time's up! Auto-complete session
        sessionCompleted = true;
        clearInterval(timerInterval);
        alert('Session time expired! Completing your session.');
        completeSession();
        return;
    }

    // Update countdown display
    const minutes = Math.floor(sessionTimeRemaining / 60);
    const seconds = sessionTimeRemaining % 60;
    document.getElementById('time-remaining').textContent =
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

    // Update progress bar
    const timeProgress = ((maxDurationSeconds - sessionTimeRemaining) / maxDurationSeconds) * 100;
    document.getElementById('progress-fill').style.width = timeProgress + '%';
    document.getElementById('progress-text').textContent = Math.round(timeProgress) + '% complete';

    // Warning disabled per user request - was distracting

    // Update progress bar color as time runs out
    const progressBar = document.getElementById('progress-fill');
    if (sessionTimeRemaining <= 300) {
        progressBar.style.backgroundColor = '#ff6b6b'; // Red for final 5 minutes
    } else if (sessionTimeRemaining <= 600) {
        progressBar.style.backgroundColor = '#ffa726'; // Orange for final 10 minutes
    }
}

timerInterval = setInterval(updateTimer, 1000);

// Initialize auto-open preference from localStorage
function initializeAutoOpenSetting() {
    const saved = localStorage.getItem('autoOpenProblems');
    if (saved !== null) {
        autoOpenProblems = JSON.parse(saved);
    }

    const checkbox = document.getElementById('auto-open-problems');
    if (checkbox) {
        checkbox.checked = autoOpenProblems;
        checkbox.addEventListener('change', function() {
            autoOpenProblems = this.checked;
            localStorage.setItem('autoOpenProblems', JSON.stringify(autoOpenProblems));
        });
    }
}

// Initialize on page load
initializeAutoOpenSetting();

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key >= '0' && e.key <= '5') {
        const rating = parseInt(e.key);
        submitRating(rating);
    } else if (e.key === 's' || e.key === 'S') {
        skipProblem();
    }
});

// Rating buttons
document.querySelectorAll('.rating-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const rating = parseInt(this.dataset.rating);
        submitRating(rating);
    });
});

// Skip buttons
document.querySelectorAll('.skip-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        skipProblem();
    });
});

function submitRating(rating) {
    const currentCard = document.querySelector('.problem-card:not([style*="display: none"])');
    if (!currentCard) return;

    // Clear any existing flash messages when rating a problem
    if (typeof clearFlashMessages !== 'undefined') {
        clearFlashMessages();
    }

    const problemId = currentCard.dataset.problemId;
    const timeSpent = Math.floor((Date.now() - problemStartTime) / 1000);

    // Disable all buttons
    currentCard.querySelectorAll('button').forEach(btn => btn.disabled = true);

    fetch('/session/review', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            problem_id: parseInt(problemId),
            rating: rating,
            time_spent: timeSpent
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json().catch(jsonError => {
            throw new Error('Invalid JSON response from server');
        });
    })
    .then(data => {
        if (data.success) {
            sessionData.push({
                rating: rating,
                timeSpent: timeSpent
            });

            // Update session time tracking
            if (data.session_time_remaining !== undefined) {
                sessionTimeRemaining = data.session_time_remaining;
            }

            // Check if session expired
            if (data.session_expired || data.session_completed) {
                sessionCompleted = true;
                if (timerInterval) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                }
                alert('Session completed! Time limit reached.');
                completeSession();
                return;
            }

            nextProblem();
        } else {
            alert('Error submitting review: ' + data.error);
            // Re-enable buttons
            currentCard.querySelectorAll('button').forEach(btn => btn.disabled = false);
        }
    })
    .catch(error => {
        console.error('Error submitting review:', error);
        alert('Error submitting review: ' + error.message);
        currentCard.querySelectorAll('button').forEach(btn => btn.disabled = false);
    });
}

function skipProblem() {
    nextProblem();
}

function nextProblem() {
    if (isLoadingNextProblem) return;

    isLoadingNextProblem = true;
    reviewedProblems++;
    updateProgress();

    // Check if we have more problems in the current batch
    if (currentProblemIndex + 1 < totalProblems) {
        // Show next problem from current batch
        currentProblemIndex++;
        showProblemAtIndex(currentProblemIndex);
        isLoadingNextProblem = false;
        return;
    }

    // Need to fetch next problem from server
    fetch('/session/next-problem')
        .then(response => response.json())
        .then(data => {
            if (data.session_expired) {
                sessionCompleted = true;
                if (timerInterval) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                }
                alert('Session expired! Completing your session.');
                completeSession();
                return;
            }

            if (data.no_problems) {
                // No more problems available, complete session
                completeSession();
                return;
            }

            if (data.success && data.problem) {
                // Add new problem to the session
                addNewProblemToSession(data.problem);
                currentProblemIndex++;

                // Show the new problem (and auto-open if enabled)
                showProblemAtIndex(currentProblemIndex);

                // For dynamically added problems, auto-open immediately if enabled
                if (autoOpenProblems) {
                    window.open(data.problem.url, '_blank');
                }

                // Update session time tracking if provided
                if (data.session && data.session.remaining_seconds !== undefined) {
                    sessionTimeRemaining = data.session.remaining_seconds;
                }
            } else {
                alert('Error loading next problem: ' + (data.error || 'Unknown error'));
                completeSession();
            }
        })
        .catch(error => {
            console.error('Error fetching next problem:', error);
            alert('Error loading next problem. Completing session.');
            completeSession();
        })
        .finally(() => {
            isLoadingNextProblem = false;
        });
}

function showProblemAtIndex(index) {
    // Hide all problems
    document.querySelectorAll('.problem-card').forEach(card => {
        card.style.display = 'none';
    });

    // Show the problem at the given index
    const cards = document.querySelectorAll('.problem-card');
    if (cards[index]) {
        cards[index].style.display = 'block';
        problemStartTime = Date.now();

        // Auto-open problem in new tab if enabled and this isn't the first problem
        if (autoOpenProblems && index > 0) {
            const problemLink = cards[index].querySelector('.problem-link');
            if (problemLink && problemLink.href) {
                window.open(problemLink.href, '_blank');
            }
        }
    }
}

function addNewProblemToSession(problem) {
    // Create new problem card HTML
    const problemCard = document.createElement('div');
    problemCard.className = 'problem-card';
    problemCard.dataset.problemId = problem.id;
    problemCard.style.display = 'none';

    problemCard.innerHTML = `
        <div class="problem-header">
            <h2>${problem.title || problem.slug.replace('-', ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</h2>
            <div class="problem-meta">
                ${problem.number ? `<span class="problem-number">#${problem.number}</span>` : ''}
                ${problem.difficulty ? `<span class="difficulty ${problem.difficulty.toLowerCase()}">${problem.difficulty}</span>` : ''}
            </div>
        </div>

        <div class="problem-link-section">
            <a href="${problem.url}" target="_blank" class="problem-link">
                Open Problem in LeetCode
                <span class="external-icon">↗</span>
            </a>
        </div>

        <div class="rating-section">
            <h3>How did you do?</h3>
            <div class="rating-buttons">
                <button class="rating-btn rating-0" data-rating="0" data-key="0">
                    <span class="rating-emoji">😵</span>
                    <span class="rating-label">Failed</span>
                    <span class="rating-shortcut">0</span>
                </button>
                <button class="rating-btn rating-1" data-rating="1" data-key="1">
                    <span class="rating-emoji">📖</span>
                    <span class="rating-label">Solution</span>
                    <span class="rating-shortcut">1</span>
                </button>
                <button class="rating-btn rating-2" data-rating="2" data-key="2">
                    <span class="rating-emoji">❌</span>
                    <span class="rating-label">Errors</span>
                    <span class="rating-shortcut">2</span>
                </button>
                <button class="rating-btn rating-3" data-rating="3" data-key="3">
                    <span class="rating-emoji">🐛</span>
                    <span class="rating-label">Debug</span>
                    <span class="rating-shortcut">3</span>
                </button>
                <button class="rating-btn rating-4" data-rating="4" data-key="4">
                    <span class="rating-emoji">✅</span>
                    <span class="rating-label">Solved</span>
                    <span class="rating-shortcut">4</span>
                </button>
                <button class="rating-btn rating-5" data-rating="5" data-key="5">
                    <span class="rating-emoji">🚀</span>
                    <span class="rating-label">Fluent</span>
                    <span class="rating-shortcut">5</span>
                </button>
            </div>
            <p class="rating-hint">Use keyboard shortcuts 0-5 or click the buttons</p>
        </div>

        <div class="session-controls">
            <button class="btn btn-secondary skip-btn" data-problem-id="${problem.id}">
                Skip for Now
            </button>
            <button class="btn btn-warning pause-btn" onclick="pauseSession()">
                ⏸️ Pause Session
            </button>
            <button class="btn btn-danger abandon-btn" onclick="abandonSession()">
                🛑 End Session
            </button>
        </div>
    `;

    // Add event listeners for the new problem's buttons
    problemCard.querySelectorAll('.rating-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const rating = parseInt(this.dataset.rating);
            submitRating(rating);
        });
    });

    problemCard.querySelector('.skip-btn').addEventListener('click', function() {
        skipProblem();
    });

    // Append to session content
    document.getElementById('session-content').appendChild(problemCard);

    // Update total problems count
    totalProblems++;
}

function updateProgress() {
    // Update problems completed count
    document.getElementById('problems-completed').textContent = reviewedProblems;
}

function completeSession() {
    // Mark session as completed and stop timer
    sessionCompleted = true;
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    // Hide session content
    document.getElementById('session-content').style.display = 'none';

    // Show completion screen
    document.getElementById('session-complete').style.display = 'block';

    // Update summary
    const totalTime = Math.floor((Date.now() - sessionStartTime) / 1000 / 60);
    const avgRating = sessionData.length > 0 ?
        (sessionData.reduce((sum, item) => sum + item.rating, 0) / sessionData.length).toFixed(1) : 0;

    document.getElementById('session-summary').innerHTML = `
        <div class="summary-stats">
            <div class="summary-stat">
                <span class="summary-number">${reviewedProblems}</span>
                <span class="summary-label">Problems Reviewed</span>
            </div>
            <div class="summary-stat">
                <span class="summary-number">${totalTime}</span>
                <span class="summary-label">Minutes</span>
            </div>
            <div class="summary-stat">
                <span class="summary-number">${avgRating}</span>
                <span class="summary-label">Avg Rating</span>
            </div>
        </div>
    `;

    // Complete session on server
    fetch('/session/complete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    });
}

function pauseSession() {
    if (confirm('Pause your practice session? You can resume it later.')) {
        // Clear flash messages when pausing session
        if (typeof clearFlashMessages !== 'undefined') {
            clearFlashMessages();
        }

        fetch('/session/pause', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Session paused! You can resume from the dashboard.');
                window.location.href = '/';
            } else {
                alert('Error pausing session: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error pausing session');
        });
    }
}

function abandonSession() {
    if (confirm('End your practice session? This will mark it as completed.')) {
        // Clear flash messages when abandoning session
        if (typeof clearFlashMessages !== 'undefined') {
            clearFlashMessages();
        }

        fetch('/session/abandon', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Session ended. Great work!');
                window.location.href = '/';
            } else {
                alert('Error ending session: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error ending session');
        });
    }
}

// Initialize progress
updateProgress();
