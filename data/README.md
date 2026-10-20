# Requirements Dataset

## Overview

This folder contains the labeled dataset used to train the requirement classification model for the Jira QA Agents project.

The dataset contains software requirements labeled into six categories. The classifier uses these examples to learn how to identify the type of each acceptance criterion or requirement.

## Dataset File

**File:** `requirements.csv`

The CSV file contains two columns:

| Column | Description |
|---|---|
| `text` | A software requirement or acceptance criterion. |
| `category` | The category assigned to that requirement. |

Example:

```csv
text,category
"The user can reset their password using a link sent by email",functional
"The email address is required and cannot be left empty",validation
"The password must be at least 8 characters long",boundary
"Only an admin can access the admin dashboard",security
"The dashboard loads in under 2 seconds",performance
"The interface is accessible to screen reader users",usability
```

## Categories

Every example must use exactly one of the following category labels:

- **functional** — Describes a feature or action the system must perform.
- **validation** — Describes checks that determine whether user input is valid.
- **boundary** — Describes limits, ranges, minimums, maximums, or edge cases.
- **security** — Describes authentication, authorization, privacy, or protection against attacks.
- **performance** — Describes response times, throughput, scalability, or system responsiveness.
- **usability** — Describes ease of use, accessibility, navigation, or interface clarity.

Use the category names exactly as written above.

## Dataset Requirements

The dataset should satisfy these minimum requirements:

- At least 1,000 labeled examples overall.
- At least 50 examples for each of the six categories.
- Exactly two columns: `text` and `category`.
- No empty requirement text.
- No invalid category labels.
- No duplicate requirement texts, ignoring capitalization.

## Validating the Dataset

From the project root directory, run:

```bash
python data/validate_dataset.py
```

The validation script checks the CSV columns, empty text, category labels, duplicate texts, total number of rows, and minimum examples per category.

The script should report that the dataset is valid when all checks pass.

## Building the Dataset

The dataset-generation script creates `requirements.csv` from predefined phrase templates.

From the project root directory, run:

```bash
python data/build_dataset.py
```

After regenerating the dataset, validate it again:

```bash
python data/validate_dataset.py
```

## Adding New Examples

You can expand the dataset by either:

1. Adding new requirement templates to `build_dataset.py` and regenerating the CSV.
2. Adding new rows directly to `requirements.csv`.

Every new row must contain a requirement and one valid category label. Avoid duplicate examples and ensure that each requirement genuinely matches its assigned category.

After making changes, run the validation script.

## Limitations

The current dataset uses synthetic examples generated from predefined templates. Although this helps create a balanced dataset quickly, the examples may not represent the full variety of real-world Jira requirements.

The classifier's performance should therefore be evaluated on separate, realistic requirements that were not used for training. Additional real-world examples may be needed to improve generalization.

## Integration

The dataset is intended for use by the requirement-classification component. The classifier should read the `text` column as input and use the `category` column as the target label.

The six category names must remain consistent across the dataset, classifier, test generator, and web application.
