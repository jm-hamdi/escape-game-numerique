import random, pygame, sys, cv2
from pygame.locals import *
import mediapipe as mp

# =========================
# CONFIGURATION
# =========================
mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(0.5)
cap = cv2.VideoCapture(0)

neutral_x, neutral_y = None, None
move_cooldown = 0
random.seed(4242)

# Pygame
pygame.init()
window_resolution = 800, 600
window = pygame.display.set_mode(window_resolution)
score = 0
tile_size = 50
player_posx = player_posy = 0
border = (window_resolution[0] // tile_size,
          window_resolution[1] // tile_size)
goal_posx = border[0]-1
goal_posy = border[1]-1
player_pos = (player_posx, player_posy)
goal_pos = (goal_posx, goal_posy)
touched = []

# Afficher le labyrinthe ? y/n
show_maze = input("Voulez-vous afficher le labyrinthe ? y/n >>> ").lower() == "y"

# =========================
# LABYRINTHE RESOLVABLE
# =========================
maze_w, maze_h = border[0], border[1]
maze = [[{'visited': False, 'walls': {'up': True,'down':True,'left':True,'right':True}} 
         for _ in range(maze_h)] for _ in range(maze_w)]

def generate_maze_dfs(x=0, y=0):
    maze[x][y]['visited'] = True
    directions = ['up','down','left','right']
    random.shuffle(directions)
    for direction in directions:
        nx, ny = x, y
        if direction == 'up': ny -= 1
        elif direction == 'down': ny += 1
        elif direction == 'left': nx -= 1
        elif direction == 'right': nx += 1
        if 0 <= nx < maze_w and 0 <= ny < maze_h and not maze[nx][ny]['visited']:
            maze[x][y]['walls'][direction] = False
            opposite = {'up':'down','down':'up','left':'right','right':'left'}
            maze[nx][ny]['walls'][opposite[direction]] = False
            generate_maze_dfs(nx, ny)

generate_maze_dfs()

def is_wall(x, y, direction):
    if direction not in maze[x][y]['walls']: return True
    return maze[x][y]['walls'][direction]

def draw_maze():
    if not show_maze: return
    window.fill((0,0,0))
    for x in range(maze_w):
        for y in range(maze_h):
            rect_color = (50,200,200) if (x,y) in touched else (0,0,0)
            if (x,y) == (player_posx, player_posy):
                rect_color = (0,0,255)  # cube bleu
            elif (x,y) == (goal_posx, goal_posy):
                rect_color = (255,0,0)  # objectif rouge
            pygame.draw.rect(window, rect_color, (x*tile_size, y*tile_size, tile_size, tile_size))
            # murs
            walls = maze[x][y]['walls']
            if walls['right']:
                pygame.draw.line(window, (100,100,100), (x*tile_size + tile_size, y*tile_size), (x*tile_size + tile_size, y*tile_size + tile_size), 3)
            if walls['down']:
                pygame.draw.line(window, (100,100,100), (x*tile_size, y*tile_size + tile_size), (x*tile_size + tile_size, y*tile_size + tile_size), 3)
    pygame.display.update()

# =========================
# BOUCLE PRINCIPALE
# =========================
draw_maze()
while True:
    ret, frame = cap.read()
    if not ret: continue
    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_detector.process(frame_rgb)

    if result.detections:
        for detection in result.detections:
            bbox = detection.location_data.relative_bounding_box
            h, w, _ = frame.shape
            x = int(bbox.xmin * w + bbox.width * w / 2)
            y = int(bbox.ymin * h + bbox.height * h / 2)

            # Initialisation de la position neutre
            if neutral_x is None:
                neutral_x, neutral_y = x, y

            dx = x - neutral_x
            dy = y - neutral_y
            threshold = 30

            # Couleur du cadre autour du visage
            color = (0,0,255) if abs(dx)<=threshold and abs(dy)<=threshold else (0,255,0)
            x_min = int(bbox.xmin * w)
            y_min = int(bbox.ymin * h)
            box_width = int(bbox.width * w)
            box_height = int(bbox.height * h)
            cv2.rectangle(frame, (x_min, y_min), (x_min+box_width, y_min+box_height), color, 2)

            # Déplacement cube bleu avec cooldown
            move_cooldown += 1
            if move_cooldown > 5:
                if dx > threshold and not is_wall(player_posx, player_posy,'right'):
                    player_posx += 1
                elif dx < -threshold and not is_wall(player_posx, player_posy,'left'):
                    player_posx -= 1
                elif dy > threshold and not is_wall(player_posx, player_posy,'down'):
                    player_posy += 1
                elif dy < -threshold and not is_wall(player_posx, player_posy,'up'):
                    player_posy -= 1
                move_cooldown = 0

    player_pos = (player_posx, player_posy)
    if player_pos == (goal_posx, goal_posy):
        score += 1
        print(f"Score: {score}")
        player_posx = player_posy = 0
        player_pos = (0,0)

    draw_maze()
    cv2.imshow("Face Control", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC pour quitter
        break

    for event in pygame.event.get():
        if event.type == QUIT:
            cap.release()
            cv2.destroyAllWindows()
            pygame.quit()
            sys.exit()
