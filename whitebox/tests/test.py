"""Comprehensive white-box tests for MoneyPoly control-flow paths."""

import conf  # noqa: F401  # apply path bootstrap before package imports

import pytest

import moneypoly.ui as ui
from moneypoly.bank import Bank
from moneypoly.board import Board
from moneypoly.cards import CardDeck
from moneypoly.config import (
	GO_SALARY,
	INCOME_TAX_AMOUNT,
	JAIL_FINE,
	JAIL_POSITION,
	LUXURY_TAX_AMOUNT,
)
from moneypoly.dice import Dice
from moneypoly.game import Game
from moneypoly.player import Player
from moneypoly.property import Property, PropertyGroup


def test_player_money_ops_and_negative_guards():
	p = Player("A")
	start = p.balance
	p.add_money(50)
	assert p.balance == start + 50
	p.deduct_money(20)
	assert p.balance == start + 30

	with pytest.raises(ValueError):
		p.add_money(-1)
	with pytest.raises(ValueError):
		p.deduct_money(-1)


def test_player_move_landing_on_go_collects_salary():
	p = Player("A")
	p.position = 39
	before = p.balance
	p.move(1)
	assert p.position == 0
	assert p.balance == before + GO_SALARY


def test_player_move_wrapping_not_on_go_collects_nothing():
	p = Player("A")
	p.position = 39
	before = p.balance
	p.move(2)
	assert p.position == 1
	assert p.balance == before


def test_player_jail_and_property_collection_methods():
	p = Player("A")
	prop = Property("X", 12, 100, 10)
	p.go_to_jail()
	assert p.position == JAIL_POSITION
	assert p.in_jail is True
	assert p.jail_turns == 0

	p.add_property(prop)
	p.add_property(prop)
	assert p.count_properties() == 1
	p.remove_property(prop)
	assert p.count_properties() == 0


def test_player_status_line_and_repr_cover():
	p = Player("A")
	text = p.status_line()
	assert "A:" in text
	assert "props=0" in text
	assert "Player('A'" in repr(p)


def test_property_rent_mortgage_unmortgage_and_availability():
	prop = Property("Solo", 1, 100, 10)
	owner = Player("Owner")
	prop.owner = owner
	assert prop.get_rent() == 10

	assert prop.mortgage() == 50
	assert prop.is_mortgaged is True
	assert prop.get_rent() == 0
	assert prop.mortgage() == 0

	assert prop.unmortgage() == 55
	# Error 17 behavior: Property.unmortgage() returns cost only; game flow
	# clears the mortgage flag after successful payment.
	assert prop.is_mortgaged is True
	prop.is_mortgaged = False
	assert prop.unmortgage() == 0

	fresh = Property("Fresh", 2, 120, 12)
	assert fresh.is_available() is True
	fresh.owner = owner
	assert fresh.is_available() is False


def test_property_group_methods_and_repr():
	group = PropertyGroup("Brown", "brown")
	p1 = Property("P1", 1, 60, 2, group=group)
	p2 = Property("P2", 3, 60, 4, group=group)
	owner = Player("Owner")

	p1.owner = owner
	assert group.all_owned_by(owner) is False
	p2.owner = owner
	assert group.all_owned_by(owner) is True
	assert group.size() == 2

	counts = group.get_owner_counts()
	assert counts[owner] == 1
	group.add_property(p2)
	assert "2 properties" in repr(group)


def test_board_tile_type_and_property_lookups():
	board = Board()
	assert board.get_tile_type(0) == "go"
	assert board.get_tile_type(2) == "community_chest"
	assert board.get_tile_type(7) == "chance"
	assert board.get_tile_type(5) == "railroad"
	assert board.get_tile_type(1) == "property"
	assert board.get_tile_type(12) == "blank"
	assert board.get_property_at(1) is not None
	assert board.get_property_at(12) is None


def test_board_purchasable_special_owned_and_unowned_queries():
	board = Board()
	prop = board.get_property_at(1)
	owner = Player("Owner")

	assert board.is_purchasable(12) is False
	assert board.is_purchasable(1) is True
	prop.owner = owner
	assert board.is_purchasable(1) is False
	prop.owner = None
	prop.is_mortgaged = True
	assert board.is_purchasable(1) is False

	assert board.is_special_tile(0) is True
	assert board.is_special_tile(1) is False
	assert prop in board.unowned_properties()


def test_board_properties_owned_by_and_repr():
	board = Board()
	owner = Player("Owner")
	prop = board.get_property_at(1)
	prop.owner = owner
	owned = board.properties_owned_by(owner)
	assert prop in owned
	assert "properties" in repr(board)


def test_bank_collect_pay_out_and_loan_paths(capsys):
	bank = Bank()
	player = Player("A")
	start = bank.get_balance()

	bank.collect(100)
	assert bank.get_balance() == start + 100

	# Current implementation applies negative amounts too.
	bank.collect(-40)
	assert bank.get_balance() == start + 60

	assert bank.pay_out(0) == 0
	assert bank.pay_out(-1) == 0
	assert bank.pay_out(10) == 10
	with pytest.raises(ValueError):
		bank.pay_out(bank.get_balance() + 1)

	before = player.balance
	bank_before_loan = bank.get_balance()
	bank.give_loan(player, 0)
	assert player.balance == before
	bank.give_loan(player, 200)
	assert player.balance == before + 200
	assert bank.get_balance() == bank_before_loan - 200
	assert bank.loan_count() == 1
	assert bank.total_loans_issued() == 200

	bank.summary()
	out = capsys.readouterr().out
	assert "Bank reserves" in out
	assert "Bank(" in repr(bank)


def test_carddeck_draw_cycle_peek_and_lengths(monkeypatch):
	cards = [{"description": "A"}, {"description": "B"}]
	deck = CardDeck(cards)
	assert len(deck) == 2
	assert deck.peek()["description"] == "A"
	assert deck.cards_remaining() == 2
	assert deck.draw()["description"] == "A"
	assert deck.draw()["description"] == "B"
	assert deck.draw()["description"] == "A"
	assert deck.cards_remaining() == 1

	monkeypatch.setattr("moneypoly.cards.random.shuffle", lambda values: values.reverse())
	deck.reshuffle()
	assert deck.index == 0
	assert "CardDeck(" in repr(deck)


def test_carddeck_empty_cases():
	deck = CardDeck([])
	assert deck.draw() is None
	assert deck.peek() is None
	assert deck.cards_remaining() == 0


def test_dice_roll_doubles_and_reset(monkeypatch):
	sequence = iter([2, 2, 3, 4])

	def fake_randint(low, high):
		assert low == 1
		assert high == 6
		return next(sequence)

	monkeypatch.setattr("moneypoly.dice.random.randint", fake_randint)

	dice = Dice()
	assert dice.roll() == 4
	assert dice.is_doubles() is True
	assert dice.doubles_streak == 1
	assert "DOUBLES" in dice.describe()

	assert dice.roll() == 7
	assert dice.is_doubles() is False
	assert dice.doubles_streak == 0
	dice.reset()
	assert dice.total() == 0
	assert "Dice(" in repr(dice)


def test_ui_helpers_input_confirm_and_prints(monkeypatch, capsys):
	p = Player("A")
	ui.print_banner("Hello")
	ui.print_player_card(p)
	ui.print_standings([p])
	ui.print_board_ownership(Board())
	out = capsys.readouterr().out
	assert "Hello" in out
	assert "Player" in out
	assert "Standings" in out

	assert ui.format_currency(1500) == "$1,500"

	monkeypatch.setattr("builtins.input", lambda _prompt: "abc")
	assert ui.safe_int_input("X", default=7) == 7
	monkeypatch.setattr("builtins.input", lambda _prompt: "42")
	assert ui.safe_int_input("X", default=0) == 42
	monkeypatch.setattr("builtins.input", lambda _prompt: "y")
	assert ui.confirm("?") is True


def test_game_current_and_advance_turn():
	g = Game(["A", "B"])
	assert g.current_player().name == "A"
	g.advance_turn()
	assert g.current_player().name == "B"
	assert g.turn_number == 1


def test_game_play_turn_in_jail_path(monkeypatch):
	g = Game(["A", "B"])
	p = g.current_player()
	p.in_jail = True
	called = {"jail": 0}
	monkeypatch.setattr(Game, "_handle_jail_turn", lambda self, _p: called.__setitem__("jail", called["jail"] + 1))
	g.play_turn()
	assert called["jail"] == 1
	assert g.current_index == 1


def test_game_play_turn_three_doubles_go_to_jail(monkeypatch):
	g = Game(["A", "B"])
	p = g.current_player()
	monkeypatch.setattr(g.dice, "roll", lambda: 4)
	g.dice.doubles_streak = 3
	g.play_turn()
	assert p.in_jail is True
	assert g.current_index == 1


def test_game_play_turn_doubles_gets_extra_turn(monkeypatch):
	g = Game(["A", "B"])
	monkeypatch.setattr(g.dice, "roll", lambda: 6)
	monkeypatch.setattr(g.dice, "is_doubles", lambda: True)
	monkeypatch.setattr(Game, "_move_and_resolve", lambda self, _p, _s: None)
	g.play_turn()
	assert g.current_index == 0


def test_game_play_turn_non_doubles_advances(monkeypatch):
	g = Game(["A", "B"])
	monkeypatch.setattr(g.dice, "roll", lambda: 5)
	monkeypatch.setattr(g.dice, "is_doubles", lambda: False)
	monkeypatch.setattr(Game, "_move_and_resolve", lambda self, _p, _s: None)
	g.play_turn()
	assert g.current_index == 1


def test_move_and_resolve_dispatches_and_checks_bankruptcy(monkeypatch):
	g = Game(["A", "B"])
	p = g.current_player()
	called = {"tile": 0, "bk": 0}

	monkeypatch.setattr(Player, "move", lambda self, _s: setattr(self, "position", 20))
	monkeypatch.setattr(Board, "get_tile_type", lambda self, _pos: "free_parking")
	monkeypatch.setattr(Game, "_tile_free_parking", lambda self, _p, _pos: called.__setitem__("tile", called["tile"] + 1))
	monkeypatch.setattr(Game, "_check_bankruptcy", lambda self, _p: called.__setitem__("bk", called["bk"] + 1))

	g._move_and_resolve(p, 5)
	assert called == {"tile": 1, "bk": 1}


def test_move_and_resolve_with_unknown_tile_still_checks_bankruptcy(monkeypatch):
	g = Game(["A", "B"])
	p = g.current_player()
	called = {"bk": 0}
	monkeypatch.setattr(Player, "move", lambda self, _s: setattr(self, "position", 12))
	monkeypatch.setattr(Board, "get_tile_type", lambda self, _pos: "mystery")
	monkeypatch.setattr(Game, "_check_bankruptcy", lambda self, _p: called.__setitem__("bk", 1))
	g._move_and_resolve(p, 2)
	assert called["bk"] == 1


def test_handle_property_tile_buy_auction_skip_self_owner_and_other(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	other = g.players[1]
	prop = g.board.get_property_at(1)
	calls = {"buy": 0, "auc": 0, "rent": 0}

	monkeypatch.setattr(Game, "buy_property", lambda self, _p, _prop: calls.__setitem__("buy", calls["buy"] + 1))
	monkeypatch.setattr(Game, "auction_property", lambda self, _prop: calls.__setitem__("auc", calls["auc"] + 1))
	monkeypatch.setattr(Game, "pay_rent", lambda self, _p, _prop: calls.__setitem__("rent", calls["rent"] + 1))

	prop.owner = None
	monkeypatch.setattr("builtins.input", lambda _prompt: "b")
	g._handle_property_tile(p, prop)
	monkeypatch.setattr("builtins.input", lambda _prompt: "a")
	g._handle_property_tile(p, prop)
	monkeypatch.setattr("builtins.input", lambda _prompt: "s")
	g._handle_property_tile(p, prop)

	prop.owner = p
	g._handle_property_tile(p, prop)

	prop.owner = other
	g._handle_property_tile(p, prop)

	assert calls == {"buy": 1, "auc": 1, "rent": 1}


def test_buy_property_succeeds_with_exact_price():
	g = Game(["A"])
	p = g.players[0]
	prop = g.board.get_property_at(1)

	p.balance = prop.price
	assert g.buy_property(p, prop) is True


def test_buy_property_fails_when_player_is_insufficient():
	g = Game(["A"])
	p = g.players[0]
	prop = g.board.get_property_at(1)
	p.balance = prop.price - 1
	assert g.buy_property(p, prop) is False


def test_buy_property_fails_if_property_already_owned_or_mortgaged():
	g = Game(["A"])
	p = g.players[0]

	# Not purchasable once already owned.
	second = g.board.get_property_at(3)
	second.owner = Player("Other")
	assert g.buy_property(p, second) is False

	# Not purchasable when mortgaged.
	third = g.board.get_property_at(6)
	third.is_mortgaged = True
	assert g.buy_property(p, third) is False


def test_pay_rent_paths_mortgaged_none_and_normal():
	g = Game(["A", "B"])
	tenant = g.players[0]
	owner = g.players[1]
	prop = g.board.get_property_at(1)

	prop.is_mortgaged = True
	before = tenant.balance
	g.pay_rent(tenant, prop)
	assert tenant.balance == before

	prop.is_mortgaged = False
	prop.owner = None
	g.pay_rent(tenant, prop)
	assert tenant.balance == before

	prop.owner = owner
	owner_before = owner.balance
	g.pay_rent(tenant, prop)
	assert tenant.balance < before
	assert owner.balance > owner_before


def test_mortgage_property_paths():
	g = Game(["A", "B"])
	player = g.players[0]
	other = g.players[1]
	prop = g.board.get_property_at(1)

	prop.owner = other
	assert g.mortgage_property(player, prop) is False

	prop.owner = player
	assert g.mortgage_property(player, prop) is True
	assert g.mortgage_property(player, prop) is False


def test_unmortgage_property_paths():
	g = Game(["A", "B"])
	player = g.players[0]
	other = g.players[1]
	prop = g.board.get_property_at(1)

	prop.owner = other
	assert g.unmortgage_property(player, prop) is False

	prop.owner = player
	assert g.unmortgage_property(player, prop) is False

	prop.mortgage()
	player.balance = 0
	assert g.unmortgage_property(player, prop) is False
	assert prop.is_mortgaged is True

	player.balance = 9999
	assert g.unmortgage_property(player, prop) is True


def test_trade_paths_owner_mismatch_insufficient_success():
	g = Game(["A", "B"])
	seller, buyer = g.players
	prop = g.board.get_property_at(1)

	assert g.trade(seller, buyer, prop, 50) is False

	prop.owner = seller
	seller.add_property(prop)
	buyer.balance = 0
	assert g.trade(seller, buyer, prop, 50) is False

	buyer.balance = 1000
	seller_before = seller.balance
	buyer_before = buyer.balance
	assert g.trade(seller, buyer, prop, 50) is True
	assert prop.owner == buyer
	assert seller.balance == seller_before + 50
	assert buyer.balance == buyer_before - 50


def test_trade_fails_for_negative_cash_without_state_change():
	g = Game(["A", "B"])
	seller, buyer = g.players
	prop = g.board.get_property_at(1)
	prop.owner = seller
	seller.add_property(prop)
	state = (prop.owner, seller.balance, buyer.balance)
	assert g.trade(seller, buyer, prop, -10) is False
	assert (prop.owner, seller.balance, buyer.balance) == state


def test_auction_property_no_bids_and_winner(monkeypatch):
	g = Game(["A", "B", "C"])
	prop = g.board.get_property_at(1)

	bids = iter([0, 0, 0])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _p, default=0: next(bids))
	g.auction_property(prop)
	assert prop.owner is None

	prop.owner = None
	bids = iter([10, 5, 999999, 30])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _p, default=0: next(bids))
	g.auction_property(prop)
	assert prop.owner is not None


def test_handle_jail_turn_use_card_then_move(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	p.in_jail = True
	p.get_out_of_jail_cards = 1
	monkeypatch.setattr("moneypoly.ui.confirm", lambda _p: True)
	monkeypatch.setattr(g.dice, "roll", lambda: 5)
	called = {"move": 0}
	monkeypatch.setattr(Game, "_move_and_resolve", lambda self, _p, _s: called.__setitem__("move", 1))

	g._handle_jail_turn(p)
	assert p.in_jail is False
	assert p.get_out_of_jail_cards == 0
	assert called["move"] == 1


def test_handle_jail_turn_pay_fine_and_move(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	p.in_jail = True
	p.get_out_of_jail_cards = 0
	start = p.balance
	answers = iter([True])
	monkeypatch.setattr("moneypoly.ui.confirm", lambda _p: next(answers))
	monkeypatch.setattr(g.dice, "roll", lambda: 4)
	called = {"move": 0}
	monkeypatch.setattr(Game, "_move_and_resolve", lambda self, _p, _s: called.__setitem__("move", 1))

	g._handle_jail_turn(p)
	assert p.in_jail is False
	assert called["move"] == 1
	assert p.balance == start - JAIL_FINE


def test_handle_jail_turn_serve_then_mandatory_release(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	p.in_jail = True
	p.jail_turns = 2
	p.get_out_of_jail_cards = 0
	monkeypatch.setattr("moneypoly.ui.confirm", lambda _p: False)
	monkeypatch.setattr(g.dice, "roll", lambda: 3)
	called = {"move": 0}
	monkeypatch.setattr(Game, "_move_and_resolve", lambda self, _p, _s: called.__setitem__("move", 1))

	g._handle_jail_turn(p)
	assert p.in_jail is False
	assert p.jail_turns == 0
	assert called["move"] == 1


def test_apply_card_none_unknown_collect_pay_jail_jail_free(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	before = p.balance

	g._apply_card(p, None)
	g._apply_card(p, {"description": "?", "action": "unknown", "value": 0})

	monkeypatch.setattr(g.bank, "pay_out", lambda amount: amount)
	g._apply_card(p, {"description": "C", "action": "collect", "value": 25})
	assert p.balance == before + 25

	g._apply_card(p, {"description": "P", "action": "pay", "value": 10})
	assert p.balance == before + 15

	g._apply_card(p, {"description": "J", "action": "jail", "value": 0})
	assert p.in_jail is True

	cards_before = p.get_out_of_jail_cards
	g._apply_card(p, {"description": "F", "action": "jail_free", "value": 0})
	assert p.get_out_of_jail_cards == cards_before + 1


def test_apply_card_move_to_and_group_collect_cards(monkeypatch):
	g = Game(["A", "B", "C"])
	p = g.players[0]
	p.position = 35
	called = {"prop": 0}

	monkeypatch.setattr(Board, "get_tile_type", lambda self, _pos: "property")
	monkeypatch.setattr(Board, "get_property_at", lambda self, _pos: g.board.properties[0])
	monkeypatch.setattr(Game, "_handle_property_tile", lambda self, _p, _prop: called.__setitem__("prop", 1))

	g._apply_card(p, {"description": "M", "action": "move_to", "value": 1})
	assert p.position == 1
	assert called["prop"] == 1

	receiver = g.players[0]
	g.players[1].balance = 100
	g.players[2].balance = 5
	start_receiver = receiver.balance
	g._apply_card(receiver, {"description": "Bday", "action": "birthday", "value": 10})
	assert receiver.balance == start_receiver + 10

	start_receiver = receiver.balance
	g._apply_card(receiver, {"description": "All", "action": "collect_from_all", "value": 50})
	assert receiver.balance == start_receiver + 50


def test_check_bankruptcy_paths_and_index_adjustment():
	g = Game(["A", "B"])
	alive = g.players[0]
	doomed = g.players[1]

	g._check_bankruptcy(alive)
	assert alive in g.players

	prop = g.board.get_property_at(1)
	prop.owner = doomed
	doomed.add_property(prop)
	doomed.balance = 0
	g.current_index = 1
	g._check_bankruptcy(doomed)
	assert doomed not in g.players
	assert prop.owner is None
	assert g.current_index == 0


def test_find_winner_current_behavior_and_empty_case():
	g = Game(["A", "B"])
	g.players[0].balance = 100
	g.players[1].balance = 200
	assert g.find_winner().name == "B"
	g.players = []
	assert g.find_winner() is None


def test_apply_card_advance_to_go_collects_salary_even_from_go(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	p.position = 0
	start = p.balance
	monkeypatch.setattr(Board, "get_tile_type", lambda self, _pos: "go")
	g._apply_card(
		p,
		{
			"description": "Advance to Go. Collect $200.",
			"action": "move_to",
			"value": 0,
		},
	)
	assert p.position == 0
	assert p.balance == start + GO_SALARY


def test_play_turn_moves_to_next_remaining_player_after_bankruptcy(monkeypatch):
	g = Game(["A", "B", "C"])
	g.current_index = 1
	eliminated = g.current_player()

	monkeypatch.setattr(g.dice, "roll", lambda: 6)
	monkeypatch.setattr(g.dice, "is_doubles", lambda: False)

	def bankrupt_current(self, player, _steps):
		player.balance = 0
		self._check_bankruptcy(player)

	monkeypatch.setattr(Game, "_move_and_resolve", bankrupt_current)
	g.play_turn()

	assert eliminated not in g.players
	assert g.current_player().name == "C"


def test_play_turn_bankrupt_player_on_doubles_does_not_get_extra_turn(monkeypatch):
	g = Game(["A", "B", "C"])
	g.current_index = 1
	eliminated = g.current_player()

	monkeypatch.setattr(g.dice, "roll", lambda: 6)
	monkeypatch.setattr(g.dice, "is_doubles", lambda: True)

	def bankrupt_current(self, player, _steps):
		player.balance = 0
		self._check_bankruptcy(player)

	monkeypatch.setattr(Game, "_move_and_resolve", bankrupt_current)
	g.play_turn()

	assert eliminated not in g.players
	assert g.turn_number == 1


def test_run_ends_with_winner_and_with_no_players(monkeypatch, capsys):
	g = Game(["A", "B"])
	counter = {"n": 0}

	def fake_play_turn(self):
		counter["n"] += 1
		if counter["n"] >= 2:
			self.meta["running"] = False

	monkeypatch.setattr(Game, "play_turn", fake_play_turn)
	monkeypatch.setattr("moneypoly.ui.print_standings", lambda _players: None)
	g.run()
	out = capsys.readouterr().out
	assert "GAME OVER" in out

	g2 = Game(["A"])
	g2.players = []
	g2.run()
	out2 = capsys.readouterr().out
	assert "no players remaining" in out2.lower()


def test_interactive_menu_all_choices(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	calls = {"s": 0, "b": 0, "m": 0, "u": 0, "t": 0, "l": 0}

	choices = iter([1, 2, 3, 4, 5, 6, 20, 0])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: next(choices))
	monkeypatch.setattr("moneypoly.ui.print_standings", lambda _players: calls.__setitem__("s", calls["s"] + 1))
	monkeypatch.setattr("moneypoly.ui.print_board_ownership", lambda _board: calls.__setitem__("b", calls["b"] + 1))
	monkeypatch.setattr(Game, "_menu_mortgage", lambda self, _p: calls.__setitem__("m", calls["m"] + 1))
	monkeypatch.setattr(Game, "_menu_unmortgage", lambda self, _p: calls.__setitem__("u", calls["u"] + 1))
	monkeypatch.setattr(Game, "_menu_trade", lambda self, _p: calls.__setitem__("t", calls["t"] + 1))
	monkeypatch.setattr(g.bank, "give_loan", lambda _p, _amt: calls.__setitem__("l", calls["l"] + 1))

	g.interactive_menu(p)
	assert calls == {"s": 1, "b": 1, "m": 1, "u": 1, "t": 1, "l": 1}


def test_menu_mortgage_and_unmortgage_paths(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	prop = g.board.get_property_at(1)
	prop.owner = p
	p.add_property(prop)
	calls = {"mort": 0, "unmort": 0}

	monkeypatch.setattr(Game, "mortgage_property", lambda self, _p, _prop: calls.__setitem__("mort", calls["mort"] + 1))
	monkeypatch.setattr(Game, "unmortgage_property", lambda self, _p, _prop: calls.__setitem__("unmort", calls["unmort"] + 1))

	prop.is_mortgaged = False
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: 1)
	g._menu_mortgage(p)

	prop.is_mortgaged = True
	g._menu_unmortgage(p)

	assert calls == {"mort": 1, "unmort": 1}


def test_menu_trade_paths(monkeypatch):
	g = Game(["A", "B"])
	player = g.players[0]
	prop = g.board.get_property_at(1)
	prop.owner = player
	player.add_property(prop)
	called = {"trade": 0}
	monkeypatch.setattr(Game, "trade", lambda self, _s, _b, _prop, _cash: called.__setitem__("trade", called["trade"] + 1))

	# invalid partner index
	choices = iter([99])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: next(choices))
	g._menu_trade(player)

	# valid partner + invalid property index
	choices = iter([1, 99])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: next(choices))
	g._menu_trade(player)

	# success path
	choices = iter([1, 1, 50])
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: next(choices))
	g._menu_trade(player)

	assert called["trade"] == 1


def test_tile_handlers_cover_all_special_tile_paths(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]

	# Go To Jail branch
	g._tile_go_to_jail(p, p.position)
	assert p.in_jail is True

	# Tax branches
	p.in_jail = False
	start_balance = p.balance
	start_bank = g.bank.get_balance()
	g._tile_income_tax(p, p.position)
	assert p.balance == start_balance - INCOME_TAX_AMOUNT
	assert g.bank.get_balance() == start_bank + INCOME_TAX_AMOUNT

	start_balance = p.balance
	start_bank = g.bank.get_balance()
	g._tile_luxury_tax(p, p.position)
	assert p.balance == start_balance - LUXURY_TAX_AMOUNT
	assert g.bank.get_balance() == start_bank + LUXURY_TAX_AMOUNT

	# Card draw paths (chance and community chest)
	seen = {"chance": 0, "community": 0}
	monkeypatch.setattr(g.meta["chance_deck"], "draw", lambda: {"action": "collect", "value": 0, "description": "C"})
	monkeypatch.setattr(g.meta["community_deck"], "draw", lambda: {"action": "collect", "value": 0, "description": "CC"})

	def fake_apply(self, _player, card):
		if card["description"] == "C":
			seen["chance"] += 1
		else:
			seen["community"] += 1

	monkeypatch.setattr(Game, "_apply_card", fake_apply)
	g._tile_chance(p, 7)
	g._tile_community_chest(p, 2)
	assert seen == {"chance": 1, "community": 1}


def test_tile_property_and_railroad_none_property_branches(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	called = {"n": 0}
	monkeypatch.setattr(Board, "get_property_at", lambda self, _pos: None)
	monkeypatch.setattr(
		Game,
		"_handle_property_tile",
		lambda self, _player, _prop: called.__setitem__("n", called["n"] + 1),
	)
	g._tile_property(p, 12)
	g._tile_railroad(p, 5)
	assert called["n"] == 0


def test_carddeck_repr_empty_deck_edge_case():
	deck = CardDeck([])
	text = repr(deck)
	assert "CardDeck(" in text


def test_apply_card_move_to_non_property_tile_path(monkeypatch):
	g = Game(["A", "B"])
	p = g.players[0]
	p.position = 10
	called = {"prop": 0}
	monkeypatch.setattr(Board, "get_tile_type", lambda self, _pos: "blank")
	monkeypatch.setattr(
		Game,
		"_handle_property_tile",
		lambda self, _player, _prop: called.__setitem__("prop", called["prop"] + 1),
	)
	g._apply_card(p, {"description": "Move", "action": "move_to", "value": 12})
	assert p.position == 12
	assert called["prop"] == 0


def test_card_collect_from_all_and_birthday_insufficient_payers_branch():
	g = Game(["A", "B", "C"])
	receiver = g.players[0]
	g.players[1].balance = 0
	g.players[2].balance = 3
	start = receiver.balance
	g._card_birthday(receiver, 10, None)
	g._card_collect_from_all(receiver, 10, None)
	assert receiver.balance == start


def test_menu_early_return_branches_no_options(monkeypatch):
	g = Game(["A"])
	player = g.players[0]

	# No properties to mortgage
	g._menu_mortgage(player)

	# No mortgaged properties to redeem
	g._menu_unmortgage(player)

	# No other players to trade with
	g._menu_trade(player)

	# Add a second player and hit "no properties to trade" branch
	g.players.append(Player("B"))
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: 1)
	g._menu_trade(player)


def test_menu_invalid_selection_branches(monkeypatch):
	g = Game(["A", "B"])
	player = g.players[0]
	prop = g.board.get_property_at(1)
	prop.owner = player
	player.add_property(prop)

	# Invalid index in mortgage menu should no-op
	prop.is_mortgaged = False
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: 99)
	g._menu_mortgage(player)
	assert prop.is_mortgaged is False

	# Valid mortgage, then invalid index in unmortgage menu should no-op
	g.mortgage_property(player, prop)
	monkeypatch.setattr("moneypoly.ui.safe_int_input", lambda _prompt, default=0: 99)
	g._menu_unmortgage(player)
	assert prop.is_mortgaged is True

