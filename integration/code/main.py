from typing import Callable, Dict

import sys
from pathlib import Path

try:
    from integration.code import crew, inventory, race, registration
except ImportError:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from integration.code import crew, inventory, race, registration


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
        print(f"ID: {member.id} | Name: {member.name} | Role: {member.role}")


def _list_members_flow() -> None:
    members = registration.list_members()
    if not members:
        print("No registered members yet.")
        return

    print("Registered members:")
    for idx, m in enumerate(members, start=1):
        print(f"{idx}. ID: {m.id} | Name: {m.name} | Role: {m.role}")


def _get_member_flow() -> None:
    member_id = _prompt_non_empty("Enter member ID: ")
    member = registration.get_member(member_id)
    if member is None:
        print("Member not found.")
        return
    print(f"Name: {member.name} | Role: {member.role}")


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
    }

    while True:
        print("\nStreetRace Manager - Integration Phase 4 (Registration + Crew + Inventory + Race)")
        print("1. Register member")
        print("2. List members")
        print("3. Get member by ID")
        print("4. Clear all members")
        print("5. Change member role")
        print("6. Change member skill level")
        print("7. View member skill level")
        print("8. Inventory management")
        print("9. Race management")
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
