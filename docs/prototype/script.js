
const stories = [
    {
        key: "SHOP-1",
        title: "Reset password",
        description:
            "As a user, I want to reset my password so that I can log in again.",
        acceptance_criteria: [
            "The user receives a reset link by email",
            "The new password must be at least 8 characters"
        ]
    },
    {
        key: "SHOP-2",
        title: "User login",
        description:
            "As a registered user, I want to log in securely to access my account.",
        acceptance_criteria: [
            "Users must enter a valid email address",
            "Incorrect passwords must be rejected",
            "Only authenticated users can access their account"
        ]
    },
    {
        key: "SHOP-3",
        title: "Product search",
        description:
            "As a customer, I want to search for products by name.",
        acceptance_criteria: [
            "Search results must match the entered product name",
            "An empty search must show a helpful message"
        ]
    }
];

// Temporary mock predictions for the frontend demonstration.
const categoryRules = [
    {
        keywords: ["8 characters", "at least", "maximum", "minimum", "limit"],
        category: "boundary"
    },
    {
        keywords: ["valid email", "empty", "invalid", "required", "rejected"],
        category: "validation"
    },
    {
        keywords: ["securely", "authenticated", "unauthorized", "owner"],
        category: "security"
    },
    {
        keywords: ["under", "seconds", "response time", "fast"],
        category: "performance"
    },
    {
        keywords: ["helpful", "easy", "clear", "understand"],
        category: "usability"
    }
];

const storySelect = document.getElementById("story-select");
const storyKey = document.getElementById("story-key");
const storyTitle = document.getElementById("story-title");
const storyDescription = document.getElementById("story-description");
const criteriaList = document.getElementById("criteria-list");
const generateButton = document.getElementById("generate-btn");
const message = document.getElementById("message");
const testResults = document.getElementById("test-results");

const storyCount = document.getElementById("story-count");
const criteriaCount = document.getElementById("criteria-count");
const testCount = document.getElementById("test-count");
const testStatus = document.getElementById("test-status");

let generatedTestCases = [];

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

function predictCategory(criterion) {
    const text = criterion.toLowerCase();

    const match = categoryRules.find(rule =>
        rule.keywords.some(keyword => text.includes(keyword))
    );

    return match ? match.category : "functional";
}

function loadStoryOptions() {
    storySelect.innerHTML = stories.map(story => `
        <option value="${escapeHTML(story.key)}">
            ${escapeHTML(story.key)} — ${escapeHTML(story.title)}
        </option>
    `).join("");
}

function displayStory() {
    const story = stories.find(item => item.key === storySelect.value);

    if (!story) {
        showMessage("No story is available.", "error");
        return;
    }

    storyKey.textContent = story.key;
    storyTitle.textContent = story.title;
    storyDescription.textContent = story.description;

    criteriaList.innerHTML = story.acceptance_criteria.map(
        (criterion, index) => {
            const category = predictCategory(criterion);

            return `
                <div class="criterion-card">
                    <div class="criterion-number">${index + 1}</div>
                    <div class="criterion-content">
                        <p>${escapeHTML(criterion)}</p>
                        <span class="category-badge ${category}">
                            ${escapeHTML(category)}
                        </span>
                    </div>
                </div>
            `;
        }
    ).join("");

    storyCount.textContent = "01";
    criteriaCount.textContent =
        String(story.acceptance_criteria.length).padStart(2, "0");

    // Clear results from the previously selected story.
    generatedTestCases = [];
    testResults.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">✓</div>
            <h3>No test cases generated</h3>
            <p>Select Generate Test Cases to preview sample results.</p>
        </div>
    `;

    testCount.textContent = "00";
    testStatus.textContent = "Not generated yet";

    showMessage("Story loaded. Ready to generate sample test cases.");
}

function generateTestCases(story) {
    const testCases = [];

    story.acceptance_criteria.forEach((criterion, index) => {
        const category = predictCategory(criterion);

        if (category === "boundary") {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Password below the minimum length is rejected",
                type: category,
                steps: [
                    "Open the relevant page",
                    "Enter a value below the required minimum",
                    "Submit the form"
                ],
                expected:
                    "The application rejects the input and displays an appropriate error."
            });

            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Password at the minimum length is accepted",
                type: category,
                steps: [
                    "Open the relevant page",
                    "Enter a value at the minimum length",
                    "Submit the form"
                ],
                expected:
                    "The application accepts the value if all other requirements are satisfied."
            });
        } else if (category === "validation") {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Invalid input is rejected",
                type: category,
                steps: [
                    "Open the relevant page",
                    "Enter invalid data",
                    "Submit the form"
                ],
                expected:
                    "The application rejects invalid data and explains the problem."
            });
        } else if (category === "security") {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Unauthorized access is prevented",
                type: category,
                steps: [
                    "Open the protected resource without authorization",
                    "Attempt to access the resource"
                ],
                expected:
                    "The application prevents unauthorized access."
            });
        } else if (category === "performance") {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Response time meets the requirement",
                type: category,
                steps: [
                    "Open the relevant page",
                    "Perform the specified action",
                    "Measure the response time"
                ],
                expected:
                    "The operation completes within the specified time limit."
            });
        } else if (category === "usability") {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: "Helpful feedback is displayed",
                type: category,
                steps: [
                    "Perform the relevant action",
                    "Review the displayed message"
                ],
                expected:
                    "The message is clear and helps the user understand what to do."
            });
        } else {
            testCases.push({
                story_key: story.key,
                id: `${story.key}-TC${testCases.length + 1}`,
                title: `Verify requirement: ${criterion}`,
                type: category,
                steps: [
                    "Open the relevant page",
                    `Perform the action described by: ${criterion}`
                ],
                expected:
                    `The application satisfies the requirement: ${criterion}`
            });
        }
    });

    return testCases;
}

function displayTestCases(testCases) {
    if (testCases.length === 0) {
        testResults.innerHTML = `
            <div class="empty-state">
                <h3>No test cases available</h3>
                <p>Try selecting another story.</p>
            </div>
        `;
        return;
    }

    testResults.innerHTML = testCases.map(testCase => `
        <article class="test-card">
            <span class="category-badge ${escapeHTML(testCase.type)}">
                ${escapeHTML(testCase.type)}
            </span>
            <h3>${escapeHTML(testCase.title)}</h3>
            <p class="muted">
                ${escapeHTML(testCase.id)} ·
                ${escapeHTML(testCase.story_key)}
            </p>

            <h4>Test Steps</h4>
            <ol>
                ${testCase.steps.map(step =>
                    `<li>${escapeHTML(step)}</li>`
                ).join("")}
            </ol>

            <h4>Expected Result</h4>
            <div class="expected-result">
                ${escapeHTML(testCase.expected)}
            </div>
        </article>
    `).join("");
}

function showMessage(text, type = "") {
    message.textContent = text;
    message.className = type ? `message ${type}` : "message";
}

function handleGenerate() {
    const story = stories.find(item => item.key === storySelect.value);

    if (!story) {
        showMessage("Please select a valid story.", "error");
        return;
    }

    generateButton.disabled = true;
    generateButton.textContent = "Generating...";

    try {
        generatedTestCases = generateTestCases(story);
        displayTestCases(generatedTestCases);

        testCount.textContent =
            String(generatedTestCases.length).padStart(2, "0");

        testStatus.textContent = "Sample results generated";

        showMessage(
            `Generated ${generatedTestCases.length} sample test case(s). ` +
            "Categories and results are illustrative mock data.",
            "success"
        );
    } catch (error) {
        console.error(error);
        showMessage("Something went wrong while generating sample cases.", "error");
    } finally {
        generateButton.disabled = false;
        generateButton.textContent = "Generate Test Cases";
    }
}

storySelect.addEventListener("change", displayStory);
generateButton.addEventListener("click", handleGenerate);

loadStoryOptions();
displayStory();
