from typing import Callable, Dict

import sys
from pathlib import Path

try:
    from integration.code import crew, gambling, inventory, mission, race, registration, results
except ImportError:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from integration.code import crew, gambling, inventory, mission, race, registration, results


def _prompt_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Value cannot be empty.")


def _register_member_flow() -> None:
    # Collect inputs but defer validation to the registration module.
    name = input("Enter member name: ").strip()
    role = input("Enter role (driver/mechanic/strategist/gambler/other): ").strip()
    try:
        member_id = registration.register_member(name=name, role=role)
    except ValueError as exc:
        # Show error coming from the module (single-source validation).
        print(f"Registration failed: {exc}")
        return

    member = registration.get_member(member_id)
    print("Registered successfully.")
    if member:
        print(f"ID: {member.id} | Name: {member.name} | Role: {member.role} | Money: {member.money}")


def _list_members_flow() -> None:
    members = registration.list_members()
    if not members:
        print("No registered members yet.")
        return

    print("Registered members:")
    for idx, m in enumerate(members, start=1):
        print(f"{idx}. ID: {m.id} | Name: {m.name} | Role: {m.role} | Money: {m.money}")


def _get_member_flow() -> None:
    member_id = _prompt_non_empty("Enter member ID: ")
    member = registration.get_member(member_id)
    if member is None:
        print("Member not found.")
        return
    print(f"Name: {member.name} | Role: {member.role} | Money: {member.money}")


def _clear_members_flow() -> None:
    confirm = input("Clear all members? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    registration.clear_members()
    print("All members cleared.")


def _change_member_role_flow() -> None:
    member_id = input("Enter member ID: ").strip()
    new_role = input("Enter new role (driver/mechanic/strategist/gambler/other): ").strip()

    # Interaction rule: role changes can only be applied to registered members.
    member = registration.get_member(member_id)
    if member is None:
        print("Member not found. Register member first.")
        return

    try:
        crew.change_role(member, new_role)
    except ValueError as exc:
        print(f"Role update failed: {exc}")
        return

    # Integration rule in CLI: role changes reset role-linked skill level.
    member.skill_level = 0

    print(f"Role updated. Name: {member.name} | Role: {member.role}")


def _change_member_skill_flow() -> None:
    member_id = input("Enter member ID: ").strip()
    raw_level = input("Enter level (0-10): ").strip()

    member = registration.get_member(member_id)
    if member is None:
        print("Member not found. Register member first.")
        return

    try:
        level = int(raw_level)
    except ValueError:
        print("Skill update failed: level must be an integer 0..10")
        return

    try:
        crew.change_rating(member, level)
    except ValueError as exc:
        print(f"Skill update failed: {exc}")
        return

    print(f"Skill updated. Name: {member.name} | Role: {member.role} | Level: {crew.get_skill(member)}")


def _view_member_skill_flow() -> None:
    member_id = input("Enter member ID: ").strip()

    member = registration.get_member(member_id)
    if member is None:
        print("Member not found.")
        return

    print(f"Name: {member.name} | Role: {member.role} | Level: {crew.get_skill(member)}")


def _inventory_flow() -> None:
    while True:
        print("\nInventory Management")
        print("1. Set cash balance")
        print("2. View cash balance")
        print("3. Adjust cash (delta)")
        print("4. Add car")
        print("5. List cars")
        print("6. Update car condition")
        print("7. Add spare part")
        print("8. Use spare part")
        print("9. List spare parts")
        print("10. Add tool")
        print("11. Use tool")
        print("12. List tools")
        print("13. Clear inventory")
        print("0. Back")

        choice = input("Choose inventory option: ").strip()
        if choice == "0":
            return

        try:
            if choice == "1":
                amount = int(input("Enter new cash balance: ").strip())
                inventory.set_cash_balance(amount)
                print(f"Cash balance set to {inventory.get_cash_balance()}")

            elif choice == "2":
                print(f"Cash balance: {inventory.get_cash_balance()}")

            elif choice == "3":
                delta = int(input("Enter cash delta (can be negative): ").strip())
                new_balance = inventory.adjust_cash(delta)
                print(f"Cash balance updated: {new_balance}")

            elif choice == "4":
                car_id = input("Enter car id: ").strip()
                model = input("Enter model: ").strip()
                condition = input("Enter condition (good/damaged/repairing/retired): ").strip() or "good"
                inventory.add_car(car_id=car_id, model=model, condition=condition)
                print("Car added.")

            elif choice == "5":
                cars = inventory.list_cars()
                if not cars:
                    print("No cars in inventory.")
                else:
                    print("Cars:")
                    for idx, car in enumerate(cars, start=1):
                        print(f"{idx}. ID: {car.id} | Model: {car.model} | Condition: {car.condition}")

            elif choice == "6":
                car_id = input("Enter car id: ").strip()
                condition = input("Enter new condition (good/damaged/repairing/retired): ").strip()
                inventory.update_car_condition(car_id, condition)
                print("Car condition updated.")

            elif choice == "7":
                part_name = input("Enter spare part name: ").strip()
                qty = int(input("Enter quantity: ").strip())
                inventory.add_spare_part(part_name, qty)
                print("Spare part added.")

            elif choice == "8":
                part_name = input("Enter spare part name: ").strip()
                qty = int(input("Enter quantity to use: ").strip())
                inventory.use_spare_part(part_name, qty)
                print("Spare part usage recorded.")

            elif choice == "9":
                parts = inventory.list_spare_parts()
                if not parts:
                    print("No spare parts in inventory.")
                else:
                    print("Spare parts:")
                    for name, qty in parts.items():
                        print(f"- {name}: {qty}")

            elif choice == "10":
                tool_name = input("Enter tool name: ").strip()
                qty = int(input("Enter quantity: ").strip())
                inventory.add_tool(tool_name, qty)
                print("Tool added.")

            elif choice == "11":
                tool_name = input("Enter tool name: ").strip()
                qty = int(input("Enter quantity to use: ").strip())
                inventory.use_tool(tool_name, qty)
                print("Tool usage recorded.")

            elif choice == "12":
                tools = inventory.list_tools()
                if not tools:
                    print("No tools in inventory.")
                else:
                    print("Tools:")
                    for name, qty in tools.items():
                        print(f"- {name}: {qty}")

            elif choice == "13":
                confirm = input("Clear all inventory data? (y/N): ").strip().lower()
                if confirm == "y":
                    inventory.clear_inventory()
                    print("Inventory cleared.")
                else:
                    print("Cancelled.")

            else:
                print("Invalid inventory option.")

        except ValueError as exc:
            print(f"Inventory action failed: {exc}")
        except KeyError as exc:
            print(f"Inventory action failed: {exc}")


def _race_flow() -> None:
    while True:
        print("\nRace Management")
        print("1. Create race")
        print("2. List races")
        print("3. View race details")
        print("4. Add race entry")
        print("5. Remove race entry")
        print("6. Clear all races")
        print("0. Back")

        choice = input("Choose race option: ").strip()
        if choice == "0":
            return

        try:
            if choice == "1":
                name = input("Enter race name: ").strip()
                prize_pool = int(input("Enter prize pool (>=0): ").strip())
                race_id = race.create_race(name=name, prize_pool=prize_pool)
                print(f"Race created. ID: {race_id}")

            elif choice == "2":
                races = race.list_races()
                if not races:
                    print("No races created yet.")
                else:
                    print("Races:")
                    for idx, r in enumerate(races, start=1):
                        print(
                            f"{idx}. ID: {r['id']} | Name: {r['name']} | "
                            f"Entries: {len(r['entries'])} | Prize: {r['prize_pool']}"
                        )

            elif choice == "3":
                race_id = input("Enter race ID: ").strip()
                r = race.get_race(race_id)
                if r is None:
                    print("Race not found.")
                else:
                    print(f"Race: {r['name']} | Status: {r['status']} | Prize: {r['prize_pool']}")
                    if not r["entries"]:
                        print("No entries yet.")
                    else:
                        print("Entries:")
                        for i, entry in enumerate(r["entries"], start=1):
                            print(
                                f"{i}. Driver: {entry.driver.name} ({entry.driver.id}) | "
                                f"Car: {entry.car.model} ({entry.car.id})"
                            )

            elif choice == "4":
                race_id = input("Enter race ID: ").strip()
                driver_id = input("Enter driver member ID: ").strip()
                car_id = input("Enter car ID: ").strip()
                note = input("Optional note: ").strip() or None

                # Interaction rules at integration layer:
                # - driver must be registered and role must be 'driver'
                # - car must exist in inventory
                member = registration.get_member(driver_id)
                if member is None:
                    print("Entry failed: member not found. Register member first.")
                    continue
                if member.role != "driver":
                    print("Entry failed: only members with role 'driver' can enter races.")
                    continue

                car = inventory.get_car(car_id)
                if car is None:
                    print("Entry failed: car not found in inventory.")
                    continue
                if car.condition == "retired":
                    print("Entry failed: retired cars cannot be entered.")
                    continue

                race.add_entry(race_id=race_id, driver=member, car=car, note=note)
                print("Race entry added.")

            elif choice == "5":
                race_id = input("Enter race ID: ").strip()
                driver_id = input("Enter driver member ID to remove: ").strip()
                race.remove_entry(race_id, driver_id)
                print("Race entry removed.")

            elif choice == "6":
                confirm = input("Clear all races? (y/N): ").strip().lower()
                if confirm == "y":
                    race.clear_races()
                    print("All races cleared.")
                else:
                    print("Cancelled.")

            else:
                print("Invalid race option.")

        except ValueError as exc:
            print(f"Race action failed: {exc}")
        except KeyError as exc:
            print(f"Race action failed: {exc}")


def _results_flow() -> None:
    while True:
        print("\nResults Management")
        print("1. Record race results")
        print("2. View race results")
        print("3. List all recorded results")
        print("4. Clear all results")
        print("0. Back")

        choice = input("Choose results option: ").strip()
        if choice == "0":
            return

        try:
            if choice == "1":
                race_id = input("Enter race ID: ").strip()
                race_data = race.get_race(race_id)
                if race_data is None:
                    print("Results failed: race not found.")
                    continue

                entries = race_data.get("entries", [])
                if not entries:
                    print("Results failed: race has no entries.")
                    continue

                # Prevent duplicate payout application for the same race.
                if results.get_results(race_id) is not None:
                    print("Results already recorded for this race.")
                    continue

                print("Current race entries:")
                for idx, entry in enumerate(entries, start=1):
                    print(f"{idx}. Driver: {entry.driver.name} ({entry.driver.id}) | Car: {entry.car.id}")

                order_input = input("Enter finish order as comma-separated driver IDs: ").strip()
                ordered_driver_ids = [x.strip() for x in order_input.split(",") if x.strip()]

                if len(ordered_driver_ids) != len(entries):
                    print("Results failed: finish order must include each race entry exactly once.")
                    continue

                id_to_entry = {entry.driver.id: entry for entry in entries}
                if len(set(ordered_driver_ids)) != len(ordered_driver_ids):
                    print("Results failed: duplicate driver IDs in finish order.")
                    continue
                if any(driver_id not in id_to_entry for driver_id in ordered_driver_ids):
                    print("Results failed: finish order contains driver IDs not in race entries.")
                    continue

                ordered_entries = [id_to_entry[driver_id] for driver_id in ordered_driver_ids]
                prize_pool = int(race_data.get("prize_pool", 0))

                # Compute payouts first and ensure inventory can cover them.
                ordered_driver_ids = [e.driver.id for e in ordered_entries]
                payouts_map = results.calculate_payouts(ordered_driver_ids, prize_pool)
                total_payout = sum(int(v or 0) for v in payouts_map.values())

                if inventory.get_cash_balance() < total_payout:
                    print("Results failed: inventory does not have enough cash to pay prizes.")
                    continue

                # Record results and credit each driver's personal balance.
                rows = results.record_results(race_id=race_id, ordered_entries=ordered_entries, prize_pool=prize_pool)
                for row in rows:
                    member = registration.get_member(str(row.get("driver_id", "")))
                    if member is not None:
                        member.money += int(row.get("payout", 0) or 0)

                # Business rule: deduct prize pool from inventory cash.
                new_balance = inventory.adjust_cash(-total_payout)

                race_data["status"] = "completed"
                print("Results recorded.")
                for row in rows:
                    print(
                        f"Pos {row['position']} | Driver: {row['driver_id']} | "
                        f"Car: {row['car_id']} | Payout: {row['payout']}"
                    )
                print(f"Total payout applied to inventory cash: {total_payout}")
                print(f"New cash balance: {new_balance}")

            elif choice == "2":
                race_id = input("Enter race ID: ").strip()
                race_results = results.get_results(race_id)
                if race_results is None:
                    print("No results recorded for this race.")
                    continue
                print(f"Results for race {race_id}:")
                for row in race_results:
                    print(
                        f"Pos {row['position']} | Driver: {row['driver_id']} | "
                        f"Car: {row['car_id']} | Payout: {row['payout']}"
                    )

            elif choice == "3":
                all_results = results.list_results()
                if not all_results:
                    print("No recorded results yet.")
                    continue
                print("Recorded results:")
                for rid, rows in all_results.items():
                    print(f"Race {rid}: {len(rows)} entries")

            elif choice == "4":
                confirm = input("Clear all results? (y/N): ").strip().lower()
                if confirm == "y":
                    results.clear_results()
                    print("All results cleared.")
                else:
                    print("Cancelled.")

            else:
                print("Invalid results option.")

        except ValueError as exc:
            print(f"Results action failed: {exc}")
        except KeyError as exc:
            print(f"Results action failed: {exc}")


def _available_roles_for_mission(m: Dict) -> list[str]:
    """Return available roles for mission checks.

    If assignees are provided, use their roles only. Otherwise use all registered roles.
    """
    assignee_ids = m.get("assignee_ids", [])
    if assignee_ids:
        roles = []
        for aid in assignee_ids:
            member = registration.get_member(str(aid))
            if member is not None:
                roles.append(member.role)
        return roles
    return [member.role for member in registration.list_members()]


def _assignee_display_names(m: Dict) -> list[str]:
    assignee_ids = m.get("assignee_ids", [])
    labels: list[str] = []
    for aid in assignee_ids:
        member = registration.get_member(str(aid))
        if member is None:
            labels.append(f"unknown ({aid})")
        else:
            labels.append(f"{member.name} ({member.id})")
    return labels


def _mission_flow() -> None:
    while True:
        print("\nMission Planning")
        print("1. Create mission")
        print("2. List missions")
        print("3. View mission details")
        print("4. Assign mission crew")
        print("5. Evaluate mission readiness")
        print("6. Start mission")
        print("7. Complete mission")
        print("8. Clear all missions")
        print("0. Back")

        choice = input("Choose mission option: ").strip()
        if choice == "0":
            return

        try:
            if choice == "1":
                mission_type = input("Enter mission type (delivery/planning/repair/rescue): ").strip()
                title = input("Enter mission title: ").strip()
                mission_id = mission.create_mission(mission_type=mission_type, title=title)
                print(f"Mission created. ID: {mission_id}")

            elif choice == "2":
                missions = mission.list_missions()
                if not missions:
                    print("No missions planned yet.")
                else:
                    print("Missions:")
                    for idx, m in enumerate(missions, start=1):
                        assignees = _assignee_display_names(m)
                        print(
                            f"{idx}. ID: {m['id']} | Type: {m['type']} | Title: {m['title']} | "
                            f"Status: {m['status']} | Required: {', '.join(m['required_roles']) or 'none'} | "
                            f"Assignees: {', '.join(assignees) or 'none'}"
                        )

            elif choice == "3":
                mission_id = input("Enter mission ID: ").strip()
                m = mission.get_mission(mission_id)
                if m is None:
                    print("Mission not found.")
                else:
                    assignees = _assignee_display_names(m)
                    print(
                        f"Mission: {m['title']} | Type: {m['type']} | Status: {m['status']} | "
                        f"Required roles: {', '.join(m['required_roles']) or 'none'}"
                    )
                    print(f"Assignees: {', '.join(assignees) or 'none'}")

            elif choice == "4":
                mission_id = input("Enter mission ID: ").strip()
                ids_input = input("Enter assignee member IDs (comma-separated): ").strip()
                assignee_ids = [x.strip() for x in ids_input.split(",") if x.strip()]

                # Integration check: assignees must exist as registered members.
                missing = [aid for aid in assignee_ids if registration.get_member(aid) is None]
                if missing:
                    print(f"Assign failed: unknown member IDs: {', '.join(missing)}")
                    continue

                updated = mission.assign_mission(mission_id, assignee_ids)
                assignees = _assignee_display_names(updated)
                print(f"Mission assigned. Assignees: {', '.join(assignees) or 'none'}")

            elif choice == "5":
                mission_id = input("Enter mission ID: ").strip()
                m = mission.get_mission(mission_id)
                if m is None:
                    print("Mission not found.")
                    continue
                available_roles = _available_roles_for_mission(m)
                check = mission.evaluate_mission_readiness(mission_id, available_roles)
                if check["can_start"]:
                    print("Mission is READY.")
                else:
                    print(f"Mission is BLOCKED: {check['reason']}")

            elif choice == "6":
                mission_id = input("Enter mission ID: ").strip()
                m = mission.get_mission(mission_id)
                if m is None:
                    print("Mission not found.")
                    continue
                available_roles = _available_roles_for_mission(m)
                result = mission.start_mission(mission_id, available_roles)
                if not result.get("started", False):
                    print(f"Mission start blocked: {result.get('reason', 'unknown reason')}")
                else:
                    print("Mission started successfully.")

            elif choice == "7":
                mission_id = input("Enter mission ID: ").strip()
                outcome = input("Enter mission outcome: ").strip() or "success"
                done = mission.complete_mission(mission_id, outcome)
                print(f"Mission completed with outcome: {done.get('outcome', outcome)}")

            elif choice == "8":
                confirm = input("Clear all missions? (y/N): ").strip().lower()
                if confirm == "y":
                    mission.clear_missions()
                    print("All missions cleared.")
                else:
                    print("Cancelled.")

            else:
                print("Invalid mission option.")

        except ValueError as exc:
            print(f"Mission action failed: {exc}")
        except KeyError as exc:
            print(f"Mission action failed: {exc}")


def _gambling_flow() -> None:
    while True:
        print("\nGambling")
        print("1. Place bet")
        print("2. List bets for race")
        print("3. View pool for race")
        print("4. Settle bets")
        print("5. Clear bets for race")
        print("6. Clear all bets")
        print("0. Back")

        choice = input("Choose gambling option: ").strip()
        if choice == "0":
            return

        try:
            if choice == "1":
                race_id = input("Enter race ID: ").strip()
                bettor_id = input("Enter bettor member ID: ").strip()
                racer_id = input("Enter racer (driver) member ID: ").strip()
                amount = int(input("Enter bet amount: ").strip())

                race_data = race.get_race(race_id)
                if race_data is None:
                    print("Bet failed: race not found.")
                    continue

                # Ensure racer is actually entered in that race.
                entry_driver_ids = {e.driver.id for e in race_data.get("entries", [])}
                if racer_id not in entry_driver_ids:
                    print("Bet failed: racer is not an entry in this race.")
                    continue

                bettor = registration.get_member(bettor_id)
                if bettor is None:
                    print("Bet failed: bettor not found.")
                    continue

                # Integration-level wallet handling: lock stake at placement time.
                if bettor.money < amount:
                    print("Bet failed: bettor does not have enough money.")
                    continue

                bet = gambling.place_bet(race_id=race_id, bettor=bettor, racer_id=racer_id, amount=amount)
                bettor.money -= amount
                print(
                    f"Bet placed. Bettor: {bet['bettor_name']} | Racer: {bet['racer_id']} | "
                    f"Amount: {bet['amount']}"
                )

            elif choice == "2":
                race_id = input("Enter race ID: ").strip()
                bets = gambling.list_bets(race_id)
                if not bets:
                    print("No bets for this race.")
                else:
                    print("Bets:")
                    for idx, b in enumerate(bets, start=1):
                        print(
                            f"{idx}. Bettor: {b['bettor_name']} ({b['bettor_id']}) | "
                            f"Racer: {b['racer_id']} | Amount: {b['amount']} | Status: {b['status']}"
                        )

            elif choice == "3":
                race_id = input("Enter race ID: ").strip()
                print(f"Total pool: {gambling.total_pool(race_id)}")

            elif choice == "4":
                race_id = input("Enter race ID: ").strip()
                bets = gambling.list_bets(race_id)
                if not bets:
                    print("Settle failed: no bets found for this race.")
                    continue
                if any(b.get("status") == "settled" for b in bets):
                    print("Settle failed: bets for this race are already settled.")
                    continue

                race_results = results.get_results(race_id)
                if not race_results:
                    print("Settle failed: race results not found. Record results before settling bets.")
                    continue

                # Winner is derived from recorded race results (position 1).
                winner_row = next((r for r in race_results if int(r.get("position", 0) or 0) == 1), None)
                if winner_row is None:
                    print("Settle failed: race results are invalid (no first-place driver).")
                    continue
                winning_racer_id = str(winner_row.get("driver_id", "")).strip()
                if not winning_racer_id:
                    print("Settle failed: race results are invalid (missing winner driver id).")
                    continue

                settlement = gambling.settle_bets(race_id, winning_racer_id)
                for row in settlement.get("results", []):
                    payout = int(row.get("payout", 0) or 0)
                    if payout <= 0:
                        continue
                    winner = registration.get_member(str(row.get("bettor_id", "")))
                    if winner is not None:
                        winner.money += payout

                print(
                    f"Bets settled. Pool: {settlement['pool']} | "
                    f"Winner bettor: {settlement['winner_bettor_id']} | "
                    f"Payout: {settlement['winner_payout']}"
                )

            elif choice == "5":
                race_id = input("Enter race ID: ").strip()
                gambling.clear_bets(race_id)
                print("Bets cleared for race.")

            elif choice == "6":
                confirm = input("Clear all bets? (y/N): ").strip().lower()
                if confirm == "y":
                    gambling.clear_bets()
                    print("All bets cleared.")
                else:
                    print("Cancelled.")

            else:
                print("Invalid gambling option.")

        except ValueError as exc:
            print(f"Gambling action failed: {exc}")
        except KeyError as exc:
            print(f"Gambling action failed: {exc}")


def run() -> None:
    actions: Dict[str, Callable[[], None]] = {
        "1": _register_member_flow,
        "2": _list_members_flow,
        "3": _get_member_flow,
        "4": _clear_members_flow,
        "5": _change_member_role_flow,
        "6": _change_member_skill_flow,
        "7": _view_member_skill_flow,
        "8": _inventory_flow,
        "9": _race_flow,
        "10": _results_flow,
        "11": _mission_flow,
        "12": _gambling_flow,
    }

    while True:
        print("\nStreetRace Manager - Integration Phase 7 (Registration + Crew + Inventory + Race + Results + Mission + Gambling)")
        print("1. Register member")
        print("2. List members")
        print("3. Get member by ID")
        print("4. Clear all members")
        print("5. Change member role")
        print("6. Change member skill level")
        print("7. View member skill level")
        print("8. Inventory management")
        print("9. Race management")
        print("10. Results management")
        print("11. Mission planning")
        print("12. Gambling")
        print("0. Exit")

        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye.")
            return

        action = actions.get(choice)
        if action is None:
            print("Invalid option.")
            continue
        action()


if __name__ == "__main__":
    run()
