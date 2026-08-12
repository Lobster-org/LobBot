from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from secrets import token_hex


@dataclass(slots=True)
class RPSMatch:
    id: str
    chat_id: int
    owner_id: int
    opponent_id: int | None
    rounds: int
    owner_name: str = "Player 1"
    opponent_name: str = "LobBot"
    betting: bool = False
    bets: dict[int, int] = field(default_factory=dict)
    message_id: int | None = None
    settlement_pending: bool = False
    scores: dict[int, int] = field(default_factory=dict)
    choices: dict[int, str] = field(default_factory=dict)
    round_number: int = 1
    expires_at: datetime | None = None


@dataclass(slots=True)
class BoardMatch:
    id: str
    game_type: str
    chat_id: int
    owner_id: int
    opponent_id: int | None
    rounds: int
    owner_name: str
    opponent_name: str
    board: list
    turn_id: int
    scores: dict[int, int] = field(default_factory=dict)
    round_number: int = 1
    expires_at: datetime | None = None


@dataclass(slots=True)
class HangmanSetup:
    id: str
    chat_id: int
    creator_id: int
    guesser_id: int
    creator_name: str
    guesser_name: str
    message_id: int
    expires_at: datetime


@dataclass(slots=True)
class HangmanMatch:
    id: str
    game_type: str
    chat_id: int
    owner_id: int
    opponent_id: int
    owner_name: str
    opponent_name: str
    message_id: int
    secret: str
    hint: str | None = None
    guessed: set[str] = field(default_factory=set)
    wrong: set[str] = field(default_factory=set)
    attempts_left: int = 6
    expires_at: datetime | None = None


class RoundMatchService:
    def __init__(self, timeout_seconds=300):
        self.timeout_seconds = timeout_seconds; self._matches = {}; self._hangman_setups = {}
    def create_rps(self, chat_id, owner_id, opponent_id, rounds,
                   owner_name="Player 1", opponent_name="LobBot", betting=False,
                   message_id=None):
        match = RPSMatch(
            id=token_hex(4), chat_id=chat_id, owner_id=owner_id,
            opponent_id=opponent_id, rounds=rounds, owner_name=owner_name,
            opponent_name=opponent_name, betting=betting,
            message_id=message_id,
            scores={owner_id: 0, (opponent_id or 0): 0},
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.timeout_seconds),
        )
        self._matches[match.id] = match; return match
    def create_board(self, game_type, chat_id, owner_id, opponent_id, rounds,
                     owner_name, opponent_name, board):
        match = BoardMatch(
            id=token_hex(4), game_type=game_type, chat_id=chat_id,
            owner_id=owner_id, opponent_id=opponent_id, rounds=rounds,
            owner_name=owner_name, opponent_name=opponent_name, board=board,
            turn_id=owner_id, scores={owner_id: 0, (opponent_id or 0): 0},
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.timeout_seconds),
        )
        self._matches[match.id] = match; return match
    def create_hangman_setup(self, chat_id, creator_id, guesser_id,
                             creator_name, guesser_name, message_id):
        setup = HangmanSetup(
            token_hex(4), chat_id, creator_id, guesser_id, creator_name,
            guesser_name, message_id,
            datetime.now(timezone.utc) + timedelta(seconds=self.timeout_seconds),
        )
        self._hangman_setups[setup.id] = setup; return setup
    def get_hangman_setup(self, setup_id, creator_id):
        setup = self._hangman_setups.get(setup_id)
        if not setup or setup.creator_id != creator_id or setup.expires_at <= datetime.now(timezone.utc):
            return None
        return setup
    def activate_hangman(self, setup, secret, hint=None):
        self._hangman_setups.pop(setup.id, None)
        match = HangmanMatch(
            id=setup.id, game_type="hangman", chat_id=setup.chat_id,
            owner_id=setup.creator_id, opponent_id=setup.guesser_id,
            owner_name=setup.creator_name, opponent_name=setup.guesser_name,
            message_id=setup.message_id, secret=secret, hint=hint,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.timeout_seconds),
        )
        self._matches[match.id] = match; return match
    def cancel_hangman_setup(self, setup_id, creator_id):
        setup = self.get_hangman_setup(setup_id, creator_id)
        if setup: self._hangman_setups.pop(setup_id, None)
        return setup
    def get(self, match_id):
        match = self._matches.get(match_id)
        if match and match.expires_at <= datetime.now(timezone.utc): return None
        return match
    def delete(self, match_id): return self._matches.pop(match_id, None)
    def for_user(self, chat_id, user_id):
        return next((match for match in self._matches.values()
                     if match.chat_id == chat_id and user_id in {match.owner_id, match.opponent_id}), None)
    def awaiting_bet_for_user(self, chat_id, user_id):
        now = datetime.now(timezone.utc)
        candidates = (
            match for match in reversed(tuple(self._matches.values()))
            if match.chat_id == chat_id
            and match.betting
            and not match.settlement_pending
            and match.expires_at > now
            and user_id in {match.owner_id, match.opponent_id}
            and user_id not in match.bets
            and len(match.bets) < 2
        )
        return next(candidates, None)
    def all(self): return tuple(self._matches.values())
    def expired(self):
        now = datetime.now(timezone.utc)
        return tuple(match for match in self._matches.values() if match.expires_at <= now)
    def cancel_for_user(self, chat_id, user_id):
        keys = [match_id for match_id, match in self._matches.items()
                if match.chat_id == chat_id and user_id in {match.owner_id, match.opponent_id}]
        for match_id in keys: self._matches.pop(match_id, None)
        return len(keys)
    def clear(self): self._matches.clear(); self._hangman_setups.clear()
