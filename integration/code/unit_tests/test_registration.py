import pytest

from integration.code import registration as reg


def setup_function():
    reg.clear_members()


def test_register_and_get_member():
    # Registers a member with a valid role and verifies retrieval by id
    member_id = reg.register_member("Alice", "driver")
    m = reg.get_member(member_id)
    assert m is not None
    assert m.name == "Alice"
    assert m.role == "driver"



def test_all_valid_roles_accepted():
    # Ensures every allowed role can be used when registering members
    roles = ["driver", "mechanic", "strategist", "gambler", "other"]
    reg.clear_members()
    ids = []
    for r in roles:
        mid = reg.register_member(f"X_{r}", r)
        ids.append(mid)
    members = reg.list_members()
    assert len(members) == len(roles)


def test_invalid_role_raises():
    # Passing a role not in the allowed list should raise ValueError
    reg.clear_members()
    with pytest.raises(ValueError):
        reg.register_member("Bob", "chef")


def test_register_invalid_name_raises():
    # Empty name should cause registration to raise ValueError
    with pytest.raises(ValueError):
        reg.register_member("", "driver")


def test_list_members():
    # Registers two members and verifies list_members returns both
    reg.register_member("A", "driver")
    reg.register_member("B", "mechanic")
    lst = reg.list_members()
    assert len(lst) == 2
    names = {m.name for m in lst}
    assert names == {"A", "B"}
