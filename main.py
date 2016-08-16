#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""

import webapp2
from google.appengine.api import mail, app_identity
from api import LiarsDiceApi

from models import User, Game, Player


class SendYourTurnEmail(webapp2.RequestHandler):
    def post(self):
        """Send a turn notification email to a user about the game.
        Called when a user completes a turn"""
        app_id = app_identity.get_application_id()
        subject = 'It''s your turn on Liar\'s Dice.'
        body = (
            'Hello {}, your opponent is waiting for your action in game {}.'
            .format(
                self.request.get('user_name'),
                self.request.get('game_key')))
        body += (
            "\n\n{} raised the bid to face: {}, total: {}. Is it a lie?"
            .format(
                self.request.get('bid_player'),
                self.request.get('bid_face'),
                self.request.get('bid_total')))
        # This will send test emails, the arguments to send_mail are:
        # from, to, subject, body
        mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                       self.request.get('email'),
                       subject,
                       body)


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every 24 hours using a cron job"""
        app_id = app_identity.get_application_id()
        # Step 1: Find all userrs
        users = User.query(User.email != None)
        for user in users:
            games = []
            # Step 2: Find player instances of that user
            player_instances = Player.query(Player.user == user.key)
            # Step 3: For each player intance find out if game is active
            # and if it's user's turn
            for player in player_instances:
                game = player.game.get()
                if (not game.game_over and not game.cancelled and 
                    (game.bid_player % game.players + 1 == player.order)):
                        games.append(game.key.urlsafe())
            if len(games) > 0:
                subject = 'Liar\'s Dice Reminder!'
                body = ('Hello {}, your opponents are waiting for you.'
                        .format(user.user_name))
                body += ('\nHere are your active games:')
                for game in games:
                    body += ('\n{}').format(game)
                body += ('\n\nYour password: {}').format(user.password)
                # This will send test emails, the arguments to send_mail are:
                # from, to, subject, body
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/send_your_turn', SendYourTurnEmail),
], debug=True)
