(function() {
    // Notification function
    function showNotification(message, type = 'success') {
        const existing = document.querySelector('.leetcode-srs-notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = 'leetcode-srs-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4CAF50' : '#f44336'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            max-width: 300px;
            animation: slideIn 0.3s ease-out;
        `;

        const style = document.createElement('style');
        style.textContent = '@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }';
        document.head.appendChild(style);

        const icon = type === 'success' ? '✅' : '❌';
        notification.textContent = `${icon} ${message}`;
        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideIn 0.3s ease-out reverse';
                setTimeout(() => notification.remove(), 300);
            }
        }, 3000);
    }

    // Check if we're on a LeetCode problem page
    const url = window.location.href;
    if (!url.includes('leetcode.com/problems/')) {
        showNotification('Please navigate to a LeetCode problem page first!', 'error');
        return;
    }

    // Extract data from __NEXT_DATA__ JSON
    function extractFromNextData() {
        try {
            const nextDataScript = document.querySelector('#__NEXT_DATA__');
            if (!nextDataScript) throw new Error('__NEXT_DATA__ not found');

            const data = JSON.parse(nextDataScript.textContent);
            const question = data.props?.pageProps?.dehydratedState?.queries?.[0]?.state?.data?.question;

            if (!question) throw new Error('Question data not found in __NEXT_DATA__');

            return {
                title: question.title,
                number: question.frontendQuestionId ? parseInt(question.frontendQuestionId) : null,
                difficulty: question.difficulty,
                tags: question.topicTags?.map(tag => tag.name) || [],
                description: question.content || '',
                slug: question.titleSlug,
                likes: question.likes || 0,
                dislikes: question.dislikes || 0,
                hints: question.hints || [],
                examples: question.exampleTestcases || '',
                constraints: question.constraints || '',
                acRate: question.acRate || 0
            };
        } catch (error) {
            console.log('Failed to extract from __NEXT_DATA__:', error);
            return null;
        }
    }

    // Fallback extraction using DOM selectors
    function fallbackExtraction() {
        // Extract slug from URL
        const slugMatch = url.match(/\/problems\/([^\/]+)/);
        const slug = slugMatch ? slugMatch[1] : '';

        // Extract title
        const titleSelectors = ['.css-v3d350', '[data-cy=question-title]', '.question-title', 'h1', '.text-title-large'];
        let title = '';
        for (const selector of titleSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim()) {
                title = element.textContent.trim();
                break;
            }
        }

        // Extract problem number from title
        const numberMatch = title.match(/^(\d+)\./);
        const number = numberMatch ? parseInt(numberMatch[1]) : null;
        if (numberMatch) {
            title = title.replace(/^\d+\.\s*/, '');
        }

        // Extract difficulty
        const difficultySelectors = ['.css-10o4wqw', '[data-difficulty]', '.difficulty-label', '.text-difficulty'];
        let difficulty = '';
        for (const selector of difficultySelectors) {
            const element = document.querySelector(selector);
            if (element) {
                const text = element.textContent.trim();
                if (['Easy', 'Medium', 'Hard'].includes(text)) {
                    difficulty = text;
                    break;
                }
                const attr = element.getAttribute('data-difficulty');
                if (attr && ['Easy', 'Medium', 'Hard'].includes(attr)) {
                    difficulty = attr;
                    break;
                }
            }
        }

        // Extract tags
        const tagSelectors = ['.topic-tag', '.tag', '[data-tag]', '.css-1hky5w4'];
        const tags = [];
        for (const selector of tagSelectors) {
            const elements = document.querySelectorAll(selector);
            for (const element of elements) {
                const text = element.textContent.trim();
                if (text && text.length > 0 && text.length < 50) {
                    tags.push(text);
                }
            }
            if (tags.length > 0) break;
        }

        // Extract description (try to get more content)
        const descriptionSelectors = [
            '.css-1f1j2yy',
            '.question-content',
            '.content__u3I1',
            '[data-track-load="description_content"]'
        ];
        let description = '';
        for (const selector of descriptionSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                const text = element.textContent.trim();
                if (text.length > 100) {
                    description = text;
                    break;
                } else if (text.length > description.length) {
                    description = text;
                }
            }
        }

        return {
            title: title || slug.replace(/-/g, ' '),
            number: number,
            difficulty: difficulty,
            tags: [...new Set(tags)].filter(tag => tag.length > 0 && !tag.includes('Show') && !tag.includes('Hide') && !/^\d+$/.test(tag)),
            description: description,
            slug: slug
        };
    }

    // Try to extract data
    const extractedData = extractFromNextData() || fallbackExtraction();

    const problemData = {
        url: url,
        title: extractedData.title,
        slug: extractedData.slug,
        number: extractedData.number,
        difficulty: extractedData.difficulty,
        tags: extractedData.tags,
        description: extractedData.description
    };

    showNotification('📚 Extracting problem data...', 'success');

    // Send to SRS app
    setTimeout(() => {
        sendToSRS(problemData);
    }, 500);

    async function sendToSRS(data) {
        try {
            const response = await fetch('http://localhost:1234/api/add-problem', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Unknown error occurred');
            }

            showNotification(result.message || 'Problem added successfully!', 'success');
        } catch (error) {
            console.error('Error sending to SRS:', error);
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                showNotification("❌ Cannot connect to SRS app. Make sure it's running on localhost:1234", 'error');
            } else {
                showNotification(`❌ Error: ${error.message}`, 'error');
            }
        }
    }
})();