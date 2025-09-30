// Global app utilities and enhancements

function clearFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        message.style.transition = 'opacity 0.3s';
        message.style.opacity = '0';
        setTimeout(function() {
            if (message.parentElement) {
                message.remove();
            }
        }, 300);
    });
}

// Make clearFlashMessages globally available
window.clearFlashMessages = clearFlashMessages;

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(function(message) {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500);
        });
    }, 5000);

    // Add keyboard shortcut hints
    addKeyboardShortcuts();

    // Add form enhancements
    enhanceForms();

    // Add loading states to buttons
    enhanceButtons();
});

function addKeyboardShortcuts() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Alt + D for Dashboard
        if (e.altKey && e.key === 'd') {
            e.preventDefault();
            clearFlashMessages();
            window.location.href = '/';
        }

        // Alt + P for Practice
        if (e.altKey && e.key === 'p') {
            e.preventDefault();
            clearFlashMessages();
            window.location.href = '/session';
        }

        // Alt + M for Problems (Manage)
        if (e.altKey && e.key === 'm') {
            e.preventDefault();
            clearFlashMessages();
            window.location.href = '/problems';
        }

        // Alt + S for Stats
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            clearFlashMessages();
            window.location.href = '/stats';
        }
    });
}

function enhanceForms() {
    // Auto-extract problem info from URL when pasted
    const urlInputs = document.querySelectorAll('input[type="url"]');
    urlInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            const url = this.value.trim();
            if (url && url.includes('leetcode.com/problems/')) {
                autoFillProblemData(url, this.closest('form'));
            }
        });
    });

    // Add form validation and clear flash messages on submit
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            // Clear any existing flash messages before form submission
            clearFlashMessages();

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = submitBtn.innerHTML.replace(/Add|Submit|Save/, 'Adding...');
            }
        });
    });
}

function autoFillProblemData(url, form) {
    if (!form) return;

    // Extract slug from URL
    const match = url.match(/\/problems\/([^\/]+)/);
    if (!match) return;

    const slug = match[1];

    // Auto-fill title if empty
    const titleInput = form.querySelector('input[name="title"]');
    if (titleInput && !titleInput.value) {
        titleInput.value = slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}

function enhanceButtons() {
    // Add loading states to async buttons
    const asyncButtons = document.querySelectorAll('.btn[data-async]');
    asyncButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            // Clear flash messages on button action
            clearFlashMessages();

            const originalText = this.innerHTML;
            this.innerHTML = 'Loading...';
            this.disabled = true;

            // Re-enable after 3 seconds if not handled elsewhere
            setTimeout(() => {
                if (this.disabled) {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }
            }, 3000);
        });
    });

    // Clear flash messages on regular button clicks too
    const allButtons = document.querySelectorAll('button, .btn');
    allButtons.forEach(function(button) {
        // Skip if already has a click handler or is a close button
        if (button.hasAttribute('data-enhanced') || button.classList.contains('flash-close')) {
            return;
        }

        button.addEventListener('click', function() {
            clearFlashMessages();
        });

        button.setAttribute('data-enhanced', 'true');
    });
}

// Utility functions for session page
window.SessionUtils = {
    formatTime: function(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    },

    showNotification: function(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `flash-message flash-${type}`;
        notification.innerHTML = `
            ${message}
            <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
        `;

        const mainContent = document.querySelector('.main-content');
        mainContent.insertBefore(notification, mainContent.firstChild);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 3000);
    },

    confirmAction: function(message) {
        return confirm(message);
    }
};

// Problem management utilities
window.ProblemUtils = {
    validateUrl: function(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.includes('leetcode.com') && url.includes('/problems/');
        } catch {
            return false;
        }
    },

    extractProblemNumber: function(title) {
        const match = title.match(/^(\d+)\./);
        return match ? parseInt(match[1]) : null;
    },

    formatTags: function(tags) {
        if (Array.isArray(tags)) {
            return tags.join(', ');
        }
        return tags || '';
    }
};

// Stats utilities
window.StatsUtils = {
    formatRating: function(rating) {
        return rating ? rating.toFixed(1) : '0.0';
    },

    getRatingColor: function(rating) {
        if (rating >= 4.5) return '#4CAF50';
        if (rating >= 3.5) return '#8bc34a';
        if (rating >= 2.5) return '#ffc107';
        if (rating >= 1.5) return '#ff9800';
        return '#f44336';
    },

    getDifficultyColor: function(difficulty) {
        switch (difficulty?.toLowerCase()) {
            case 'easy': return '#4CAF50';
            case 'medium': return '#ff9800';
            case 'hard': return '#f44336';
            default: return '#b0b0b0';
        }
    }
};

// API utilities
window.ApiUtils = {
    async makeRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            window.SessionUtils.showNotification('Request failed: ' + error.message, 'error');
            throw error;
        }
    },

    async addProblem(problemData) {
        return this.makeRequest('/api/add-problem', {
            method: 'POST',
            body: JSON.stringify(problemData)
        });
    },

    async getDueProblems(limit = 10) {
        return this.makeRequest(`/api/due-problems?limit=${limit}`);
    },

    async submitReview(problemId, rating, timeSpent) {
        return this.makeRequest('/session/review', {
            method: 'POST',
            body: JSON.stringify({
                problem_id: problemId,
                rating: rating,
                time_spent: timeSpent
            })
        });
    }
};

// Theme and UI enhancements
window.UIUtils = {
    addTooltips: function() {
        // Add tooltips to elements with title attributes
        const elementsWithTitles = document.querySelectorAll('[title]');
        elementsWithTitles.forEach(function(element) {
            element.addEventListener('mouseenter', function(e) {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.textContent = this.title;
                tooltip.style.cssText = `
                    position: absolute;
                    background: #2a2a2a;
                    color: #e0e0e0;
                    padding: 0.5rem;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    z-index: 1000;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    pointer-events: none;
                `;

                // Remove original title to prevent browser tooltip
                this.setAttribute('data-title', this.title);
                this.removeAttribute('title');

                document.body.appendChild(tooltip);

                // Position tooltip
                const rect = this.getBoundingClientRect();
                tooltip.style.left = rect.left + 'px';
                tooltip.style.top = (rect.bottom + 5) + 'px';
            });

            element.addEventListener('mouseleave', function() {
                // Restore title
                if (this.hasAttribute('data-title')) {
                    this.title = this.getAttribute('data-title');
                    this.removeAttribute('data-title');
                }

                // Remove tooltip
                const tooltip = document.querySelector('.tooltip');
                if (tooltip) {
                    tooltip.remove();
                }
            });
        });
    },

    addSmoothScrolling: function() {
        // Add smooth scrolling to anchor links
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        anchorLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    },

    addProgressIndicators: function() {
        // Add progress indicators for forms
        const forms = document.querySelectorAll('form');
        forms.forEach(function(form) {
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
            if (inputs.length > 0) {
                const progressBar = document.createElement('div');
                progressBar.className = 'form-progress';
                progressBar.style.cssText = `
                    height: 3px;
                    background: #3a3a3a;
                    margin-bottom: 1rem;
                    border-radius: 2px;
                    overflow: hidden;
                `;

                const progressFill = document.createElement('div');
                progressFill.style.cssText = `
                    height: 100%;
                    background: #4CAF50;
                    width: 0%;
                    transition: width 0.3s ease;
                `;

                progressBar.appendChild(progressFill);
                form.insertBefore(progressBar, form.firstChild);

                function updateProgress() {
                    const filledInputs = Array.from(inputs).filter(input =>
                        input.value.trim() !== ''
                    ).length;
                    const progress = (filledInputs / inputs.length) * 100;
                    progressFill.style.width = progress + '%';
                }

                inputs.forEach(function(input) {
                    input.addEventListener('input', updateProgress);
                    input.addEventListener('change', updateProgress);
                });

                updateProgress();
            }
        });
    }
};

// Initialize UI enhancements
document.addEventListener('DOMContentLoaded', function() {
    window.UIUtils.addTooltips();
    window.UIUtils.addSmoothScrolling();
    window.UIUtils.addProgressIndicators();
});

// Service Worker registration for offline capability (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Only register if we have a service worker file
        fetch('/sw.js').then(function(response) {
            if (response.ok) {
                navigator.serviceWorker.register('/sw.js')
                    .then(function(registration) {
                        console.log('SW registered: ', registration);
                    })
                    .catch(function(registrationError) {
                        console.log('SW registration failed: ', registrationError);
                    });
            }
        }).catch(function() {
            // Service worker file doesn't exist, which is fine
        });
    });
}