from typing import Callable, Dict

import sys
from pathlib import Path

try:
    from integration.code import registration
except ImportError:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from integration.code import registration


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
    print(f"ID: {member.id} | Name: {member.name} | Role: {member.role}")


def _clear_members_flow() -> None:
    confirm = input("Clear all members? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return
    registration.clear_members()
    print("All members cleared.")


def run() -> None:
    actions: Dict[str, Callable[[], None]] = {
        "1": _register_member_flow,
        "2": _list_members_flow,
        "3": _get_member_flow,
        "4": _clear_members_flow,
    }

    while True:
        print("\nStreetRace Manager - Integration Phase 1 (Registration)")
        print("1. Register member")
        print("2. List members")
        print("3. Get member by ID")
        print("4. Clear all members")
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
