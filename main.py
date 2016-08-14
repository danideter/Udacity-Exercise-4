#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging

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
        games = Game.query(Game.game_over == False, Game.cancelled == False)
        for game in games:
            player = Player.query(
                Player.game == game.key,
                Player.order == game.bid_player % game.players + 1).get()

            user = player.user.get()
            if user.email is not None:
                subject = 'Liar\'s Dice Reminder!'
                body = ('Hello {}, your oppoents are waiting in game {}.'
                        .format(user.user_name, game.key.urlsafe()))
                body += '\n\nYour password: {}'.format(user.password)
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
