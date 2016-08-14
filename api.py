# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""


import logging
import endpoints

from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, GameHistory, Player, Dice, Score
from models import (
    StringMessage,
    NewGameForm,
    GameForm,
    GameForms,
    RaiseBidForm,
    DiceForms,
    GameHistoryForm,
    GameHistoryForms,
    ScoreForms)
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
GET_USER_GAMES_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1),
    password=messages.StringField(2),)
RAISE_BID_REQUEST = endpoints.ResourceContainer(
    RaiseBidForm,
    urlsafe_game_key=messages.StringField(1),)
GET_DICE_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1),
    password=messages.StringField(2),
    urlsafe_game_key=messages.StringField(3),)
CALL_LIAR_REQUEST = endpoints.ResourceContainer(
    password=messages.StringField(1),
    urlsafe_game_key=messages.StringField(2))
USER_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1),
    email=messages.StringField(2),
    password=messages.StringField(3),)


@endpoints.api(name='liars_dice', version='v1')
class LiarsDiceApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.user_name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(
            user_name=request.user_name,
            email=request.email,
            password=request.password)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        # check for user uniquness
        user_bucket = []

        for user in request.users:
            if user in user_bucket:
                raise endpoints.BadRequestException('A user cannot be '
                                                    'represented more than '
                                                    'once.')
            else:
                user_bucket.append(user)
            if not User.query(User.user_name == user).get():
                raise endpoints.NotFoundException(
                    'A User with the name %s does not exist!'
                    % (user.replace("'", "''")))
        try:
            game = Game.new_game(request.users, request.dice_per_player,
                                 request.dice_sides, request.wild)
        except ValueError:
            # Change for wrong number of faces
            raise endpoints.BadRequestException('At least 1 die is needed to '
                                                'play.')
        return game.to_form('Good luck playing Pirate''s Dice!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.cancelled:
                return game.to_form('Game has been cancelled.')
            elif game.game_over:
                return game.to_form('Game is over. %s won.' %
                                    (game.winner.get().user_name))
            else:
                bidding_player = Player.query(
                    Player.game == game.key,
                    Player.order == (game.bid_player) % game.players + 1).get()
                return game.to_form('It\'s %s\'s turn!' %
                                    (bidding_player.user.get().user_name))
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_USER_GAMES_REQUEST,
                      response_message=GameForms,
                      path='games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns games for a specific user."""
        user = User.query(User.user_name == request.user_name).get()

        if user:
            if user.password != request.password:
                raise endpoints.UnauthorizedException(
                            'Invalid password!')

            user_plays = Player.query(Player.user == user.key)

            if user_plays:
                games = []
                for play in user_plays:
                    game = play.game.get()
                    if not game.game_over and not game.cancelled:
                        game_number = len(games)
                        games.append(
                            game.to_form('Game number %d.' % (game_number)))
                if len(games) != 0:
                    forms = GameForms()
                    forms.games = games
                    return forms
                else:
                    raise endpoints.NotFoundException(
                        'No active games found.')
            else:
                raise endpoints.NotFoundException('No games found.')
        else:
            raise endpoints.NotFoundException('User not found.')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancels a game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        # Maybe will add a drop feature instead someday to prevent rage quits.
        # Idea: would be a Player field
        if game:
            if game.game_over or game.cancelled:
                return game.to_form('Game already over!')
            else:
                game.cancelled = True
                game.put()
            return game.to_form('Game cancelled.')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=GET_DICE_REQUEST,
                      response_message=DiceForms,
                      path='dice/{urlsafe_game_key}',
                      name='get_dice',
                      http_method='GET')
    def get_dice(self, request):
        """Returns a player's dice."""
        # Can still use if game is over or cancelled for historical purposes
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        user = User.query(User.user_name == request.user_name).get()
        if game:
            player = Player.query(
                Player.game == game.key,
                Player.user == user.key)
            if user:
                if player:
                    if user.password != request.password:
                        raise endpoints.UnauthorizedException(
                            'Invalid password!')
                    else:
                        # For those using themselves to test
                        ids = []
                        for row in player:
                            ids.append(row.key)
                        dice = (Dice.query(Dice.player.IN(ids))
                                    .order(Dice.player).order(Dice.face))
                        return Dice.to_form(dice)
                else:
                    raise endpoints.NotFoundException('Player not found!')
            else:
                raise endpoints.NotFoundException(
                    'A User with the name %s does not exist!'
                    % (user.replace("'", "''")))
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=RAISE_BID_REQUEST,
                      response_message=GameForm,
                      path='bid/{urlsafe_game_key}',
                      name='raise_bid',
                      http_method='PUT')
    def raise_bid(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        # Validity logic
        if game.game_over or game.cancelled:
            return game.to_form('Game already over!')

        bidding_player = Player.query(
            Player.game == game.key,
            Player.order == game.bid_player % game.players + 1).get()

        bidding_user = bidding_player.user.get()

        if bidding_user.password != request.password:
            return game.to_form('Invalid password.')

        if (game.bid_face == game.die_faces and
                game.bid_total == game.dice_total * game.players):
            return game.to_form('Already at max possible bid. Bid cannot be '
                                'rasied. Call liar to end game.')

        if request.bid_face < 1 or request.bid_face > game.die_faces:
            return game.to_form('Invalid face number. Must be between 1 '
                                'and ' + str(game.die_faces) + '.')

        if request.bid_face < game.bid_face:
            return game.to_form('Invalid dice face. Must be greater than or '
                                'equal to the current dice face bid:%d.' %
                                (game.bid_face))

        if (request.bid_face == game.bid_face and
                request.bid_total <= game.bid_total):
            return game.to_form('Invalid bid. If not raising dice face, '
                                'must raise dice total')

        # Game logic
        game.bid_face = request.bid_face
        game.bid_total = request.bid_total
        game.turn += 1
        # Update player info
        if game.bid_player == game.players:
            game.bid_player = 1
        else:
            game.bid_player += 1
        game.put()

        # Record History
        game_history = GameHistory(game=game.key,
                                   turn=game.turn,
                                   player=bidding_player.key,
                                   bid_face=game.bid_face,
                                   bid_total=game.bid_total)
        game_history.put()

        # Find the next player
        next_player = Player.query(
            Player.game == game.key,
            Player.order == game.bid_player % game.players + 1).get()

        next_user = next_player.user.get()

        if next_user.email is not None:
            task_params = ({
                'email': next_user.email,
                'user_name': next_user.user_name,
                'game_key': game.key.urlsafe(),
                'dice': Dice.query(Dice.player == next_player.key)
                            .order(Dice.face),
                'bid_face': game.bid_face,
                'bid_total': game.bid_total,
                'bid_player': bidding_user.user_name})

            taskqueue.add(
                params=task_params,
                url='/tasks/send_your_turn'
            )

        return game.to_form('Current bid is now face: %d, number %d. It is '
                            '%s\'s turn.' % (request.bid_face,
                                             request.bid_total,
                                             next_user.user_name))

    @endpoints.method(request_message=CALL_LIAR_REQUEST,
                      response_message=GameForm,
                      path='liar/{urlsafe_game_key}',
                      name='call_liar',
                      http_method='PUT')
    def call_liar(self, request):
        """Returns a player's dice."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)

        # Validity logic
        if game.game_over or game.cancelled:
            return game.to_form('Game already over!')

        if game.turn < 1:
            return game.to_form(
                'At least one turn must pass before calling liar.')

        # Get players of interest
        bidding_player = Player.query(
            Player.game == game.key,
            Player.order == game.bid_player).get()

        bidding_user = bidding_player.user.get()

        calling_player = Player.query(
            Player.game == game.key,
            Player.order == game.bid_player % game.players + 1).get()

        calling_user = calling_player.user.get()

        if calling_user.password != request.password:
            return game.to_form('Invalid password.')

        # Game Logic
        game.game_over = True

        # Count dice and update score
        """ Technically, players can cheat by playing against themselves.
        Ignoring validity check in the meanwhile for testing purposes. """
        players = Player.query(Player.game == game.key)
        ids = []
        dice_total = 0
        for player in players:
            ids.append(player.key)
            # Dice logic
            dice = Dice.query(Dice.player.IN(ids))
            for die in dice:
                if die.face == game.bid_face:
                    dice_total += die.total

            # Score logic
            # Prevent score for being raised if playing against self
            if players.count() > 1:
                score_user = player.user.get()
                score = Score.query(Score.user == score_user.key).get()
                if score:
                    score.games += 1
                else:
                    score = Score(user=score_user.key,
                                  games=1,
                                  wins=0,
                                  score=0)
                score.put()

        message = ('For a face of %d: real total - %d, bid total - %d. ' %
                   (game.bid_face, dice_total, game.bid_total))
        if die.total < game.bid_total:
            winner = calling_user.key
            message += ('%s was lying! %s wins!' %
                        (bidding_user.user_name.replace("'", "''"),
                         calling_user.user_name.replace("'", "''")))
        else:
            winner = bidding_user.key
            message += ('%s was telling the truth! %s wins!' %
                        (bidding_user.user_name.replace("'", "''"),
                         bidding_user.user_name.replace("'", "''")))

        game.winner = winner

        # Add score to winner
        # Prevent score for being raised if playing against self
        if players.count() > 1:
            winner_score = Score.query(Score.user == game.winner).get()
            winner_score.wins += 1
            winner_score.score += game.turn

            winner_score.put()
        game.put()
        return game.to_form(message)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForms,
                      path='history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Returns the move history for a specified game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            game_history = (GameHistory.query(GameHistory.game == game.key)
                                       .order(GameHistory.turn))
            if game_history:
                return GameHistory.to_form(game_history)
            else:
                raise endpoints.NotFoundException(
                    'No bids have been raised for this game yet')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(response_message=ScoreForms,
                      path='rank',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns all players and their ranks."""
        # Create Score Forms
        # Can order app engine request
        scores = Score.query().order(-Score.score)
        forms = ScoreForms()
        forms.scores = []
        rank = 1
        if scores.count() > 0:
            for score in scores:
                forms.scores.append(score.to_form(rank))
                rank += 1
            return forms
        else:
            raise endpoints.NotFoundException('No scores recorded yet!')

api = endpoints.api_server([LiarsDiceApi])
