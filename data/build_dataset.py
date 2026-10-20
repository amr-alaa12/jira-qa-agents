"""Builds data/requirements.csv (text,category) from phrase templates.

Run:  python data/build_dataset.py
To add more rows: add items to the lists/templates below (or append rows
by hand to requirements.csv), then run validate_dataset.py.
"""
import csv, itertools, os, random

random.seed(42)
PER_CATEGORY = 200
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.csv")

def cap(s):
    return s[0].upper() + s[1:]

# ---------------------------------------------------------------- functional
actors = ["The user", "A registered user", "The customer", "An admin", "A logged-in user", "The shopper", "The manager", "A new visitor"]
actions = [
    "reset their password using a link sent by email", "add an item to the shopping cart", "remove an item from the shopping cart",
    "update their profile picture", "log out from any page", "save a draft and continue editing later", "download an invoice as a PDF",
    "search products by name", "filter the results by price", "sort the list by date", "create a new project", "delete their own comment",
    "share a document with another user", "mark a task as completed", "subscribe to the newsletter", "unsubscribe from email notifications",
    "view the order history", "cancel an order before it ships", "track the delivery status of an order", "change the display language",
    "export the report to CSV", "add a product to the wishlist", "apply a discount code at checkout", "pay with a saved card",
    "edit a submitted form", "upload a document to a ticket", "assign a ticket to a team member", "reopen a closed ticket",
    "bookmark an article", "rate a purchased product", "invite a colleague by email", "switch between accounts",
    "schedule a meeting from the calendar", "print the booking confirmation", "add a comment to a story", "follow another user",
]
sys_actions = [
    "sends a confirmation email after registration", "creates an order when the payment succeeds", "updates the stock count after each purchase",
    "saves the form data when the user clicks Save", "shows a success message after the profile is updated", "sends a reset link to the registered email address",
    "generates an invoice for every completed order", "notifies the assignee when a ticket is reassigned", "logs the user out when they click Log out",
    "redirects the user to the dashboard after login", "refreshes the list after a new item is added", "sends a reminder email one day before the due date",
    "removes the item from the list after it is deleted", "stores the selected language for the next visit", "creates a receipt after each payment",
    "calculates the order total including tax", "updates the cart total when the quantity changes", "displays the correct number of search results",
    "marks the order as shipped when the courier collects it", "sends a push notification when a new message arrives", "archives a project when the owner closes it",
    "restores the previous version when the user clicks Undo", "adds the new user to the selected team", "shows the latest five notifications on the home page",
]
events = ["the order is placed", "the user submits the form", "the payment is completed", "the account is created", "the file is uploaded", "the ticket is closed", "the user clicks Save", "the item is deleted"]
results = [
    "a confirmation message is displayed", "a confirmation email is sent to the user", "the change appears in the activity history",
    "the dashboard shows the updated information", "the user is taken to the next page", "the record is saved in the system",
]
functional = set()
for a, ac in itertools.product(actors, actions):
    functional.add(f"{a} can {ac}")
for s in sys_actions:
    functional.add(f"The system {s}")
for e, r in itertools.product(events, results):
    functional.add(f"After {e}, {r}")

# ---------------------------------------------------------------- validation
fields = ["email address", "phone number", "postal code", "date of birth", "credit card number", "username", "coupon code", "website URL",
          "first name", "last name", "street address", "country field", "password confirmation", "IBAN", "national ID number", "search keyword",
          "quantity field", "start date", "end date", "invoice number"]
val_templates = [
    "The system rejects an invalid {f}", "The {f} is required and cannot be left empty", "An error message is shown when the {f} has an incorrect format",
    "Submitting the form with a blank {f} is not allowed", "The {f} must not contain special characters", "The form cannot be submitted until the {f} is valid",
    "The {f} is checked for the correct format before the data is saved", "A duplicate {f} is not accepted", "Entering letters in the {f} shows a validation error",
    "The system does not accept an {f} that contains only spaces",
]
extra_validation = [
    "The email address must contain an @ symbol", "The end date must be later than the start date", "The date of birth cannot be a future date",
    "The phone number must contain digits only", "The password confirmation must match the password", "Expired credit cards are rejected at checkout",
    "The postal code must match the selected country format", "Uploaded files must be PDF, PNG or JPG only", "Files with unsupported types are rejected",
    "Negative numbers are not accepted in the quantity field", "The coupon code must exist and still be active", "An unknown username is rejected with an error message",
    "Required fields are marked and checked before submission", "Script tags entered in text fields are rejected", "The name field must not contain numbers",
    "The URL must start with http or https", "The password must include at least one number and one letter", "A comment cannot be submitted when it is empty",
    "The selected delivery date must be a working day", "Decimal values are not allowed in the number of guests",
]
validation = set(extra_validation)
for f, t in itertools.product(fields, val_templates):
    validation.add(cap(t.format(f=f)))

# ------------------------------------------------------------------ boundary
bfields = [("password", "characters"), ("username", "characters"), ("comment", "characters"), ("project name", "characters"),
           ("display name", "characters"), ("description", "characters"), ("message", "characters"), ("title", "characters")]
boundary = set()
for (f, u), n in itertools.product(bfields, [3, 5, 6, 8, 10, 12, 15, 20, 30, 50, 100, 255, 500]):
    boundary.add(f"The {f} must be at least {n} {u} long")
    boundary.add(f"The {f} cannot be longer than {n} {u}")
for (f, u), n in itertools.product(bfields[:4], [4, 8, 16, 32]):
    boundary.add(f"A {f} with exactly {n} {u} is accepted")
for item, lo, hi in [("quantity", 1, 10), ("quantity", 1, 99), ("rating", 1, 5), ("age", 18, 65), ("number of guests", 1, 8), ("discount", 0, 50),
                     ("page size", 10, 100), ("temperature setting", 16, 30), ("number of seats", 1, 6), ("volume", 0, 100), ("loan term in years", 1, 30), ("room count", 1, 4)]:
    boundary.add(f"The {item} must be between {lo} and {hi}")
    boundary.add(f"A {item} of {hi + 1} is rejected while {hi} is accepted")
    boundary.add(f"A {item} below {lo} is not allowed")
for n in [1, 2, 5, 10, 20, 25, 50]:
    boundary.add(f"Users can add up to {n} items to the cart")
    boundary.add(f"A user can upload a maximum of {n} files at one time")
    boundary.add(f"Each team can have no more than {n} members")
    boundary.add(f"The maximum file upload size is {n} MB")
for n in [3, 5, 10]:
    boundary.add(f"The account is locked after {n} failed login attempts")
    boundary.add(f"The user can request a password reset at most {n} times per day")
for n in [18, 21, 16, 13, 65]:
    boundary.add(f"Users must be {n} years or older to register")
for n in [0, 1, 99, 100, 999]:
    boundary.add(f"The minimum order amount is {n} dollars")
    boundary.add(f"Orders above {n + 1000} dollars require manager approval")

# ------------------------------------------------------------------ security
roles = ["an admin", "the account owner", "a manager", "an authenticated user", "a team lead", "a finance user"]
sec_actions = ["view the audit log", "delete a user account", "change another user's role", "download customer data", "approve refunds",
               "see the billing page", "edit system settings", "export all orders", "access the admin dashboard", "view private projects"]
resources = ["the admin dashboard", "other users' orders", "the billing information of another account", "private documents", "the user management page",
             "the system settings", "confidential reports", "another user's profile data"]
security = set()
for r, a in itertools.product(roles, sec_actions):
    security.add(f"Only {r} can {a}")
for res in resources:
    security.add(f"Users without permission cannot access {res}")
    security.add(f"Unauthenticated users are redirected to the login page when opening {res}")
    security.add(f"Access to {res} is recorded in the audit log")
security.update([
    "Passwords are stored as salted hashes", "All traffic between the browser and the server uses HTTPS", "Passwords are never shown in plain text",
    "Sessions expire after a period of inactivity", "The user is logged out when the session token expires", "Credit card numbers are encrypted at rest",
    "Login is protected against brute-force attacks", "The system is protected against SQL injection", "User input is sanitized to prevent cross-site scripting",
    "API requests require a valid authentication token", "Sensitive data does not appear in log files", "Two-factor authentication is available for all accounts",
    "Password reset links can be used only once", "Password reset links expire after use", "Session cookies are marked as secure and HttpOnly",
    "The system blocks requests from unauthorized IP addresses", "Personal data is deleted when the user requests account removal",
    "Error messages do not reveal whether an email address is registered", "Uploaded files are scanned for malware", "API keys are never exposed in the browser",
    "Cross-site request forgery tokens are required for form submissions", "Users cannot view orders that belong to other users by changing the URL",
    "Role-based access control limits what each user can do", "Failed login attempts are logged", "Data is encrypted during transfer between services",
    "Users must re-enter their password before changing their email address", "Admin actions require a second confirmation step",
    "Access tokens cannot be reused after logout", "Personal information is masked in exported reports", "The system complies with data protection regulations",
])

# --------------------------------------------------------------- performance
pages = ["home page", "login page", "dashboard", "product page", "checkout page", "search results page", "profile page", "report page", "order history page", "settings page"]
performance = set()
for p, n in itertools.product(pages, [1, 2, 3, 5]):
    performance.add(f"The {p} loads in under {n} seconds")
for n in [100, 200, 300, 500, 1000]:
    performance.add(f"The API responds within {n} milliseconds for 95 percent of requests")
    performance.add(f"Search results appear within {n} milliseconds of typing")
for n in [100, 500, 1000, 5000, 10000]:
    performance.add(f"The system supports {n} concurrent users without slowing down")
    performance.add(f"The application handles {n} requests per second")
for n in [2, 5, 10, 30]:
    performance.add(f"Exporting a report takes less than {n} seconds")
    performance.add(f"File uploads of 10 MB complete within {n} seconds")
    performance.add(f"The payment is processed within {n} seconds")
performance.update([
    "The application stays responsive under heavy load", "Database queries finish quickly even with one million records",
    "Pages remain fast when many users are online at the same time", "The system recovers from a traffic spike within one minute",
    "Images are compressed so that pages load quickly on slow connections", "The mobile app starts in under three seconds",
    "Memory usage stays stable during long sessions", "Batch jobs finish within the nightly maintenance window",
    "The system scales automatically when traffic increases", "Large lists load without noticeable delay",
    "The system is available 99.9 percent of the time", "Response time does not degrade as the number of records grows",
    "Notifications are delivered within a few seconds", "Caching is used to reduce page load time", "Scrolling through long lists is smooth",
])

# ----------------------------------------------------------------- usability
screens = ["checkout page", "registration form", "dashboard", "settings page", "search page", "login page", "profile page", "booking form", "help page", "order page"]
usability = set()
for s in screens:
    usability.update([
        f"The {s} is easy to use on a mobile phone", f"The {s} has clear labels on every button", f"The {s} can be used with the keyboard only",
        f"The {s} uses a consistent layout with the rest of the application", f"Help text is shown next to complicated fields on the {s}",
        f"The text on the {s} is easy to read", f"A new user can complete the {s} without any training",
        f"The {s} works well on small screens", f"The {s} is accessible to screen reader users",
        f"The {s} shows a clear progress indicator",
    ])
usability.update([
    "Error messages are written in plain language", "Error messages explain how to fix the problem", "All images have descriptive alt text",
    "The color contrast meets accessibility guidelines", "Important actions are easy to find from the main menu", "The interface supports a dark mode",
    "Users can undo their last action", "Tooltips explain icons that are not self-explanatory", "The application supports multiple languages",
    "Font size can be increased without breaking the layout", "The navigation menu is the same on every page", "A confirmation dialog appears before deleting data",
    "Required fields are clearly marked", "The user always knows which step of the process they are on", "Buttons are large enough to tap on a touch screen",
    "The layout adapts to tablets and desktops", "Success messages are clear and easy to notice", "The search box is visible on every page",
    "Users can find the help section within two clicks", "The design looks the same in all supported browsers",
])


# ---- extra variety so every category can reach PER_CATEGORY
data_items = ["customer records", "payment details", "personal messages", "uploaded documents", "account settings", "health records", "employee salaries", "login credentials"]
for d in data_items:
    security.update([
        f"{cap(d)} are encrypted when stored", f"{cap(d)} are encrypted when sent over the network", f"{cap(d)} can only be read by authorized users",
        f"Every change to {d} is recorded with the user and time", f"{cap(d)} are never included in error messages",
    ])
for n in [250, 750, 2000, 3000]:
    performance.add(f"The API responds within {n} milliseconds for 95 percent of requests")
    performance.add(f"The system supports {n} concurrent users without slowing down")
for p_ in pages:
    performance.update([
        f"The {p_} stays fast when 1000 users are online", f"The {p_} remains responsive on a slow mobile connection",
        f"The {p_} does not freeze while data is loading", f"The {p_} renders its main content quickly",
    ])
for op in ["Saving a record", "Logging in", "Sending a message", "Generating an invoice", "Importing a CSV file", "Running a search", "Loading the activity feed", "Syncing data to the server"]:
    for n in [1, 3, 5]:
        performance.add(f"{op} takes less than {n} seconds")
for s_ in screens:
    usability.update([
        f"Users can complete the main task on the {s_} in only a few steps", f"The {s_} gives immediate feedback after every action",
        f"Links and buttons on the {s_} are easy to tell apart", f"The {s_} avoids technical jargon", f"The {s_} looks tidy and is not cluttered",
        f"The {s_} remembers the user's preferences", f"Users can easily go back from the {s_} without losing their data",
    ])

POOLS = {"functional": functional, "validation": validation, "boundary": boundary,
         "security": security, "performance": performance, "usability": usability}

rows = []
for cat, pool in POOLS.items():
    items = sorted(pool)
    random.shuffle(items)
    chosen = items[:PER_CATEGORY]
    print(f"{cat:12s} available={len(items):4d} used={len(chosen)}")
    rows += [(t, cat) for t in chosen]
random.shuffle(rows)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "category"])
    w.writerows(rows)
print(f"Wrote {len(rows)} rows to {OUT}")
