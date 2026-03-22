import io
import re
import unittest
from unittest.mock import patch

from integration.code import gambling, inventory, leaderboard, main, mission, race, registration, results


class IntegrationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_state()

    def tearDown(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        registration.clear_members()
        inventory.clear_inventory()
        race.clear_races()
        results.clear_results()
        mission.clear_missions()
        gambling.clear_bets()
        main._racers_stats.clear()
        main._gamblers_stats.clear()

    def _run_flow(self, flow, inputs):
        """Execute a main.py CLI flow with deterministic mocked input."""
        with patch("builtins.input", side_effect=inputs), patch("sys.stdout", new_callable=io.StringIO) as fake_out:
            flow()
            return fake_out.getvalue()

    def _add_entry_like_main(self, race_id: str, driver_id: str, car_id: str):
        """Execute add-entry via main._race_flow and infer outcome from state/output."""
        out = self._run_flow(main._race_flow, ["4", race_id, driver_id, car_id, "", "0"])
        race_data = race.get_race(race_id)
        if race_data is not None and any(e.driver.id == driver_id and e.car.id == car_id for e in race_data.get("entries", [])):
            return True, "entry added"
        if "member not found" in out:
            return False, "member not found"
        if "only members with role 'driver'" in out:
            return False, "member is not a driver"
        if "car not found" in out:
            return False, "car not found"
        if "retired cars cannot be entered" in out:
            return False, "car retired"
        return False, "entry not added"

    def _record_results_like_main(self, race_id: str, ordered_driver_ids: list[str]):
        """Execute result-recording via main._results_flow and infer outcome."""
        order_input = ",".join(ordered_driver_ids)
        before_cash = inventory.get_cash_balance()
        before_results = results.get_results(race_id)
        out = self._run_flow(main._results_flow, ["1", race_id, order_input, "0"])
        rows = results.get_results(race_id)
        if rows is not None and before_results is None:
            total_payout = sum(int(r.get("payout", 0) or 0) for r in rows)
            return {
                "ok": True,
                "rows": rows,
                "total_payout": total_payout,
                "new_balance": inventory.get_cash_balance(),
            }
        if "race not found" in out:
            return {"ok": False, "reason": "race not found"}
        if "race has no entries" in out:
            return {"ok": False, "reason": "no entries"}
        if "Results already recorded" in out:
            return {"ok": False, "reason": "results already recorded"}
        if "duplicate driver IDs" in out:
            return {"ok": False, "reason": "duplicate driver ids"}
        if "not in race entries" in out:
            return {"ok": False, "reason": "unknown driver id in order"}
        if "must include each race entry exactly once" in out:
            return {"ok": False, "reason": "finish order mismatch"}
        if "does not have enough cash" in out:
            return {"ok": False, "reason": "insufficient inventory cash"}
        return {
            "ok": False,
            "reason": "unknown",
            "previous_cash": before_cash,
        }

    def _place_bet_like_main(self, race_id: str, bettor_id: str, racer_id: str, amount: int):
        """Execute bet placement via main._gambling_flow and infer outcome."""
        out = self._run_flow(main._gambling_flow, ["1", race_id, bettor_id, racer_id, str(amount), "0"])
        bets = gambling.list_bets(race_id) if race.get_race(race_id) is not None else []
        bet = next((b for b in bets if b.get("bettor_id") == bettor_id and b.get("racer_id") == racer_id and b.get("amount") == amount), None)
        if bet is not None:
            return {"ok": True, "bet": bet}
        if "race not found" in out:
            return {"ok": False, "reason": "race not found"}
        if "racer is not an entry in this race" in out:
            return {"ok": False, "reason": "racer is not an entry in this race"}
        if "bettor not found" in out:
            return {"ok": False, "reason": "bettor not found"}
        if "does not have enough money" in out:
            return {"ok": False, "reason": "bettor does not have enough money"}
        if "only bettors with role 'gambler'" in out:
            return {"ok": False, "reason": "only bettors with role 'gambler' can place bets"}
        if "already exists for racer" in out:
            return {"ok": False, "reason": "a bet already exists for racer"}
        return {"ok": False, "reason": "unknown"}

    def _settle_bets_like_main(self, race_id: str):
        """Execute bet settlement via main._gambling_flow and infer outcome."""
        out = self._run_flow(main._gambling_flow, ["4", race_id, "0"])
        if "Bets settled." in out:
            rows = gambling.list_bets(race_id)
            pool = sum(int(r.get("amount", 0) or 0) for r in rows)
            race_results = results.get_results(race_id) or []
            winner_row = next((r for r in race_results if int(r.get("position", 0) or 0) == 1), None)
            winner_driver_id = str(winner_row.get("driver_id", "")).strip() if winner_row else ""
            winner_bet = next((r for r in rows if str(r.get("racer_id", "")).strip() == winner_driver_id), None)
            return {
                "ok": True,
                "settlement": {
                    "pool": pool,
                    "winner_bettor_id": winner_bet.get("bettor_id") if winner_bet else None,
                    "winner_payout": pool if winner_bet else 0,
                },
            }
        if "no bets found" in out:
            return {"ok": False, "reason": "no bets found for this race"}
        if "already settled" in out:
            return {"ok": False, "reason": "bets already settled"}
        if "results not found" in out:
            return {"ok": False, "reason": "race results not found"}
        return {"ok": False, "reason": "unknown"}

    def _create_mission_like_main(self, mission_type: str, title: str):
        """Create mission via main._mission_flow and return mission id."""
        out = self._run_flow(main._mission_flow, ["1", mission_type, title, "0"])
        match = re.search(r"ID:\s*([a-f0-9]+)", out)
        if match is None:
            return None, out
        return match.group(1), out

    def _assign_mission_like_main(self, mission_id: str, assignee_ids: list[str]):
        """Assign mission crew via main._mission_flow."""
        ids_input = ",".join(assignee_ids)
        out = self._run_flow(main._mission_flow, ["4", mission_id, ids_input, "0"])
        return out

    def _evaluate_mission_like_main(self, mission_id: str):
        """Evaluate readiness via main._mission_flow."""
        out = self._run_flow(main._mission_flow, ["5", mission_id, "0"])
        return out

    def _start_mission_like_main(self, mission_id: str):
        """Start mission via main._mission_flow."""
        out = self._run_flow(main._mission_flow, ["6", mission_id, "0"])
        return out

    def _complete_mission_like_main(self, mission_id: str, outcome: str = "success"):
        """Complete mission via main._mission_flow."""
        out = self._run_flow(main._mission_flow, ["7", mission_id, outcome, "0"])
        return out

    def test_register_driver_then_enter_race(self):
        """Scenario: register a driver and enter that driver into a race.

        Modules: registration + inventory + race
        Expected: entry is added and linked to the correct driver/car.
        """
        driver_id = registration.register_member("Alex", "driver")
        inventory.add_car("car-1", "R34", "good")
        race_id = race.create_race("City Sprint", prize_pool=100)

        ok, reason = self._add_entry_like_main(race_id, driver_id, "car-1")

        self.assertTrue(ok, msg=reason)
        race_data = race.get_race(race_id)
        self.assertIsNotNone(race_data)
        entries = race_data["entries"]
        self.assertEqual(1, len(entries))
        self.assertEqual(driver_id, entries[0].driver.id)
        self.assertEqual("car-1", entries[0].car.id)

    def test_cannot_enter_race_without_registered_driver(self):
        """Scenario: attempt race entry with an unknown driver id.

        Modules: registration + inventory + race
        Expected: integration validation blocks entry before race.add_entry.
        """
        inventory.add_car("car-2", "Evo", "good")
        race_id = race.create_race("Dockside Dash", prize_pool=80)

        ok, reason = self._add_entry_like_main(race_id, "missing-driver", "car-2")

        self.assertFalse(ok)
        self.assertEqual("member not found", reason)
        race_data = race.get_race(race_id)
        self.assertIsNotNone(race_data)
        self.assertEqual([], race_data["entries"])

    def test_cannot_enter_race_with_non_driver_role(self):
        """Scenario: registered member exists but role is not driver.

        Modules: registration + race
        Expected: integration layer blocks race entry for non-drivers.
        """
        strategist_id = registration.register_member("Ivy", "strategist")
        inventory.add_car("car-x", "S15", "good")
        race_id = race.create_race("Role Gate", prize_pool=40)

        ok, reason = self._add_entry_like_main(race_id, strategist_id, "car-x")

        self.assertFalse(ok)
        self.assertEqual("member is not a driver", reason)
        self.assertEqual([], race.get_race(race_id)["entries"])

    def test_cannot_enter_race_with_retired_car(self):
        """Scenario: valid driver but car is retired.

        Modules: registration + inventory + race
        Expected: integration layer blocks race entry.
        """
        driver_id = registration.register_member("Kai", "driver")
        inventory.add_car("car-ret", "Silvia", "retired")
        race_id = race.create_race("Old Timer", prize_pool=30)

        ok, reason = self._add_entry_like_main(race_id, driver_id, "car-ret")

        self.assertFalse(ok)
        self.assertEqual("car retired", reason)
        self.assertEqual([], race.get_race(race_id)["entries"])

    def test_complete_race_updates_results_driver_money_and_inventory_cash(self):
        """Scenario: complete a race and apply payouts.

        Modules: race + results + registration + inventory (+ main integration logic)
        Expected: results recorded, driver money credited, inventory cash reduced.
        """
        d1 = registration.register_member("D1", "driver")
        d2 = registration.register_member("D2", "driver")
        d3 = registration.register_member("D3", "driver")

        inventory.set_cash_balance(1000)
        inventory.add_car("c1", "R34", "good")
        inventory.add_car("c2", "Evo", "good")
        inventory.add_car("c3", "Supra", "good")

        race_id = race.create_race("Grand Prix", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "c1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "c2")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d3, "c3")[0])

        outcome = self._record_results_like_main(race_id, [d1, d2, d3])

        self.assertTrue(outcome["ok"], msg=outcome.get("reason"))
        self.assertEqual(100, outcome["total_payout"])
        self.assertEqual(900, outcome["new_balance"])

        rows = results.get_results(race_id)
        self.assertIsNotNone(rows)
        self.assertEqual(3, len(rows))
        self.assertEqual([1, 2, 3], [r["position"] for r in rows])

        self.assertEqual(50, registration.get_member(d1).money)
        self.assertEqual(30, registration.get_member(d2).money)
        self.assertEqual(20, registration.get_member(d3).money)

        race_data = race.get_race(race_id)
        self.assertEqual("completed", race_data["status"])

    def test_results_blocked_when_inventory_cash_is_insufficient(self):
        """Scenario: payout cannot be covered by inventory cash.

        Modules: race + results + inventory
        Expected: results are not recorded and balances do not change.
        """
        d1 = registration.register_member("Cashless1", "driver")
        d2 = registration.register_member("Cashless2", "driver")
        d3 = registration.register_member("Cashless3", "driver")

        inventory.set_cash_balance(20)
        inventory.add_car("cc1", "A", "good")
        inventory.add_car("cc2", "B", "good")
        inventory.add_car("cc3", "C", "good")

        race_id = race.create_race("Low Cash Cup", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "cc1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "cc2")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d3, "cc3")[0])

        outcome = self._record_results_like_main(race_id, [d1, d2, d3])

        self.assertFalse(outcome["ok"])
        self.assertEqual("insufficient inventory cash", outcome["reason"])
        self.assertIsNone(results.get_results(race_id))
        self.assertEqual(20, inventory.get_cash_balance())
        self.assertEqual(0, registration.get_member(d1).money)

    def test_results_cannot_be_recorded_twice_for_same_race(self):
        """Scenario: duplicate result recording for one race.

        Modules: race + results + inventory
        Expected: second attempt is blocked by integration check.
        """
        d1 = registration.register_member("One", "driver")
        d2 = registration.register_member("Two", "driver")
        inventory.set_cash_balance(200)
        inventory.add_car("o1", "M1", "good")
        inventory.add_car("o2", "M2", "good")
        race_id = race.create_race("Once", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "o1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "o2")[0])

        first = self._record_results_like_main(race_id, [d1, d2])
        second = self._record_results_like_main(race_id, [d1, d2])

        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual("results already recorded", second["reason"])

    def test_results_blocked_on_invalid_finish_order(self):
        """Scenario: finish order has duplicate ids.

        Modules: race + results
        Expected: integration validation rejects invalid order.
        """
        d1 = registration.register_member("Order1", "driver")
        d2 = registration.register_member("Order2", "driver")
        inventory.set_cash_balance(300)
        inventory.add_car("od1", "Model1", "good")
        inventory.add_car("od2", "Model2", "good")
        race_id = race.create_race("Order Test", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "od1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "od2")[0])

        outcome = self._record_results_like_main(race_id, [d1, d1])

        self.assertFalse(outcome["ok"])
        self.assertEqual("duplicate driver ids", outcome["reason"])
        self.assertIsNone(results.get_results(race_id))

    def test_assign_mission_and_validate_required_roles(self):
        """Scenario: assign mission and validate required roles before start.

        Modules: mission + registration (+ main helper role aggregation)
        Expected: mission blocked when required role missing; starts when role exists.
        """
        driver_id = registration.register_member("Mia", "driver")
        mission_id, _ = self._create_mission_like_main("repair", "Pitlane repair")
        self.assertIsNotNone(mission_id)

        out_assign_1 = self._assign_mission_like_main(mission_id, [driver_id])
        self.assertIn("Mission assigned", out_assign_1)

        blocked_out = self._evaluate_mission_like_main(mission_id)
        self.assertIn("Mission is BLOCKED", blocked_out)
        self.assertIn("mechanic", blocked_out)

        mechanic_id = registration.register_member("Noah", "mechanic")
        out_assign_2 = self._assign_mission_like_main(mission_id, [driver_id, mechanic_id])
        self.assertIn("Mission assigned", out_assign_2)

        ready_out = self._evaluate_mission_like_main(mission_id)
        start_out = self._start_mission_like_main(mission_id)

        self.assertIn("Mission is READY", ready_out)
        self.assertIn("Mission started successfully", start_out)
        self.assertEqual("in_progress", mission.get_mission(mission_id)["status"])

    def test_mission_without_assignees_uses_all_registered_roles(self):
        """Scenario: no mission assignees, readiness uses all registered members.

        Modules: mission + registration + main helper
        Expected: a planning mission can start when strategist exists globally.
        """
        registration.register_member("S", "strategist")
        mission_id, _ = self._create_mission_like_main("planning", "Strategy board")
        self.assertIsNotNone(mission_id)

        eval_out = self._evaluate_mission_like_main(mission_id)
        start_out = self._start_mission_like_main(mission_id)

        self.assertIn("Mission is READY", eval_out)
        self.assertIn("Mission started successfully", start_out)

    def test_assignee_display_names_handles_unknown_member(self):
        """Scenario: mission references an unknown assignee id.

        Modules: mission + registration + main helper
        Expected: helper renders unknown label safely.
        """
        mission_id, _ = self._create_mission_like_main("delivery", "Drop")
        self.assertIsNotNone(mission_id)
        out_assign = self._assign_mission_like_main(mission_id, ["missing-id"])
        self.assertIn("unknown member IDs", out_assign)
        mission.assign_mission(mission_id, ["missing-id"])
        labels = main._assignee_display_names(mission.get_mission(mission_id))

        self.assertEqual(1, len(labels))
        self.assertIn("unknown (missing-id)", labels[0])

    def test_gambling_and_leaderboard_updates_after_settlement(self):
        """Scenario: settle bets after race results and reflect leaderboard stats.

        Modules: registration + race + results + gambling + leaderboard (+ main stat updates)
        Expected: winner gets payout, gambler/racer leaderboards reflect integrated updates.
        """
        driver_id = registration.register_member("Driver", "driver")
        gambler_id = registration.register_member("Gambler", "gambler")

        gambler = registration.get_member(gambler_id)
        gambler.money = 300

        inventory.set_cash_balance(500)
        inventory.add_car("cg1", "RX7", "good")

        race_id = race.create_race("Night Run", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "cg1")[0])

        outcome = self._record_results_like_main(race_id, [driver_id])
        self.assertTrue(outcome["ok"], msg=outcome.get("reason"))

        placed = self._place_bet_like_main(race_id, gambler_id, driver_id, 50)
        self.assertTrue(placed["ok"], msg=placed.get("reason"))
        self.assertEqual(50, placed["bet"]["amount"])

        settled = self._settle_bets_like_main(race_id)
        self.assertTrue(settled["ok"], msg=settled.get("reason"))

        top_racer = leaderboard.top_racers(main._racers_stats, n=1, by="points")[0]
        top_gambler = leaderboard.top_gamblers(main._gamblers_stats, n=1, by="net_profit")[0]

        self.assertEqual(driver_id, top_racer["driver_id"])
        self.assertEqual(25, top_racer["points"])
        self.assertEqual(gambler_id, top_gambler["bettor_id"])
        self.assertEqual(0, top_gambler["net_profit"])

    def test_bet_fails_if_racer_not_in_race_entries(self):
        """Scenario: bettor targets a driver not entered in the race.

        Modules: race + registration + gambling
        Expected: integration checks reject placement.
        """
        entered_driver = registration.register_member("Entered", "driver")
        other_driver = registration.register_member("NotEntered", "driver")
        bettor_id = registration.register_member("Better", "gambler")
        registration.get_member(bettor_id).money = 200

        inventory.add_car("betcar", "GT", "good")
        race_id = race.create_race("Bet Gate", prize_pool=60)
        self.assertTrue(self._add_entry_like_main(race_id, entered_driver, "betcar")[0])

        placed = self._place_bet_like_main(race_id, bettor_id, other_driver, 50)

        self.assertFalse(placed["ok"])
        self.assertEqual("racer is not an entry in this race", placed["reason"])
        self.assertEqual([], gambling.list_bets(race_id))

    def test_only_gambler_role_can_place_bets(self):
        """Scenario: non-gambler attempts to place a bet.

        Modules: registration + race + gambling
        Expected: gambling module rejects role mismatch.
        """
        driver_id = registration.register_member("Racer", "driver")
        not_gambler_id = registration.register_member("Mechanic", "mechanic")
        registration.get_member(not_gambler_id).money = 100

        inventory.add_car("rolebet", "R8", "good")
        race_id = race.create_race("Role Bet", prize_pool=10)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "rolebet")[0])

        result = self._place_bet_like_main(race_id, not_gambler_id, driver_id, 20)

        self.assertFalse(result["ok"])
        self.assertIn("only bettors with role 'gambler'", result["reason"])

    def test_settle_bets_blocked_until_results_exist(self):
        """Scenario: settling is attempted before race results are recorded.

        Modules: race + gambling + results
        Expected: integration check blocks settlement.
        """
        driver_id = registration.register_member("D", "driver")
        bettor_id = registration.register_member("G", "gambler")
        registration.get_member(bettor_id).money = 100

        inventory.add_car("settlec1", "X", "good")
        race_id = race.create_race("Need Results", prize_pool=20)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "settlec1")[0])
        self.assertTrue(self._place_bet_like_main(race_id, bettor_id, driver_id, 30)["ok"])

        settled = self._settle_bets_like_main(race_id)

        self.assertFalse(settled["ok"])
        self.assertEqual("race results not found", settled["reason"])

    def test_settle_bets_cannot_run_twice(self):
        """Scenario: second settle attempt on already-settled race bets.

        Modules: gambling + results + registration
        Expected: second call is blocked.
        """
        driver_id = registration.register_member("S1", "driver")
        bettor_id = registration.register_member("S2", "gambler")
        registration.get_member(bettor_id).money = 100

        inventory.set_cash_balance(100)
        inventory.add_car("s2c", "Y", "good")
        race_id = race.create_race("Double Settle", prize_pool=50)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "s2c")[0])
        self.assertTrue(self._record_results_like_main(race_id, [driver_id])["ok"])
        self.assertTrue(self._place_bet_like_main(race_id, bettor_id, driver_id, 20)["ok"])

        first = self._settle_bets_like_main(race_id)
        second = self._settle_bets_like_main(race_id)

        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual("bets already settled", second["reason"])

    def test_leaderboard_views_return_expected_top_rows(self):
        """Scenario: leaderboard read helpers over integrated stats dictionaries.

        Modules: main stats updates + leaderboard
        Expected: top views and direct stat lookups are consistent.
        """
        d1 = registration.register_member("TopD1", "driver")
        d2 = registration.register_member("TopD2", "driver")
        g1 = registration.register_member("TopG1", "gambler")
        g2 = registration.register_member("TopG2", "gambler")

        registration.get_member(g1).money = 200
        registration.get_member(g2).money = 200

        inventory.set_cash_balance(500)
        inventory.add_car("t1", "A", "good")
        inventory.add_car("t2", "B", "good")
        race_id = race.create_race("TopBoard", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "t1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "t2")[0])
        self.assertTrue(self._record_results_like_main(race_id, [d1, d2])["ok"])
        self.assertTrue(self._place_bet_like_main(race_id, g1, d1, 100)["ok"])
        self.assertTrue(self._place_bet_like_main(race_id, g2, d2, 100)["ok"])
        self.assertTrue(self._settle_bets_like_main(race_id)["ok"])

        top_racer = leaderboard.top_racers(main._racers_stats, n=1, by="points")[0]
        top_gambler = leaderboard.top_gamblers(main._gamblers_stats, n=1, by="net_profit")[0]
        one_racer = leaderboard.get_racer_stats(main._racers_stats, d1)
        one_gambler = leaderboard.get_gambler_stats(main._gamblers_stats, g1)

        self.assertEqual(d1, top_racer["driver_id"])
        self.assertEqual(g1, top_gambler["bettor_id"])
        self.assertEqual(d1, one_racer["driver_id"])
        self.assertEqual(g1, one_gambler["bettor_id"])

    def test_change_role_integration_resets_skill_level(self):
        """Scenario: role change through integration rule resets skill to zero.

        Modules: registration + crew (+ main integration rule)
        Expected: member role changes and skill_level is reset.
        """
        member_id = registration.register_member("RoleSwap", "driver")
        member = registration.get_member(member_id)
        member.skill_level = 9
        out = self._run_flow(main._change_member_role_flow, [member_id, "mechanic"])

        self.assertIn("Role updated.", out)
        self.assertEqual("mechanic", member.role)
        self.assertEqual(0, member.skill_level)

    def test_place_bet_locks_stake_and_updates_gambler_stats(self):
        """Scenario: successful bet placement locks stake and updates stats.

        Modules: registration + race + gambling + main stats
        Expected: bettor money decreases and total_staked increases.
        """
        driver_id = registration.register_member("StakeD", "driver")
        bettor_id = registration.register_member("StakeG", "gambler")
        registration.get_member(bettor_id).money = 120

        inventory.add_car("stakecar", "Z", "good")
        race_id = race.create_race("Stake Race", prize_pool=0)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "stakecar")[0])

        placed = self._place_bet_like_main(race_id, bettor_id, driver_id, 70)

        self.assertTrue(placed["ok"], msg=placed.get("reason"))
        self.assertEqual(50, registration.get_member(bettor_id).money)
        stats = leaderboard.get_gambler_stats(main._gamblers_stats, bettor_id)
        self.assertEqual(1, stats["total_bets"])
        self.assertEqual(70, stats["total_staked"])
        self.assertEqual(-70, stats["net_profit"])

    def test_place_bet_fails_when_bettor_has_insufficient_money(self):
        """Scenario: bettor does not have enough money to lock stake.

        Modules: registration + race + gambling
        Expected: placement blocked, no bet created, stats unchanged.
        """
        driver_id = registration.register_member("FundD", "driver")
        bettor_id = registration.register_member("FundG", "gambler")
        registration.get_member(bettor_id).money = 10

        inventory.add_car("fundcar", "Q", "good")
        race_id = race.create_race("Funds", prize_pool=0)
        self.assertTrue(self._add_entry_like_main(race_id, driver_id, "fundcar")[0])

        placed = self._place_bet_like_main(race_id, bettor_id, driver_id, 50)

        self.assertFalse(placed["ok"])
        self.assertEqual("bettor does not have enough money", placed["reason"])
        self.assertEqual([], gambling.list_bets(race_id))
        self.assertIsNone(leaderboard.get_gambler_stats(main._gamblers_stats, bettor_id))

    def test_results_blocked_on_finish_order_with_unknown_driver_id(self):
        """Scenario: finish order contains driver not entered in race.

        Modules: race + results
        Expected: result recording is rejected before persistence.
        """
        d1 = registration.register_member("KnownA", "driver")
        d2 = registration.register_member("KnownB", "driver")
        inventory.set_cash_balance(200)
        inventory.add_car("uk1", "M", "good")
        inventory.add_car("uk2", "N", "good")
        race_id = race.create_race("Unknown ID", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "uk1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "uk2")[0])

        outcome = self._record_results_like_main(race_id, [d1, "not-in-race"])

        self.assertFalse(outcome["ok"])
        self.assertEqual("unknown driver id in order", outcome["reason"])
        self.assertIsNone(results.get_results(race_id))

    def test_complete_mission_sets_status_and_outcome(self):
        """Scenario: mission goes from ready to started to completed.

        Modules: mission + registration + main helper
        Expected: final status is completed and outcome is stored.
        """
        mechanic_id = registration.register_member("Fixer", "mechanic")
        mission_id, _ = self._create_mission_like_main("repair", "Garage")
        self.assertIsNotNone(mission_id)
        self.assertIn("Mission assigned", self._assign_mission_like_main(mission_id, [mechanic_id]))
        self.assertIn("Mission started successfully", self._start_mission_like_main(mission_id))
        self.assertIn("Mission completed with outcome: success", self._complete_mission_like_main(mission_id, "success"))

        done = mission.get_mission(mission_id)
        self.assertEqual("completed", done["status"])
        self.assertEqual("success", done["outcome"])

    def test_settlement_pool_goes_to_single_winner_and_status_changes(self):
        """Scenario: two bettors, one winning racer, full pool to winner.

        Modules: race + results + gambling + registration
        Expected: winner receives full pool and all bets become settled.
        """
        d1 = registration.register_member("WinD", "driver")
        d2 = registration.register_member("LoseD", "driver")
        g1 = registration.register_member("WinG", "gambler")
        g2 = registration.register_member("LoseG", "gambler")
        registration.get_member(g1).money = 200
        registration.get_member(g2).money = 200

        inventory.set_cash_balance(200)
        inventory.add_car("pool1", "A", "good")
        inventory.add_car("pool2", "B", "good")
        race_id = race.create_race("Pool", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "pool1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "pool2")[0])
        self.assertTrue(self._record_results_like_main(race_id, [d1, d2])["ok"])

        self.assertTrue(self._place_bet_like_main(race_id, g1, d1, 50)["ok"])
        self.assertTrue(self._place_bet_like_main(race_id, g2, d2, 50)["ok"])

        settled = self._settle_bets_like_main(race_id)

        self.assertTrue(settled["ok"])
        settlement = settled["settlement"]
        self.assertEqual(100, settlement["pool"])
        self.assertEqual(g1, settlement["winner_bettor_id"])
        self.assertEqual(100, settlement["winner_payout"])
        statuses = {b["status"] for b in gambling.list_bets(race_id)}
        self.assertEqual({"settled"}, statuses)

    def test_leaderboard_sort_by_wins_for_racers(self):
        """Scenario: leaderboard ranks racers by wins.

        Modules: main stats updates + leaderboard
        Expected: racer with more wins appears first.
        """
        d1 = registration.register_member("Wins1", "driver")
        d2 = registration.register_member("Wins2", "driver")

        inventory.set_cash_balance(300)
        inventory.add_car("w1", "X", "good")
        inventory.add_car("w2", "Y", "good")

        race1 = race.create_race("Wins R1", prize_pool=50)
        self.assertTrue(self._add_entry_like_main(race1, d1, "w1")[0])
        self.assertTrue(self._add_entry_like_main(race1, d2, "w2")[0])
        self.assertTrue(self._record_results_like_main(race1, [d1, d2])["ok"])

        race2 = race.create_race("Wins R2", prize_pool=50)
        self.assertTrue(self._add_entry_like_main(race2, d1, "w1")[0])
        self.assertTrue(self._add_entry_like_main(race2, d2, "w2")[0])
        self.assertTrue(self._record_results_like_main(race2, [d1, d2])["ok"])

        top = leaderboard.top_racers(main._racers_stats, n=1, by="wins")[0]
        self.assertEqual(d1, top["driver_id"])
        self.assertEqual(2, top["wins"])

    def test_leaderboard_sort_by_total_payouts_for_gamblers(self):
        """Scenario: leaderboard ranks gamblers by total payouts.

        Modules: main stats updates + leaderboard
        Expected: gambler with larger payout appears first.
        """
        d1 = registration.register_member("PayDriver1", "driver")
        d2 = registration.register_member("PayDriver2", "driver")
        g1 = registration.register_member("Pay1", "gambler")
        g2 = registration.register_member("Pay2", "gambler")
        registration.get_member(g1).money = 300
        registration.get_member(g2).money = 300

        inventory.set_cash_balance(300)
        inventory.add_car("p1", "P1", "good")
        inventory.add_car("p2", "P2", "good")
        race_id = race.create_race("PayoutSort", prize_pool=100)
        self.assertTrue(self._add_entry_like_main(race_id, d1, "p1")[0])
        self.assertTrue(self._add_entry_like_main(race_id, d2, "p2")[0])
        self.assertTrue(self._record_results_like_main(race_id, [d1, d2])["ok"])

        self.assertTrue(self._place_bet_like_main(race_id, g1, d1, 150)["ok"])
        self.assertTrue(self._place_bet_like_main(race_id, g2, d2, 50)["ok"])
        self.assertTrue(self._settle_bets_like_main(race_id)["ok"])

        top = leaderboard.top_gamblers(main._gamblers_stats, n=1, by="total_payouts")[0]
        self.assertEqual(g1, top["bettor_id"])
        self.assertEqual(200, top["total_payouts"])


if __name__ == "__main__":
    unittest.main()
