"""Application configuration for Swim Journey."""

PAGE_TITLE = "Riya's Swim Journey"
PAGE_ICON = "🏊‍♀️"
SUBTITLE = "Every swim is a step forward. 🌊"

DEFAULT_SWIMMER = "Riya Kalro"

CACHE_TTL_SECONDS = 300  # 5 minutes

RESULTS_TAB_NAME = "Results"

EXPECTED_COLUMNS = [
    "Swimmer Name",
    "Swim Date",
    "Meet Name",
    "Distance",
    "Stroke",
    "Course",
    "Time",
    "Result Type",
    "Notes",
    "Source URL",
]

VALID_COURSES = ("SCY", "SCM", "LCM")

# Result types that must be excluded from personal-best calculations
EXCLUDED_RESULT_TYPE_KEYWORDS = ("dq", "disqualified", "relay", "split", "exhibition", "unofficial")
