// Enhanced debug script for LeetCode difficulty extraction
// Paste this in browser console on a LeetCode problem page

console.log("🔍 LeetCode Difficulty Extraction Debug v2");
console.log("==========================================");

// Test the fixed __NEXT_DATA__ extraction
function testNextDataExtraction() {
    console.log("\n1. Testing __NEXT_DATA__ extraction:");

    const nextDataScript = document.querySelector('#__NEXT_DATA__');
    if (!nextDataScript) {
        console.log("❌ No __NEXT_DATA__ script found");
        return null;
    }

    const data = JSON.parse(nextDataScript.textContent);
    const queries = data.props?.pageProps?.dehydratedState?.queries || [];

    console.log(`📊 Found ${queries.length} queries`);

    let question = null;
    queries.forEach((query, i) => {
        console.log(`  Query ${i}:`, query.queryKey);
        if (query.state?.data?.question) {
            question = query.state.data.question;
            console.log(`  ✅ Found question data in query ${i} (${query.queryKey})`);
            console.log(`     - Title: ${question.title}`);
            console.log(`     - Number: ${question.frontendQuestionId}`);
            console.log(`     - Difficulty: ${question.difficulty}`);
            console.log(`     - Tags: ${question.topicTags?.map(t => t.name).join(', ') || 'None'}`);
        }
    });

    return question;
}

// Test DOM fallback extraction
function testDOMExtraction() {
    console.log("\n2. Testing DOM difficulty extraction:");

    const difficultySelectors = [
        '.css-10o4wqw',
        '[data-difficulty]',
        '.difficulty-label',
        '.text-difficulty',
        '.text-difficulty-easy',
        '.text-difficulty-medium',
        '.text-difficulty-hard',
        '.text-green-s',
        '.text-yellow',
        '.text-pink',
        '.text-label-1',
        '.text-label-2',
        '.text-label-3',
        '[class*="difficulty"]',
        '[class*="Difficulty"]'
    ];

    let foundDifficulty = null;

    difficultySelectors.forEach(selector => {
        try {
            const elements = document.querySelectorAll(selector);
            elements.forEach((element, i) => {
                const text = element.textContent.trim();
                if (['Easy', 'Medium', 'Hard'].includes(text)) {
                    console.log(`✅ Found "${text}" using selector: ${selector} (element ${i})`);
                    if (!foundDifficulty) foundDifficulty = text;
                }

                const attr = element.getAttribute('data-difficulty');
                if (attr && ['Easy', 'Medium', 'Hard'].includes(attr)) {
                    console.log(`✅ Found "${attr}" in data-difficulty attribute using selector: ${selector}`);
                    if (!foundDifficulty) foundDifficulty = attr;
                }
            });
        } catch (e) {
            console.log(`❌ Error with selector ${selector}:`, e.message);
        }
    });

    if (!foundDifficulty) {
        console.log("❌ No difficulty found via DOM extraction");

        // Let's search more broadly
        console.log("\n🔍 Searching for any element containing 'Easy', 'Medium', or 'Hard':");
        const allElements = document.querySelectorAll('*');
        let found = 0;
        allElements.forEach(el => {
            const text = el.textContent?.trim();
            if (text && ['Easy', 'Medium', 'Hard'].includes(text) && found < 5) {
                console.log(`  Found "${text}" in <${el.tagName.toLowerCase()}> with classes: ${el.className}`);
                found++;
            }
        });
    }

    return foundDifficulty;
}

// Test complete extraction
function testCompleteExtraction() {
    console.log("\n3. Testing complete extraction (like bookmarklet would do):");

    const nextDataResult = testNextDataExtraction();
    const domResult = testDOMExtraction();

    const finalResult = {
        url: window.location.href,
        title: nextDataResult?.title || document.querySelector('h1')?.textContent?.trim() || '',
        number: nextDataResult?.frontendQuestionId ? parseInt(nextDataResult.frontendQuestionId) : null,
        difficulty: nextDataResult?.difficulty || domResult || '',
        tags: nextDataResult?.topicTags?.map(t => t.name) || [],
        description: nextDataResult?.content || '',
        slug: nextDataResult?.titleSlug || window.location.pathname.split('/')[2]
    };

    console.log("\n🎯 Final extracted data:");
    console.table(finalResult);

    console.log("\n📋 Copy this for testing API:");
    console.log(JSON.stringify(finalResult, null, 2));

    return finalResult;
}

// Run all tests
const result = testCompleteExtraction();

// Also test what would happen if we send this to the API
console.log("\n4. Testing API payload:");
console.log("This is what would be sent to /api/add-problem:");
console.log(JSON.stringify(result, null, 2));