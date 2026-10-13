import unittest
from datetime import date
from services.analytics_service import count_completed_workouts, current_streak, longest_streak, kg_to_unit, unit_to_kg, workout_volume, total_reps

class AnalyticsTests(unittest.TestCase):
    def test_completed_count(self):
        rows = [{"status":"completed"},{"status":"active"},{"status":"abandoned"}]
        self.assertEqual(count_completed_workouts(rows), 1)

    def test_streak_including_today(self):
        rows = [{"status":"completed","workout_date":"2026-10-11"},{"status":"completed","workout_date":"2026-10-12"},{"status":"completed","workout_date":"2026-10-13"}]
        self.assertEqual(current_streak(rows, date(2026,10,13)), 3)

    def test_streak_can_end_yesterday(self):
        rows = [{"status":"completed","workout_date":"2026-10-11"},{"status":"completed","workout_date":"2026-10-12"}]
        self.assertEqual(current_streak(rows, date(2026,10,13)), 2)

    def test_longest_streak(self):
        rows = [{"status":"completed","workout_date":"2026-10-01"},{"status":"completed","workout_date":"2026-10-02"},{"status":"completed","workout_date":"2026-10-05"},{"status":"completed","workout_date":"2026-10-06"},{"status":"completed","workout_date":"2026-10-07"}]
        self.assertEqual(longest_streak(rows), 3)

    def test_volume_and_reps_ignore_incomplete(self):
        rows = [{"weight_kg":40,"reps":12,"completed":True},{"weight_kg":50,"reps":8,"completed":False}]
        self.assertEqual(workout_volume(rows), 480)
        self.assertEqual(total_reps(rows), 12)

    def test_units_roundtrip(self):
        self.assertAlmostEqual(unit_to_kg(220.46226218, "lb"), 100, places=5)
        self.assertAlmostEqual(kg_to_unit(100, "lb"), 220.46226218, places=5)

if __name__ == "__main__":
    unittest.main()
