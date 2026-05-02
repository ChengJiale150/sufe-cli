from sufe_cli.commands.canvas.course import extract_course, sort_and_slice_courses


def test_extract_course_normalizes_time_and_roles() -> None:
    course = extract_course(
        {
            "id": 40442,
            "name": "深度学习（0875）",
            "workflow_state": "available",
            "created_at": "2026-02-25T04:03:12Z",
            "enrollments": [{"type": "ta", "role": "TaEnrollment", "user_id": 53509}, {}],
        }
    )

    assert course == {
        "id": 40442,
        "name": "深度学习（0875）",
        "workflow_state": "available",
        "created_at": "2026-02-25 12:03",
        "roles": ["TaEnrollment"],
    }


def test_sort_and_slice_courses_by_created_at_desc() -> None:
    courses = [
        {"id": 1, "name": "A", "created_at": "2025-09-01 16:00"},
        {"id": 2, "name": "B", "created_at": "2026-02-25 12:03"},
        {"id": 3, "name": "C", "created_at": "2024-01-01 08:00"},
    ]

    assert sort_and_slice_courses(courses, "created_at", "desc", limit=2, offset=0) == [
        {"id": 2, "name": "B", "created_at": "2026-02-25 12:03"},
        {"id": 1, "name": "A", "created_at": "2025-09-01 16:00"},
    ]
