from sufe_cli.commands.canvas.assignment import build_assignment_rows


def test_build_assignment_rows_merges_assignments_and_submissions() -> None:
    rows = build_assignment_rows(
        [
            {
                "assignments": [
                    {"id": 30662, "name": "Homework 2", "due_at": "2025-11-02T14:00:00Z", "points_possible": 140},
                    {"id": 30663, "name": "Homework 3", "due_at": "2025-11-09T14:00:00Z", "points_possible": 100},
                ],
            }
        ],
        [{"assignment_id": 30662, "grade": "100", "submitted_at": "2025-10-12T09:47:00Z"}],
    )

    assert rows == [
        {
            "id": 30662,
            "name": "Homework 2",
            "due_at": "2025-11-02 22:00",
            "points_possible": 140,
            "grade": "100",
            "submitted_at": "2025-10-12 17:47",
        },
        {
            "id": 30663,
            "name": "Homework 3",
            "due_at": "2025-11-09 22:00",
            "points_possible": 100,
            "grade": None,
            "submitted_at": None,
        },
    ]
