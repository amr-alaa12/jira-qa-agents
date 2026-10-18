# Jira QA Agents

**A Multi-Agent LLM Framework for Automated UI Test Generation and Self-Healing**

## Project Overview

Jira QA Agents is a research project exploring the use of Large Language Models (LLMs) and multi-agent systems to automate the software UI testing lifecycle.

The proposed framework transforms Jira user stories and acceptance criteria into executable UI test scripts, evaluates test failures, and investigates self-healing techniques to improve test robustness as web applications evolve.

## Research Objectives

- **Requirements Analysis:** Extract user stories and acceptance criteria from Jira and identify ambiguity or quality issues.
- **Requirements Classification:** Classify requirements as Functional Requirements (FR) or Non-Functional Requirements (NFR), including relevant quality attributes.
- **Test Case Generation:** Generate structured test cases from user stories and acceptance criteria using LLM-based agents.
- **Test Script Generation:** Convert generated test cases into executable UI automation scripts using Playwright and Python.
- **Multi-Agent Orchestration:** Investigate how specialized AI agents can collaborate to generate, review, and improve test artifacts.
- **Failure Analysis:** Analyze execution failures to distinguish potential locator issues from other test or application failures.
- **Self-Healing UI Tests:** Investigate techniques for identifying replacement UI elements and repairing broken locators.
- **Evaluation:** Measure test-generation quality, execution success, repair accuracy, and overall framework performance.

## Proposed Workflow

1. Retrieve user stories and acceptance criteria from Jira.
2. Analyze requirements quality and detect ambiguity.
3. Classify requirements and identify relevant quality attributes.
4. Generate test cases from acceptance criteria.
5. Generate executable Playwright test scripts.
6. Execute tests and collect results.
7. Analyze failures and investigate possible locator repairs.
8. Re-run repaired tests and evaluate the results.

## Planned Technology Stack

- **Programming Language:** Python
- **Artificial Intelligence:** Large Language Models (LLMs)
- **Architecture:** Multi-agent system
- **Requirements Source:** Jira REST API
- **UI Automation:** Playwright
- **Test Framework:** pytest
- **Version Control:** Git and GitHub

Specific libraries and orchestration frameworks will be selected as the implementation develops.

## Research and Evaluation

The project will investigate the following evaluation dimensions:

- Accuracy and completeness of generated test cases.
- Traceability between acceptance criteria and generated tests.
- Executable test-script success rate.
- Comparison between single-agent and multi-agent approaches.
- Accuracy of failure classification and locator repair.
- Test recovery rate after UI changes.
- Limitations, reliability, and reproducibility of LLM-generated artifacts.

Evaluation methods and baselines will be defined during the research process.

## Literature Review

The research draws on existing work in:

- User story quality assessment and requirements engineering.
- Functional and non-functional requirements classification.
- LLM-based test case and test script generation.
- Multi-agent LLM orchestration for software engineering.
- Self-healing locators and automated web test repair.

Relevant papers, implementation notes, and experimental findings will be documented throughout the project.

