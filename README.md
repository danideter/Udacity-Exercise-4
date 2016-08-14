#Full Stack Nanodegree Project 4 Refresh
## Liar's Dice Edition

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
2.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
3.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 
 
 
##Game Description:
Pirate's dice is a game of analyzing and bluffing. It's deceptively simple.
Each player rolls the same number of dice in a cup. Then, players take turns
guessing how many dice share the same face value, but there are two catches:
1.  Guesses must always be increasing in face value or totals
2.  Players can flat out lie.
On a player's turn, he or she can call the previous person a liar. If the caller
is correct, he or she wins. If not, the bidding player wins.

An example game between two players may go as follows:

Dice 3, Faces 4, 1's are Wild 

Bids

Player 1 - face 1, total 1

Player 2 - face 1, total 3

Player 1 - face 2, total 2

Player 2 - face 4, total 1

Player 1 - face 4, total 3

Player 2 - face 4, total 4

Player 1 - Call Liar

Results

2 Dice with face of 4 and 2 Dice with face of 1

Dice Total = 4

Player 2 was telling the truth! Player 2 wins!

##Scoring:
When a game is completed, the total number of turns is added to the player's 
alltime score. This means games that have more players and dice that tend to
last longer are worth more score points. Of course, that also means players
must keep playing if they want to have the top score!


A version of the game has been deployed to piratesdicegame.appspot.com

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Handler for taskqueue handler.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional), password (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists. A user
    can provide a password to protect turns and move order.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: users, dice_per_player (default=6), dice_sides (default=5), wild (default=1)
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. users provided must correspond to
    existing users - will raise a NotFoundException if not. If no wild face
    desired, set to 0.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **cancel_game**
    - Path: 'cancel/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with cancelled game state.
    - Description: Cancels a game and returns the game state as confirmation.

 - **get_dice**
    - Path: 'dice/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key, user_name, password
    - Returns: DiceForms.
    - Description: Gets a user's dice to help aid in bluff making and callinf.

 - **raise_bid**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, bid_face, bid_total, password
    - Returns: GameForm with new game state.
    - Description: Accepts a 'bid_face' and 'bid_total' to return the updated state of the game.
    Only accepts a valid bid. A valid bid either raises the 'bid_face' or keeps the 'bid_face'
    the same and raises the 'bid_total'. If the current bid player provided a 'password', it
    must be provided to accept the bid.
    
 - **call_liar**
    - Path: 'liar/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key, password
    - Returns: GameForm with end game state.
    - Description: Ends the game and determines a winner by calculating the true dice total
    by comparing it to the bid total.
    
 - **get_user_rankings**
    - Path: 'rank'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms. 
    - Description: Returns all the user scores ordered to show off top players. Users are
    ranked by the total turns completed in games they've won.
    
 - **get_game_history**
    - Path: 'history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForms
    - Description: Returns all the actions players have taken in a turn. Useful to see if
    someone is bluffing.

##Models Included:
 - **User**
    - Stores unique user_name, (optional) password, and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.

 - **Player**
    - Stores users and their and provides a link for fice to games.
    - Associated with Game model via KeyProperty.

 - **Dice**
    - Stores a player's dice in a game.
    - Associated with Game model via KeyProperty.

 - **Score**
    - Records user scores based on completed games. 
    - Associated with Users model via KeyProperty.

 - **GameHistory**
    - Records completed turns. Associated with Game model via KeyProperty.

##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, players, die_faces
    dice_total, winner, game_over, cancelled, turn, message, bid_player,
    bid_face, bid_total).
 - **GameForms**
    - Multiple GameForm container.
 - **NewGameForm**
    - Used to create a new game (users, min, max, attempts)
 - **RaiseBidForm**
    - Inbound raise bid form (bid_face, bid_total, password).
 - **DiceForm**
    - Outbound to show player his or her dice (player, face, total).
 - **DiceForms**
    - Multiple DiceForm container.
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, dice_per_player,
    dice_sides, wild).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **GameHistoryForm**
    - Used to display game turn history (turn, user_name, bid_face, bid_total)
 - **GameHistoryForms**
    - Multiple GameHistoryForm container.