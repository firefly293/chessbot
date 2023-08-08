# imports
import io
import os
import random
from typing import List

import cairosvg
import chess
import chess.svg
import discord
from discord import app_commands

#import pickle

# secrets
TOKEN_0 = 0
TOKEN_1 = 1
with (open('secrets.save', "r") as secrets):
    lines = secrets.readlines()
    token = lines[TOKEN_1]



# variables
class customMember:
    def __init__(self, id: int, display_name: str, name: str):
        self.id = id
        self.display_name = display_name
        self.name = name
        self.mention = "<@" + str(id) + ">"
    def fromMember(member: discord.Member):
        return customMember(member.id, member.display_name, member.name)

class Game:
    def __init__(self, white_user: customMember, black_user: customMember):
        self.board = chess.Board()
        self.whiteUser = white_user
        self.blackUser = black_user
        self.whiteOfferedDraw = False
        self.blackOfferedDraw = False
        self.takebackReqested = False
class Challenge:
    def __init__(self, challenger_user: customMember, challenged_user: customMember, colorStr: str):
        self.challenger = challenger_user
        self.challenged = challenged_user
        self.color = colorStr
    def createGame(self):
        if (self.color == "r"):
            # pick random between "w" and "b"
            self.color = random.choice(["w", "b"])

        if (self.color == "w"):
            game = Game(self.challenger, self.challenged)
            globalGames.append(game)
            return len(globalGames) - 1
        else:
            game = Game(self.challenged, self.challenger)
            globalGames.append(game)
            return len(globalGames) - 1


global globalGames
global globalChallenges
globalGames:List[Game] = []
globalChallenges:List[Challenge] = []

# set up client
intents = discord.Intents().all()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# commands
@tree.command(name = "move", description="Play your move!")
@app_commands.describe(move="The move to play in SAN (e.g. Nf3) or UCI (e.g. g1f3) notation.")
@app_commands.rename(move='move')
async def move(interaction: discord.Interaction, move: str):
    await interaction.response.defer()
    
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))

    if (inGame and isTurn):
        # get the legal moves
        valid_moves = [m.uci() for m in globalGames[gameIndex].board.legal_moves]
        valid_san_moves = [globalGames[gameIndex].board.san(chess.Move.from_uci(uci_move)) for uci_move in valid_moves]

        # check if move is in legal moves
        if (move in valid_san_moves or move in valid_moves):
            globalGames[gameIndex].board.push_san(move)
            globalGames[gameIndex].takebackReqested = False
            gameStatus = statusCheck(globalGames[gameIndex].board)
            currentTurnUser = None
            if (globalGames[gameIndex].board.turn == chess.WHITE):
                currentTurnUser = globalGames[gameIndex].whiteUser
            else:
                currentTurnUser = globalGames[gameIndex].blackUser
            message = ""
            if (gameStatus == "w"):
                message = f"{globalGames[gameIndex].whiteUser.mention} has defeated {globalGames[gameIndex].blackUser.mention} by checkmate!"
            elif (gameStatus == "b"):
                message = f"{globalGames[gameIndex].blackUser.nention} defeated {globalGames[gameIndex].whiteUser.mention} by checkmate!"
            elif (gameStatus == "ds"):
                message = f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by stalemate."
            elif (gameStatus == "di"):
                message = f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by insufficient material."
            elif (gameStatus == "d75"):
                message = f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by 75 move rule."
            elif (gameStatus == "d5r"):
                message = f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by fivefold repetition."
            elif (gameStatus == "c"):
                message = f"Your move has been played. It's your move now, {currentTurnUser.mention}. Check!"
            else:
                message = f"Your move has been played. It's your move now, {currentTurnUser.mention}."
            boardPNG = await getBoardPNG(globalGames[gameIndex].board, globalGames[gameIndex].board.peek())
            await interaction.followup.send(f"{message} Here is the updated state of the board:",
                                            file=boardPNG)
            if (gameStatus != "c" and gameStatus != "none"): # if its not check and it has a special status, it means the game is done
                await endGame(interaction, gameIndex)
                return
        else:
            await interaction.followup.send(f"'{move}' is an invalid move. Please play a legal move.")
            return
    else:
        if (inGame and not isTurn):
            await interaction.followup.send(f"It's not your turn to play.")
            return
        await interaction.followup.send(f"You are not currently playing a game.")

@tree.command(name = "resign", description="Resign the game.")
async def resign(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))
    if (inGame):
        opponent = getOpponent(gameIndex, interaction.user)
        await interaction.followup.send(f"{opponent.mention} has defeated {interaction.user.mention} by resignation.")
        await endGame(interaction, gameIndex)
        return
    else:
        await interaction.followup.send("You are not currently playing a game.")

@tree.command(name="draw", description="Offer a draw to the other player.")
async def draw(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))
    if (inGame):
        if (interaction.user.id == globalGames[gameIndex].whiteUser.id):
            # the current player is white
            if (globalGames[gameIndex].whiteOfferedDraw):
                await interaction.followup.send("You already offered a draw.")
                return
            elif (globalGames[gameIndex].blackOfferedDraw):
                await interaction.followup.send(f"{globalGames[gameIndex].blackUser.display_name} has already offered you a draw. Use /acceptdraw if you want to accept it.")
                return
            else:
                globalGames[gameIndex].whiteOfferedDraw = True
                await interaction.followup.send(f"{globalGames[gameIndex].blackUser.mention}, {interaction.user.display_name} has offered a draw. Use /acceptdraw or /declinedraw to respond.")
                return
        else:
            # the current player is black
            if (globalGames[gameIndex].blackOfferedDraw):
                await interaction.followup.send("You already offered a draw.")
                return
            elif (globalGames[gameIndex].whiteOfferedDraw):
                await interaction.followup.send(f"{globalGames[gameIndex].whiteUser.display_name} has already offered you a draw. Use /acceptdraw if you want to accept it.")
                return
            else:
                globalGames[gameIndex].blackOfferedDraw = True
                await interaction.followup.send(f"{globalGames[gameIndex].whiteUser.mention}, {interaction.user.display_name} has offered a draw. Use /acceptdraw or /declinedraw to respond.")
                return
    else:
        await interaction.followup.send("You are not currently playing a game.")

@tree.command(name="acceptdraw", description="Accept the draw offer.")
async def acceptdraw(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))
    if (inGame):
        if (interaction.user.id == globalGames[gameIndex].whiteUser.id):
            # the current player is white
            if (globalGames[gameIndex].blackOfferedDraw):
                await interaction.followup.send(f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by agreement.")
                await endGame(interaction, gameIndex)
                return
            else:
                await interaction.followup.send(f"{globalGames[gameIndex].blackUser.display_name} has not offered you a draw.")
        else:
            # the current player is black
            if (globalGames[gameIndex].whiteOfferedDraw):
                await interaction.followup.send(f"The game between {globalGames[gameIndex].whiteUser.mention} and {globalGames[gameIndex].blackUser.mention} is a draw by agreement.")
                await endGame(interaction, gameIndex)
                return
            else:
                await interaction.followup.send(f"{globalGames[gameIndex].whiteUser.display_name} has not offered you a draw.")
    else:
        await interaction.followup.send("You are not currently playing a game.")

@tree.command(name = "declinedraw", description="Decline the draw offer.")
async def declinedraw(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))
    print(inGame, gameIndex)
    if (inGame):
        if (interaction.user.id == globalGames[gameIndex].whiteUser.id):
            # the current player is white
            if (globalGames[gameIndex].blackOfferedDraw):
                await interaction.followup.send(f"You declined {globalGames[gameIndex].blackUser.mention}'s draw offer.")
                globalGames[gameIndex].blackOfferedDraw = False
                return
            else:
                await interaction.followup.send(f"{globalGames[gameIndex].blackUser.display_name} has not offered you a draw.")
                return
        else:
            # the current player is black
            if (globalGames[gameIndex].whiteOfferedDraw):
                await interaction.followup.send(f"You declined {globalGames[gameIndex].whiteUser.mention}'s draw offer.")
                globalGames[gameIndex].whiteOfferedDraw = False
                return
            else:
                await interaction.followup.send(f"{globalGames[gameIndex].whiteUser.display_name} has not offered you a draw.")
                return
    else:
        await interaction.followup.send("You are not currently playing a game.")

@tree.command(name="takeback", description="Request to take back your move.")
async def takeback(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn = getGame(customMember.fromMember(interaction.user))
    if (inGame):
        if (not globalGames[gameIndex].takebackReqested):
            if (not (len(globalGames[gameIndex].board.move_stack) == 0)):
                if (not isTurn):
                    await interaction.followup.send(f"{getOpponent(gameIndex, interaction.user).mention}, {interaction.user.name} wants to take back their move. Use /accepttakeback to accept it or play your next move to decline it.")
                    globalGames[gameIndex].takebackReqested = True
                else:
                    await interaction.followup.send("The last move in the game was not yours, so you cannot request a takeback.")
            else:
                await interaction.followup.send("There are no moves to take back.")
        else:
            await interaction.followup.send("You have already requested a takeback.")
    else:
        await interaction.followup.send("You are not currently playing a game.")

@tree.command(name="accepttakeback", description="Accept a takeback request.")
async def accepttakeback(interaction: discord.Interaction):
    await interaction.response.defer()
    gameIndex, inGame, isTurn =  getGame(customMember.fromMember(interaction.user))
    if (inGame):
        if (isTurn):
            # check if takeback was requested
            if (globalGames[gameIndex].takebackReqested):
                globalGames[gameIndex].board.pop()
                globalGames[gameIndex].takebackReqested = False
                boardPNG = None
                if (len(globalGames[gameIndex].board.move_stack) == 0):
                    boardPNG = await getBoardPNG(globalGames[gameIndex].board, orientation=globalGames[gameIndex].board.turn)
                else:
                    boardPNG = await getBoardPNG(globalGames[gameIndex].board, lastMove=globalGames[gameIndex].board.peek(), orientation=globalGames[gameIndex].board.turn)
                await interaction.followup.send(f"Takeback was accepted. It's your move, {getOpponent(gameIndex, interaction.user).mention}. Here is the current state of the board:", file=boardPNG)
            else:
                await interaction.followup.send(f"{getOpponent(gameIndex, interaction.user).display_name} has not requested a takeback.")
        else:
            await interaction.followup.send(f"{getOpponent(gameIndex, interaction.user).display_name} has not requested a takeback.")
    else:
        await interaction.followup.send("You are not currently in playing a game.")


@tree.command(name = "challenge", description="Create a new challenge!")
@app_commands.describe(user="The user that you want to challenge.", color="'w' for white, 'b' for black, 'r' for random color")
@app_commands.rename(user='user', color='color')
async def challenge(interaction: discord.Interaction, user: discord.Member, color: str):
    await interaction.response.defer()
    
    if (color.lower() != "w" and color.lower() != "b" and color.lower() != "r"):
        # invalid color
        await interaction.followup.send(f"Invalid color selection '{color}' provided. Please use either 'w', 'b', or 'r'")
        return
    
    # get user ids
    challengerID = interaction.user.id
    challengedID = user.id

    for challenge in globalChallenges:
        # check if same challenge already exists
        if (challenge.challenger.id == challengerID and challenge.challenged.id == challengedID):
            await interaction.followup.send("You have already challenged this person. Please wait until they accept/decline your challenge to challenge them again.")
            return

    # create the challenge
    challenge = Challenge(customMember.fromMember(interaction.user), customMember.fromMember(user), color)
    globalChallenges.append(challenge)

    colorString = ""
    if (color == "w"):
        colorString = "white"
    elif (color == "b"):
        colorString = "black"
    else:
        colorString = "a random color"

    await interaction.followup.send(f"{user.mention}, {interaction.user.display_name} has challenged you to a game of chess where they are {colorString}. Use /accept and /decline to respond.")

@tree.command(name = "accept", description="Accept a challenge.")
@app_commands.describe(user="The user who's challenge you want to accept.")
@app_commands.rename(user='user')
async def accept(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()

    # make sure neither player is in a game
    if (isInGame(customMember.fromMember(interaction.user)) or isInGame(customMember.fromMember(user))):
        await interaction.followup.send(f"Either you or {user.display_name} is already in a game.")
        return

    # find the challenge
    for challenge in globalChallenges:
        if (challenge.challenger.id == user.id and challenge.challenged.id == interaction.user.id):
            game = globalGames[challenge.createGame()]
            globalChallenges.remove(challenge)
            boardPNG = await getBoardPNG(game.board)
            await interaction.followup.send(f"New game started between {game.whiteUser.mention} (white) and {game.blackUser.mention} (black). It's your move, {game.whiteUser.mention}. Here is the starting position:", 
                                            file=boardPNG)
            return
    await interaction.followup.send(f"{user.display_name} hasn't challenged you.")
            
@tree.command(name = "decline", description="Decline a challenge.")
@app_commands.describe(user = "The user who's challenge you want to decline.")
@app_commands.rename(user = 'user')
async def decline(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()
    # find the challenge
    for challenge in globalChallenges:
        if (challenge.challenger.id == user.id and challenge.challenged.id == interaction.user.id):
            globalChallenges.remove(challenge)
            await interaction.followup.send(f"Challenge between you and {user.mention} has been declined.")
            return
    await interaction.followup.send(f"No challenge exists between you and {user.display_name}")


@tree.command(name = "displayboard", description="Display the current state of the board.")
async def displayboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    gameIndex, isGame, isTurn = getGame(customMember.fromMember(interaction.user))

    if (isGame):
        boardPNG = None
        if (interaction.user.id == globalGames[gameIndex].whiteUser.id):
            # the current player is white
            if (len(globalGames[gameIndex].board.move_stack) > 0):
                boardPNG = await getBoardPNG(globalGames[gameIndex].board, globalGames[gameIndex].board.peek(), chess.WHITE)
            else:
                boardPNG = await getBoardPNG(globalGames[gameIndex].board, orientation=chess.WHITE)
            await interaction.followup.send("Current state of the board:", file=boardPNG)
            return
        else:
            # the current player is black
            # the current player is white
            if (len(globalGames[gameIndex].board.move_stack) > 0):
                boardPNG = await getBoardPNG(globalGames[gameIndex].board, globalGames[gameIndex].board.peek(), chess.BLACK)
            else:
                boardPNG = await getBoardPNG(globalGames[gameIndex].board, orientation=chess.BLACK)
            await interaction.followup.send("Current state of the board:", file=boardPNG)
            return
    else:
        await interaction.followup.send("You are not currently playing a game")

@client.event
async def on_ready():
    commands = await tree.sync()
    print([i.name for i in commands])
    print(f'Logged in as {client.user.name}')



# @client.event
# async def on_disconnect():
#     # pickle games and challenges
#     pickle.dump(games, open("pickles/games.p", "wb"))
#     pickle.dump(challenges, open("pickles/challenges.p", "wb"))
#     print("disconnected")

# methods
async def getBoardPNG(chessBoard: chess.Board, lastMove: chess.Move = chess.Move.null(), orientation: chess.Color = None):
    # Generate SVG content
    svg_board = None
    if (orientation is None):
        svg_board = chess.svg.board(board=chessBoard, orientation=chessBoard.turn, lastmove=lastMove)
    else:
        svg_board = chess.svg.board(board=chessBoard, orientation=orientation, lastmove=lastMove)
        
    # Convert SVG to PNG
    png_bytes = cairosvg.svg2png(bytestring=svg_board.encode('utf-8'))
        
    # Create an in-memory file-like object
    png_io = io.BytesIO(png_bytes)
        
    # Create a `discord.File` object from the in-memory object
    file = discord.File(png_io, filename='chess_board.png')

    return file


def statusCheck(chessBoard: chess.Board):
    if chessBoard.is_checkmate():
        if chessBoard.turn == chess.WHITE:
            return "b"
        else:
            return "w"
    elif chessBoard.is_stalemate():
        return "ds"
    elif chessBoard.is_insufficient_material():
        return "di"
    elif chessBoard.is_seventyfive_moves():
        return "d75"
    elif chessBoard.is_fivefold_repetition():
        return "d5r"
    elif chessBoard.is_check():
        return "c"
    else:
        return "none"

def isInGame(user: customMember):
    for game in globalGames:
        if (game.whiteUser.id == user.id or game.blackUser.id == user.id):
            return True
    return False

def getGame(user: customMember):
    gameIndex = -1
    inGame = False
    isTurn = False
    # find the game
    for game in globalGames:
        # check if they are white
        if (game.whiteUser.id == user.id):
            inGame = True
            if (game.board.turn == chess.WHITE):
                isTurn = True
                gameIndex = globalGames.index(game)
                break
        if (game.blackUser.id == user.id):
            inGame = True
            if (game.board.turn == chess.BLACK):
                isTurn = True
                gameIndex = globalGames.index(game)
                break
        if (inGame):
            break
    return gameIndex, inGame, isTurn

def getOpponent(gameIndex: int, user: discord.Member):
    if (globalGames[gameIndex].whiteUser.id == user.id):
        return globalGames[gameIndex].blackUser
    return globalGames[gameIndex].whiteUser

async def endGame(interaction: discord.Interaction, gameIndex: int):
    globalGames.remove(globalGames[gameIndex])
    await interaction.followup.send("The game has ended.")

def encodeGame(game: Game) -> str:
    gamestr = ""
    # save the board
    gamestr += str(len(game.board.move_stack)) + ' '
    for uci in [m.uci() for m in game.board.move_stack]:
        gamestr += uci + ' '
    # save whiteUser
    gamestr += str(game.whiteUser.id) + ' '
    gamestr += game.whiteUser.display_name + ' '
    gamestr += game.whiteUser.name + ' '
    # save blackUser
    gamestr += str(game.blackUser.id) + ' '
    gamestr += game.blackUser.display_name + ' '
    gamestr += game.blackUser.name + ' '
    # save whiteOfferedDraw
    gamestr += str(game.whiteOfferedDraw) + ' '
    # save blackOfferedDraw
    gamestr += str(game.blackOfferedDraw) + ' '
    # save takebackRequest
    gamestr += str(game.takebackReqested)

    return gamestr

def decodeGame(gamestr: str) -> Game:
    board = chess.Board()
    whiteUser = None
    blackUser = None
    whiteOfferedDraw = False
    blackOfferedDraw = False


    tokens = gamestr.split()
    nMoves = None
    tokenCount = 0
    
    # board
    nMoves = int(tokens[tokenCount])
    tokenCount += 1
    for moveNumber in range(nMoves):
        board.push_uci(tokens[tokenCount])
        tokenCount += 1
    # whiteUser
    whiteUserID = int(tokens[tokenCount])
    print(whiteUserID)
    tokenCount += 1
    whiteUserDisplayName = tokens[tokenCount]
    print(whiteUserDisplayName)
    tokenCount += 1
    whiteUserName = tokens[tokenCount]
    print(whiteUserName)
    tokenCount += 1
    whiteUser = customMember(whiteUserID, whiteUserDisplayName, whiteUserName)
    # blackUser
    blackUserID = int(tokens[tokenCount])
    tokenCount += 1
    blackUserDisplayName = tokens[tokenCount]
    tokenCount += 1
    blackUserName = tokens[tokenCount]
    tokenCount += 1
    blackUser = customMember(blackUserID, blackUserDisplayName, blackUserName)
    # whiteOfferedDraw
    whiteOfferedDraw = (tokens[tokenCount] == "True")
    tokenCount += 1
    # blackOfferedDraw
    blackOfferedDraw = (tokens[tokenCount] == "True")
    tokenCount += 1
    # takebackRequested
    takebackRequested = (tokens[tokenCount] == "True")
    tokenCount += 1

    game = Game(whiteUser, blackUser)
    game.board = board
    game.whiteOfferedDraw = whiteOfferedDraw
    game.blackOfferedDraw = blackOfferedDraw
    game.takebackReqested = takebackRequested
    return game

def saveGames(gameList: List[Game], filePath: str) -> None:
    file = open(filePath, "w")
    file.flush()
    lines = []
    for game in gameList:
        gamestr = encodeGame(game)
        lines.append(gamestr)
    file.writelines(lines)

def loadGames(filePath: str) -> List[Game]:
    file = open(filePath, "r")
    gameList: List[Game] = []
    lines = file.readlines()
    print(lines)
    for line in lines:
        game = decodeGame(line)
        print(game.board, game.whiteUser.name, game.blackUser.name, game.whiteOfferedDraw, game.blackOfferedDraw)
        gameList.append(game)
    return gameList


def encodeChallenge(challenge: Challenge) -> str:
    challengestr = ""

    # challenger
    challengestr += str(challenge.challenger.id) + ' '
    challengestr += challenge.challenger.display_name + ' '
    challengestr += challenge.challenger.name + ' '
    # challenged
    challengestr += str(challenge.challenged.id) + ' '
    challengestr += challenge.challenged.display_name + ' '
    challengestr += challenge.challenged.name + ' '
    # color
    challengestr += challenge.color

    return challengestr

def decodeChallenge(challengestr: str) -> Challenge:
    challenger = None
    challenged = None
    color = None

    tokens = challengestr.split()
    challenger = customMember(int(tokens[0]), tokens[1], tokens[2])
    challenged = customMember(int(tokens[3]), tokens[4], tokens[5])
    color = tokens[2]

    challenge = Challenge(challenger, challenged, color)
    return challenge

def saveChallenges(challengeList: List[Challenge], filePath: str) -> None:
    file = open(filePath, "w")
    file.flush()
    lines = []
    for challenge in challengeList:
        challengestr = encodeChallenge(challenge)
        lines.append(challengestr)
    file.writelines(lines)

def loadChallenges(filePath: str) -> List[Challenge]:
    file = open(filePath, "r")
    challengeList: List[Challenge] = []
    lines = file.readlines()
    for line in lines:
        challenge = decodeChallenge(line)
        print(challenge.challenger.name, challenge.challenged.name, challenge.color)
        challengeList.append(challenge)
    return challengeList





if (os.path.isfile("saves/games.save")):
    if (os.path.getsize("saves/games.save") != 0):
        # load the games
        globalGames = loadGames('saves/games.save')
        print("loaded games")
if (os.path.isfile("saves/challenges.txt")):
    if (os.path.getsize("saves/challenges.txt") != 0):
        globalChallenges = loadChallenges("saves/challenges.save")
        print("loaded challenges")


client.run(token)

print('disconnected')
if (len(globalGames) > 0):
    saveGames(globalGames, "saves/games.save")
    print("saved games")
else:
    with (open("saves/games.save", "w") as file):
        file.truncate(0)
if (len(globalChallenges) > 0):
    saveChallenges(globalChallenges, "saves/challenges.save")
    print("saved challenges")
else:
    with (open("saves/challenges.save", "w") as file):
        file.truncate(0)
