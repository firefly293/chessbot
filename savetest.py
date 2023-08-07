import chess


def saveBoard(chessBoard: chess.Board, filePath: str) -> None:
    file = open(filePath, "w")
    file.flush()
    for uci in [m.uci() for m in chessBoard.move_stack]:
        file.write(uci + ' ')
    file.write(str(False))

def loadBoard(filePath: str) -> chess.Board:
    file = open(filePath, "r")
    contents = file.read()
    loadedBoard = chess.Board()
    for uci in contents.split()[0:-1]:
        loadedBoard.push_uci(uci)
    return loadedBoard

board = chess.Board()

board.push_san('e4')
board.push_san('e5')
board.push_san('Nf3')
board.push_san('Nc6')

saveBoard(board, 'saves/board.txt')
newBoard = loadBoard('saves/board.txt')
print(newBoard)

