"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

# Will maybe someday split this up into different files.


class User(ndb.Model):
    """User profile"""
    user_name = ndb.StringProperty(required=True)
    password = ndb.StringProperty()
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""
    players = ndb.IntegerProperty(required=True)
    die_faces = ndb.IntegerProperty(required=True)
    dice_total = ndb.IntegerProperty(required=True)
    wild = ndb.IntegerProperty(required=True)
    game_over = ndb.BooleanProperty(required=True, default=False)
    cancelled = ndb.BooleanProperty(required=True, default=False)
    turn = ndb.IntegerProperty(required=True)
    bid_player = ndb.IntegerProperty(required=True)
    bid_face = ndb.IntegerProperty(required=True)
    bid_total = ndb.IntegerProperty(required=True)
    winner = ndb.KeyProperty(kind='User')

    @classmethod
    def new_game(cls, users, dice_per_player, dice_sides, wild):
        """Creates and returns a new game"""
        if dice_per_player < 1:
            raise ValueError('At least 1 die is needed to play.')
        if dice_sides < 1:
            raise ValueError('Can only play in positive space.')
        # Set up game
        game = Game(players=len(users),
                    die_faces=dice_sides,
                    dice_total=dice_per_player,
                    wild=wild,
                    game_over=False,
                    turn=0,
                    bid_player=0,
                    bid_face=1,
                    bid_total=0)
        game.put()
        # Set up players
        for player_number in range(0, len(users)):
            user = User.query(User.user_name == users[player_number]).get()
            player = Player(game=game.key, order=player_number+1,
                            user=user.key)
            player.put()
            dice_array = [0]*dice_sides
            for die in range(0, dice_per_player):
                roll = random.randrange(0, dice_sides, 1)
                dice_array[roll] += 1
            for face, total in enumerate(dice_array):
                if total != 0:
                    (Dice(player=player.key, face=face+1,
                          total=total).put())
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.players = self.players
        if self.winner:
            form.winner = self.winner.get().user_name
        form.die_faces = self.die_faces
        form.dice_total = self.dice_total
        form.bid_player = self.bid_player
        form.bid_face = self.bid_face
        form.bid_total = self.bid_total
        form.game_over = self.game_over
        form.cancelled = self.cancelled
        form.turn = self.turn
        form.message = message
        return form


class Player(ndb.Model):
    """Player object to map users to game"""
    game = ndb.KeyProperty(required=True, kind='Game')
    user = ndb.KeyProperty(required=True, kind='User')
    order = ndb.IntegerProperty(required=True)


class Dice(ndb.Model):
    player = ndb.KeyProperty(required=True, kind='Player')
    face = ndb.IntegerProperty(required=True)
    total = ndb.IntegerProperty(required=True)

    @classmethod
    def to_form(self, dice_query):
        dice = []
        for item in dice_query:
            form = DiceForm()
            player = item.player.get()
            form.player = player.order
            form.face = item.face
            form.total = item.total
            dice.append(form)
        forms = DiceForms()
        forms.dice = dice
        return forms


class Score(ndb.Model):
    user = ndb.KeyProperty(required=True, kind='User')
    games = ndb.IntegerProperty(required=True)
    wins = ndb.IntegerProperty(required=True)
    # Total number of turns took to win a game
    score = ndb.IntegerProperty(required=True)

    def to_form(self, rank):
        """Returns a GameForm representation of the Game"""
        form = ScoreForm()
        form.rank = rank
        form.user_name = self.user.get().user_name
        form.games = self.games
        form.wins = self.wins
        form.score = self.score
        return form


class GameHistory(ndb.Model):
    game = ndb.KeyProperty(required=True, kind='Game')
    turn = ndb.IntegerProperty(required=True)
    player = ndb.KeyProperty(required=True, kind='Player')
    bid_face = ndb.IntegerProperty(required=True)
    bid_total = ndb.IntegerProperty(required=True)

    @classmethod
    def to_form(self, history_query):
        game_history = []
        for turn in history_query:
            # Find player name that raised bid
            player = turn.player.get()
            user = player.user.get()

            # Put data into form
            form = GameHistoryForm()
            form.turn = turn.turn
            form.user_name = user.user_name
            form.bid_face = turn.bid_face
            form.bid_total = turn.bid_total
            game_history.append(form)
        forms = GameHistoryForms()
        forms.game_history = game_history
        return forms


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    players = messages.IntegerField(2, required=True)
    die_faces = messages.IntegerField(3, required=True)
    dice_total = messages.IntegerField(4, required=True)
    winner = messages.StringField(5)
    game_over = messages.BooleanField(6, required=True)
    cancelled = messages.BooleanField(7, required=True)
    turn = messages.IntegerField(8, required=True)
    message = messages.StringField(9, required=True)
    bid_player = messages.IntegerField(10, required=True)
    bid_face = messages.IntegerField(11, required=True)
    bid_total = messages.IntegerField(12, required=True)


class GameForms(messages.Message):
    """Used to raise the bid in an existing game"""
    games = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    users = messages.StringField(1, repeated=True)
    dice_per_player = messages.IntegerField(2, default=5)
    dice_sides = messages.IntegerField(3, default=6)
    wild = messages.IntegerField(4, default=1)


class RaiseBidForm(messages.Message):
    """Used to raise the bid in an existing game"""
    bid_face = messages.IntegerField(1, required=True)
    bid_total = messages.IntegerField(2, required=True)
    password = messages.StringField(3)


class DiceForm(messages.Message):
    """Used to raise the bid in an existing game"""
    player = messages.IntegerField(1, required=True)
    face = messages.IntegerField(2, required=True)
    total = messages.IntegerField(3, required=True)


class DiceForms(messages.Message):
    """Used to raise the bid in an existing game"""
    dice = messages.MessageField(DiceForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class GameHistoryForm(messages.Message):
    turn = messages.IntegerField(1, required=True)
    user_name = messages.StringField(2, required=True)
    bid_face = messages.IntegerField(3, required=True)
    bid_total = messages.IntegerField(4, required=True)


class GameHistoryForms(messages.Message):
    """A form to send the history for a game."""
    game_history = messages.MessageField(GameHistoryForm, 1, repeated=True)


class ScoreForm(messages.Message):
    rank = messages.IntegerField(1, required=True)
    user_name = messages.StringField(2, required=True)
    games = messages.IntegerField(3, required=True)
    wins = messages.IntegerField(4, required=True)
    score = messages.IntegerField(5, required=True)


class ScoreForms(messages.Message):
    """A form to send the history for a game."""
    scores = messages.MessageField(ScoreForm, 1, repeated=True)
