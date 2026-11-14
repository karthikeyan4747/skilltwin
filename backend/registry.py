"""Feature registry: each problem-statement requirement mapped to its UI route, API tag,
implementing modules and tests. /about, /api/v1/meta and the docs consistency test read it."""

from dataclasses import dataclass

REPO_URL = "https://github.com/karthikeyan4747/skilltwin"


@dataclass(frozen=True)
class Feature:
    id: str
    title: str
    requirement: str
    ui_route: str
    api_tag: str
    modules: tuple[str, ...]
    tests: tuple[str, ...]
    required: bool = True


FEATURES: tuple[Feature, ...] = (
    Feature(
        "profile",
        "User Profile",
        "Maintain learner details, existing skills, certifications, projects and career goals.",
        "#/profile",
        "User Profile",
        ("backend/api/routes/profile.py", "frontend/js/views/profile.js"),
        ("tests/test_api.py",),
    ),
    Feature(
        "analysis",
        "Skill Analysis",
        "Identify strengths and weaknesses based on skills and assessments.",
        "#/analysis",
        "Skill Analysis",
        ("backend/core/analysis.py", "frontend/js/views/analysis.js"),
        ("tests/core/test_analysis.py",),
    ),
    Feature(
        "career",
        "Career Matching",
        "Compare current skills with the requirements of a selected job role.",
        "#/career",
        "Career Matching",
        ("backend/core/career.py", "backend/services/jobs.py", "frontend/js/views/career.js"),
        ("tests/core/test_career.py", "tests/test_services.py"),
    ),
    Feature(
        "recommendations",
        "Learning Recommendations",
        "Suggest relevant courses, tutorials and practical exercises.",
        "#/roadmap",
        "Learning Recommendations",
        (
            "backend/core/roadmap.py",
            "backend/agents/recommender.py",
            "frontend/js/views/roadmap.js",
        ),
        ("tests/core/test_roadmap.py",),
    ),
    Feature(
        "progress",
        "Progress Tracking",
        "Monitor learning progress and assessment performance.",
        "#/progress",
        "Progress Tracking",
        ("backend/core/progress.py", "backend/core/twin.py", "frontend/js/views/progress.js"),
        ("tests/core/test_small_modules.py",),
    ),
    Feature(
        "mentor",
        "AI Mentor",
        "Provide guidance and update learning recommendations based on individual performance.",
        "#/mentor",
        "AI Mentor",
        (
            "backend/agents/mentor.py",
            "backend/orchestrator/coaching.py",
            "frontend/js/views/mentor.js",
        ),
        ("tests/test_orchestrator.py",),
    ),
    Feature(
        "assessment",
        "Assessment",
        "Evidence from MCQ, explain-back, predict-output, code and work-ticket questions; "
        "a failed answer reroutes the roadmap to its root cause.",
        "#/assessment",
        "Assessment",
        ("backend/orchestrator/questions.py", "backend/orchestrator/assessment.py"),
        ("tests/test_orchestrator.py", "tests/test_sample_scenario.py"),
        required=False,
    ),
    Feature(
        "scenario",
        "Sample Scenario",
        "One click: a failed React answer reroutes to its root cause, then the goal switches.",
        "#/dashboard",
        "Sample Scenario",
        ("backend/orchestrator/scenario.py", "frontend/js/views/dashboard.js"),
        ("tests/test_sample_scenario.py",),
        required=False,
    ),
    Feature(
        "twin",
        "Learner Twin",
        "Predicts answers before submission and simulates a day of work tickets.",
        "#/mentor",
        "Learner Twin",
        ("backend/agents/twin.py", "backend/core/twin.py"),
        ("tests/test_orchestrator.py",),
        required=False,
    ),
    Feature(
        "lessons",
        "Lessons",
        "Python code visualizer and a JavaScript grid game that records code evidence.",
        "#/lessons",
        "Lessons",
        ("backend/core/grid.py", "frontend/js/views/lessons.js"),
        ("tests/test_api.py",),
        required=False,
    ),
    Feature(
        "publish",
        "Learn in Public",
        "LinkedIn draft and learning log generated from verified evidence.",
        "#/publish",
        "Learn in Public",
        ("backend/agents/publisher.py", "frontend/js/views/publish.js"),
        ("tests/test_api.py",),
        required=False,
    ),
    Feature(
        "insights",
        "Institution Insights",
        "Top cohort misconceptions per skill for universities and employers.",
        "#/insights",
        "Institution Insights",
        ("backend/core/insights.py", "frontend/js/views/insights.js"),
        ("tests/core/test_small_modules.py",),
        required=False,
    ),
)

ADAPTATION_LOOPS: tuple[tuple[str, str], ...] = (
    (
        "Poor performance",
        "A failed answer walks the prerequisite graph to the deepest unverified skill and "
        "moves that path to the front of the roadmap (backend/orchestrator/assessment.py).",
    ),
    (
        "Career goal change",
        "Verified skills carry over to the new role and the roadmap is rebuilt for the "
        "remaining gap only (backend/orchestrator/planning.py).",
    ),
)
