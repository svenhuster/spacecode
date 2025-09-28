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

            // Search through all queries to find the one with question data
            const queries = data.props?.pageProps?.dehydratedState?.queries || [];
            let question = null;

            for (const query of queries) {
                if (query.state?.data?.question) {
                    question = query.state.data.question;
                    console.log('Found question data in query:', query.queryKey);
                    break;
                }
            }

            if (!question) throw new Error('Question data not found in any query');

            // Try different field names for question ID
            let questionNumber = null;
            if (question.frontendQuestionId) {
                questionNumber = parseInt(question.frontendQuestionId);
            } else if (question.questionFrontendId) {
                questionNumber = parseInt(question.questionFrontendId);
            } else if (question.questionId) {
                questionNumber = parseInt(question.questionId);
            } else if (question.id) {
                questionNumber = parseInt(question.id);
            }

            // If still no number, try extracting from title
            if (!questionNumber && question.title) {
                const titleMatch = question.title.match(/^(\d+)\./);
                if (titleMatch) {
                    questionNumber = parseInt(titleMatch[1]);
                }
            }

            const extractedData = {
                title: question.title,
                number: questionNumber,
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

            console.log('Extracted data:', extractedData);
            return extractedData;
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

        // Extract problem number from title or URL
        let number = null;
        const titleMatch = title.match(/^(\d+)\./);
        if (titleMatch) {
            number = parseInt(titleMatch[1]);
            title = title.replace(/^\d+\.\s*/, '');
        } else {
            // Try extracting from URL if not in title
            const urlMatch = url.match(/\/problems\/(\d+)-/);
            if (urlMatch) {
                number = parseInt(urlMatch[1]);
            }
        }

        // Extract difficulty with more comprehensive selectors
        const difficultySelectors = [
            '.css-10o4wqw', // Old selector
            '[data-difficulty]',
            '.difficulty-label',
            '.text-difficulty',
            '.text-difficulty-easy',
            '.text-difficulty-medium',
            '.text-difficulty-hard',
            '.text-green-s', // Easy difficulty
            '.text-yellow', // Medium difficulty
            '.text-pink', // Hard difficulty
            '.text-label-1', // New LeetCode styling
            '.text-label-2',
            '.text-label-3',
            '[class*="difficulty"]', // Any class containing "difficulty"
            '[class*="Difficulty"]'
        ];

        let difficulty = '';
        for (const selector of difficultySelectors) {
            const elements = document.querySelectorAll(selector);
            for (const element of elements) {
                const text = element.textContent.trim();
                if (['Easy', 'Medium', 'Hard'].includes(text)) {
                    difficulty = text;
                    console.log(`Found difficulty "${text}" using selector: ${selector}`);
                    break;
                }
                // Check data attributes
                const attr = element.getAttribute('data-difficulty');
                if (attr && ['Easy', 'Medium', 'Hard'].includes(attr)) {
                    difficulty = attr;
                    console.log(`Found difficulty "${attr}" in data-difficulty attribute`);
                    break;
                }
            }
            if (difficulty) break;
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