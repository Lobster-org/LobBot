from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from app.core.events import EventBus
from app.modules.games.events import GAME_COMPLETED, GAME_WON
from app.modules.games.games import CoinFlipGame, GuessNumberGame, RockPaperScissorsGame, TriviaGame
from app.modules.games.handlers import bet_command, cancel_game_callback, rps_callback, trivia_callback
from app.modules.games.registry import GameRegistry
from app.modules.games.services.game_service import CooldownActive, GameService
from app.modules.games.services.session_service import GameSessionService
from app.modules.games.services.round_service import RoundMatchService
from app.modules.games.services.reward_tracker import RewardTracker


class Random:
    def choice(self, values): return values[0]
    def randint(self, low, high): return 10

def service(clock=lambda: 100.0):
    registry = GameRegistry()
    for game in (CoinFlipGame(), GuessNumberGame(), RockPaperScissorsGame(), TriviaGame()): registry.register(game)
    return GameService(registry, GameSessionService(), EventBus(), Random(), clock,
                       RoundMatchService(), RewardTracker())

@pytest.mark.asyncio
async def test_coinflip_is_deterministic_and_emits_results():
    game = service(); events = []
    async def record(event): events.append(event.name)
    game.events.subscribe(GAME_COMPLETED, record); game.events.subscribe(GAME_WON, record)
    result = await game.coinflip(-100, 1, "heads")
    assert result.won is True and result.metadata["outcome"] == "heads"
    assert events == [GAME_COMPLETED, GAME_WON]

def test_rps_winner_rules():
    game = RockPaperScissorsGame()
    assert game.play("rock", lambda _: "scissors") == ("scissors", True)
    assert game.play("rock", lambda _: "paper") == ("paper", False)
    assert game.play("rock", lambda _: "rock") == ("rock", None)

@pytest.mark.asyncio
async def test_guess_high_low_win_and_max_attempts():
    game = service(); await game.start_guess(-100, 1)
    assert (await game.guess(-100, 1, 5))[0] == "low"
    assert (await game.guess(-100, 1, 15))[0] == "high"
    assert (await game.guess(-100, 1, 10))[0] == "correct"
    game._cooldowns.clear(); await game.start_guess(-100, 1)
    for _ in range(4): assert (await game.guess(-100, 1, 1))[0] == "low"
    assert (await game.guess(-100, 1, 1))[0] == "failed"

def test_trivia_answers_and_category():
    game = TriviaGame(); question = game.question("technology", lambda values: values[0])
    assert game.answer(question, question["answer"]) is True
    assert game.answer(question, 3) is False

def test_session_expiration_and_cooldown():
    now = datetime.now(timezone.utc); clock = [now]
    sessions = GameSessionService(timeout=2, clock=lambda: clock[0]); sessions.create(-100, 1, "guess")
    clock[0] += timedelta(seconds=3)
    assert sessions.get(-100, 1, "guess") is None
    game = service()
    game.check_cooldown(-100, 1, "coinflip")
    with pytest.raises(CooldownActive): game.check_cooldown(-100, 1, "coinflip")

@pytest.mark.asyncio
async def test_wrong_user_rps_callback_is_rejected():
    game = service(); match = game.matches.create_rps(-100, 1, 3, 5)
    answers = []
    async def answer(*args, **kwargs): answers.append((args, kwargs))
    callback = SimpleNamespace(data=f"games:rps:{match.id}:rock", from_user=SimpleNamespace(id=2), answer=answer)
    await rps_callback(callback, game)
    assert answers[0][1]["show_alert"] is True


@pytest.mark.asyncio
async def test_completed_rps_session_cannot_be_replayed():
    game = service(); match = game.matches.create_rps(-100, 1, None, 1)
    edits, answers = [], []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): answers.append((args, kwargs))
    callback = SimpleNamespace(
        data=f"games:rps:{match.id}:rock", from_user=SimpleNamespace(id=1), answer=answer,
        message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text),
    )
    await rps_callback(callback, game)
    await rps_callback(callback, game)
    assert len(edits) == 1
    assert answers[-1][1]["show_alert"] is True


@pytest.mark.asyncio
async def test_multiplayer_rps_hides_choices_until_both_players_answer():
    game = service(); match = game.matches.create_rps(-100, 1, 2, 1, "@alice", "Bob")
    edits, answers = [], []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): answers.append((args, kwargs))
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text)
    first = SimpleNamespace(data=f"games:rps:{match.id}:rock", from_user=SimpleNamespace(id=1), answer=answer, message=message)
    second = SimpleNamespace(data=f"games:rps:{match.id}:scissors", from_user=SimpleNamespace(id=2), answer=answer, message=message)
    await rps_callback(first, game)
    assert "Confirmed: <b>@alice</b>" in edits[0]
    assert "Waiting for: <b>Bob</b>" in edits[0]
    assert "rock" not in edits[0]
    await rps_callback(second, game)
    assert "@alice" in edits[1] and "Bob" in edits[1]
    assert "rock" in edits[1] and "scissors" in edits[1]


@pytest.mark.asyncio
async def test_trivia_reveal_includes_question_and_every_option():
    game = service(); question = game.registry.get("trivia").question("technology", lambda values: values[0])
    game.sessions.create(-100, 1, "trivia", {"question": question, "category": "technology", "rounds": 1, "round": 1, "score": 0})
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    callback = SimpleNamespace(
        data="games:trivia:1:1:1", from_user=SimpleNamespace(id=1), answer=answer,
        message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text),
    )
    await trivia_callback(callback, game)
    reveal = edits[0]
    assert question["question"] in reveal
    assert all(option in reveal for option in question["choices"])
    assert "your answer" in reveal and "Coins gained" in reveal


@pytest.mark.asyncio
async def test_rps_next_round_edits_same_message_without_sending_another():
    game = service(); match = game.matches.create_rps(-100, 1, None, 5, "Alice", "LobBot")
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def forbidden_answer(*args, **kwargs): raise AssertionError("must not send a new message")
    async def callback_answer(*args, **kwargs): pass
    callback = SimpleNamespace(
        data=f"games:rps:{match.id}:rock", from_user=SimpleNamespace(id=1), answer=callback_answer,
        message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text, answer=forbidden_answer),
    )
    await rps_callback(callback, game)
    assert len(edits) == 1
    assert "Round winner" in edits[0] and "Round 2/5" in edits[0]


@pytest.mark.asyncio
async def test_betting_rps_keeps_pot_visible_during_rounds():
    game = service(); match = game.matches.create_rps(
        -100, 1, None, 5, "Alice", "LobBot", betting=True
    )
    match.bets = {1: 40, 2: 60}
    # Use a multiplayer opponent so both escrow contributions form the pot.
    match.opponent_id = 2; match.opponent_name = "Bob"; match.scores[2] = 0
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): pass
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text)
    await rps_callback(SimpleNamespace(data=f"games:rps:{match.id}:rock", from_user=SimpleNamespace(id=1), answer=answer, message=message), game)
    await rps_callback(SimpleNamespace(data=f"games:rps:{match.id}:scissors", from_user=SimpleNamespace(id=2), answer=answer, message=message), game)
    assert "Pot: <b>100 coins</b>" in edits[-1]


@pytest.mark.asyncio
async def test_match_creator_can_place_custom_bet_in_latest_betting_match():
    game = service()
    game.matches.create_rps(-100, 1, None, 5, "Alice", "LobBot")
    betting = game.matches.create_rps(
        -100, 1, 2, 5, "Alice", "Bob", betting=True, message_id=99
    )
    class Bets:
        async def place(self, chat, user, match, amount, all_in):
            assert (chat, user, match, amount, all_in) == (-100, 1, betting.id, 25, False)
            return {"ok": True, "amount": 25}
    game.bets = Bets()
    edits, replies = [], []
    async def edit_message_text(**kwargs): edits.append(kwargs)
    async def delete(): pass
    async def reply(text, **kwargs): replies.append(text)
    message = SimpleNamespace(
        text="/bet 25", chat=SimpleNamespace(id=-100, type="supergroup"),
        from_user=SimpleNamespace(id=1), bot=SimpleNamespace(edit_message_text=edit_message_text),
        delete=delete, reply=reply,
    )

    await bet_command(message, game)

    assert betting.bets == {1: 25}
    assert "Alice" in edits[0]["text"] and "25" in edits[0]["text"]
    assert replies == []


@pytest.mark.asyncio
async def test_trivia_next_round_edits_same_message_without_sending_another():
    game = service(); question = game.registry.get("trivia").question("technology", lambda values: values[0])
    game.sessions.create(-100, 1, "trivia", {"question": question, "category": "technology", "rounds": 5, "round": 1, "score": 0})
    edits = []
    async def edit_text(text, **kwargs): edits.append(text)
    async def forbidden_answer(*args, **kwargs): raise AssertionError("must not send a new message")
    async def callback_answer(*args, **kwargs): pass
    callback = SimpleNamespace(
        data="games:trivia:1:0:1", from_user=SimpleNamespace(id=1), answer=callback_answer,
        message=SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text, answer=forbidden_answer),
    )
    await trivia_callback(callback, game)
    assert len(edits) == 1
    assert "Question 1/5" in edits[0] and "Round 2/5" in edits[0]


@pytest.mark.asyncio
async def test_rps_participant_can_cancel_and_outsider_cannot():
    game = service(); match = game.matches.create_rps(-100, 1, 2, 5, "Alice", "Bob")
    edits, alerts = [], []
    async def edit_text(text, **kwargs): edits.append(text)
    async def answer(*args, **kwargs): alerts.append((args, kwargs))
    message = SimpleNamespace(chat=SimpleNamespace(id=-100), edit_text=edit_text)
    outsider = SimpleNamespace(data=f"games:cancel:rps:{match.id}", from_user=SimpleNamespace(id=3), answer=answer, message=message)
    await cancel_game_callback(outsider, game)
    assert alerts[-1][1]["show_alert"] is True and game.matches.get(match.id)
    participant = SimpleNamespace(data=f"games:cancel:rps:{match.id}", from_user=SimpleNamespace(id=2), answer=answer, message=message)
    await cancel_game_callback(participant, game)
    assert "cancelled by <b>Bob</b>" in edits[0]
    assert game.matches.get(match.id) is None
