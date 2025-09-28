// Debug script to understand __NEXT_DATA__ structure on LeetCode
// Paste this in browser console on a LeetCode problem page

const nextDataScript = document.querySelector('#__NEXT_DATA__');
if (nextDataScript) {
    const data = JSON.parse(nextDataScript.textContent);

    console.log("Full __NEXT_DATA__ structure:");
    console.log(data);

    // Try different paths to find difficulty
    console.log("\n=== Trying different paths for difficulty ===");

    // Path 1: The one we're currently using
    const question1 = data.props?.pageProps?.dehydratedState?.queries?.[0]?.state?.data?.question;
    console.log("Path 1 (current): data.props.pageProps.dehydratedState.queries[0].state.data.question");
    console.log("Difficulty:", question1?.difficulty);

    // Path 2: Alternative query structure
    const queries = data.props?.pageProps?.dehydratedState?.queries;
    if (queries) {
        queries.forEach((query, i) => {
            console.log(`\nQuery ${i}:`, query.queryKey);
            if (query.state?.data?.question) {
                console.log(`  - Has question data`);
                console.log(`  - Difficulty:`, query.state.data.question.difficulty);
            }
        });
    }

    // Path 3: Check pageProps directly
    console.log("\n=== Checking pageProps directly ===");
    console.log("pageProps keys:", Object.keys(data.props?.pageProps || {}));

    // Path 4: Look for any difficulty fields
    console.log("\n=== Searching for 'difficulty' field anywhere ===");
    function findDifficulty(obj, path = '') {
        if (!obj || typeof obj !== 'object') return;

        for (const key in obj) {
            if (key === 'difficulty' && typeof obj[key] === 'string') {
                console.log(`Found at ${path}.${key}:`, obj[key]);
            } else if (typeof obj[key] === 'object') {
                findDifficulty(obj[key], path ? `${path}.${key}` : key);
            }
        }
    }

    findDifficulty(data);
} else {
    console.log("No __NEXT_DATA__ script found on this page");
}