import unittest

from logic.optimizer import EnergyOptimizer, EnergyState


class EnergyOptimizerTests(unittest.TestCase):
    def setUp(self):
        # Each test gets a fresh optimizer instance.
        self.optimizer = EnergyOptimizer()

    def test_solar_serves_load_and_charges_battery(self):
        # Solar first serves demand; remaining solar charges the battery with efficiency loss.
        usage, battery = self.optimizer.optimize(
            EnergyState(
                solar=100,
                demand=40,
                battery_level=10,
                battery_capacity=100,
                grid_available=True,
                grid_price=6,
                peak_hour=False,
            )
        )

        self.assertEqual(usage.solar_used, 40)
        self.assertAlmostEqual(usage.battery_charged, 54)
        self.assertEqual(usage.grid_used, 0)
        self.assertAlmostEqual(battery, 64)

    def test_peak_hour_prefers_battery_before_grid(self):
        # During expensive peak hours, battery discharges down to reserve before grid use.
        usage, battery = self.optimizer.optimize(
            EnergyState(
                solar=0,
                demand=90,
                battery_level=100,
                battery_capacity=100,
                grid_available=True,
                grid_price=12,
                peak_hour=True,
            )
        )

        self.assertAlmostEqual(usage.battery_used, 72)
        self.assertAlmostEqual(usage.grid_used, 18)
        self.assertAlmostEqual(battery, 20)

    def test_island_mode_reports_unmet_demand(self):
        # With grid unavailable and battery at reserve, unmet demand is reported.
        usage, battery = self.optimizer.optimize(
            EnergyState(
                solar=10,
                demand=100,
                battery_level=20,
                battery_capacity=100,
                grid_available=False,
                grid_price=6,
                peak_hour=False,
            )
        )

        self.assertEqual(usage.grid_used, 0)
        self.assertGreater(usage.unmet_demand, 0)
        self.assertEqual(battery, 20)


if __name__ == "__main__":
    unittest.main()
