import random
import pygame
import sys
import cv2
import mediapipe as mp
from pygame.locals import *
import os
import tkinter as tk
from tkinter import messagebox

# =========================
# CONFIGURATION (modifiable)
# =========================
SEED = 10
tile_size_target = 50
player_image_path = "player.png"
show_maze = True

# =========================
# FONCTIONS AUXILIAIRES
# =========================

def demander_code_secret():
    def verifier_code():
        code = entry.get()
        if code == "E7":
            fenetre.destroy()
        else:
            messagebox.showerror("Erreur", "Code incorrect, réessayez.")
            entry.delete(0, tk.END)

    fenetre = tk.Tk()
    fenetre.title("Code secret")

    label = tk.Label(fenetre, text="Entrez le code secret pour démarrer :")
    label.pack(pady=10)

    entry = tk.Entry(fenetre, show="*")
    entry.pack(pady=5)

    bouton = tk.Button(fenetre, text="Valider", command=verifier_code)
    bouton.pack(pady=10)

    fenetre.mainloop()

def generate_maze_dfs():
    # Génère un labyrinthe avec DFS récursif sur la grille `maze`
    stack = []
    start_x, start_y = 0, 0
    maze[start_x][start_y]['visited'] = True
    stack.append((start_x, start_y))

    while stack:
        x, y = stack[-1]
        # collect neighbors that are inside grid and not visited
        neighbors = []
        if x > 0 and not maze[x - 1][y]['visited']:
            neighbors.append(('left', x - 1, y))
        if x < maze_w - 1 and not maze[x + 1][y]['visited']:
            neighbors.append(('right', x + 1, y))
        if y > 0 and not maze[x][y - 1]['visited']:
            neighbors.append(('up', x, y - 1))
        if y < maze_h - 1 and not maze[x][y + 1]['visited']:
            neighbors.append(('down', x, y + 1))

        if neighbors:
            direction, nx, ny = random.choice(neighbors)
            # remove wall between (x,y) and (nx,ny)
            if direction == 'left':
                maze[x][y]['walls']['left'] = False
                maze[nx][ny]['walls']['right'] = False
            elif direction == 'right':
                maze[x][y]['walls']['right'] = False
                maze[nx][ny]['walls']['left'] = False
            elif direction == 'up':
                maze[x][y]['walls']['up'] = False
                maze[nx][ny]['walls']['down'] = False
            elif direction == 'down':
                maze[x][y]['walls']['down'] = False
                maze[nx][ny]['walls']['up'] = False

            maze[nx][ny]['visited'] = True
            stack.append((nx, ny))
        else:
            stack.pop()

def is_wall(x, y, direction):
    # retourne True si le mouvement depuis (x,y) dans 'direction' est bloqué par un mur
    if x < 0 or x >= maze_w or y < 0 or y >= maze_h:
        return True
    # si la cellule a le mur approchant, c'est un mur
    if maze[x][y]['walls'].get(direction, True):
        return True
    # aussi vérifier la cellule voisine pour cohérence aux bords
    if direction == 'left':
        nx, ny = x - 1, y
        if nx < 0: return True
        return maze[nx][ny]['walls'].get('right', True)
    if direction == 'right':
        nx, ny = x + 1, y
        if nx >= maze_w: return True
        return maze[nx][ny]['walls'].get('left', True)
    if direction == 'up':
        nx, ny = x, y - 1
        if ny < 0: return True
        return maze[nx][ny]['walls'].get('down', True)
    if direction == 'down':
        nx, ny = x, y + 1
        if ny >= maze_h: return True
        return maze[nx][ny]['walls'].get('up', True)
    return True

def draw_maze(window):
    window.fill((0, 0, 0))
    if not show_maze:
        # draw player and goal only
        px = player_posx * tile_size
        py = player_posy * tile_size
        gx = goal_posx * tile_size
        gy = goal_posy * tile_size
        window.blit(player_image, (px, py))
        pygame.draw.rect(window, (255, 0, 0), (gx, gy, tile_size, tile_size))
        return

    wall_color = (255, 255, 255)
    cell_color = (30, 30, 30)
    goal_color = (255, 0, 0)

    for x in range(maze_w):
        for y in range(maze_h):
            cx = x * tile_size
            cy = y * tile_size
            # background cell
            pygame.draw.rect(window, cell_color, (cx, cy, tile_size, tile_size))
            walls = maze[x][y]['walls']
            half = 1
            if walls.get('up', True):
                pygame.draw.line(window, wall_color, (cx, cy), (cx + tile_size, cy), 2)
            if walls.get('down', True):
                pygame.draw.line(window, wall_color, (cx, cy + tile_size), (cx + tile_size, cy + tile_size), 2)
            if walls.get('left', True):
                pygame.draw.line(window, wall_color, (cx, cy), (cx, cy + tile_size), 2)
            if walls.get('right', True):
                pygame.draw.line(window, wall_color, (cx + tile_size, cy), (cx + tile_size, cy + tile_size), 2)

    # draw goal
    gx = goal_posx * tile_size
    gy = goal_posy * tile_size
    pygame.draw.rect(window, goal_color, (gx + 4, gy + 4, tile_size - 8, tile_size - 8))

    # draw player
    px = player_posx * tile_size
    py = player_posy * tile_size
    window.blit(player_image, (px, py))

# =========================
# INITIALISATIONS
# =========================
random.seed(SEED)
mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(0.5)
neutral_x, neutral_y = None, None
move_cooldown = 0
score = 0
player_posx = player_posy = 0
touched = []

# Initialisation de Pygame et calculs préliminaires
pygame.init()
info = pygame.display.Info()
screen_w, screen_h = info.current_w, info.current_h
ref_width = 400
ref_tile_count_x = max(1, ref_width // tile_size_target)
tile_size = max(8, screen_w // ref_tile_count_x)
border_x = screen_w // tile_size
border_y = screen_h // tile_size
goal_posx = border_x - 1
goal_posy = border_y - 1
player_pos = (player_posx, player_posy)
goal_pos = (goal_posx, goal_posy)

# Génération du labyrinthe
maze_w, maze_h = border_x, border_y
maze = [[{'visited': False, 'walls': {'up': True, 'down': True, 'left': True, 'right': True}}
         for _ in range(maze_h)] for _ in range(maze_w)]
generate_maze_dfs()

# =========================
# DEMANDE DU CODE SECRET (avec tkinter)
# =========================
demander_code_secret()

# =========================
# INITIALISATION DE LA FENETRE PYGAME (après le code secret)
# =========================
window = pygame.display.set_mode((screen_w, screen_h), pygame.FULLSCREEN)
pygame.display.set_caption("Maze Face Control (fullscreen)")

# =========================
# CHARGEMENT DES RESSOURCES (après la fenêtre Pygame)
# =========================
if os.path.exists(player_image_path):
    player_image = pygame.image.load(player_image_path).convert_alpha()
    player_image = pygame.transform.scale(player_image, (tile_size, tile_size))
else:
    player_image = pygame.Surface((tile_size, tile_size))
    player_image.fill((0, 0, 255))

# =========================
# INITIALISATION DE LA CAMERA
# =========================
cap = cv2.VideoCapture(0)

# =========================
# BOUCLE PRINCIPALE
# =========================
clock = pygame.time.Clock()
running = True

while running:
    ret, frame = cap.read()
    if not ret:
        break

    # Traitement Mediapipe
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_detector.process(frame_rgb)
    if result.detections:
        for detection in result.detections:
            bbox = detection.location_data.relative_bounding_box
            h, w, _ = frame.shape
            x = int(bbox.xmin * w + bbox.width * w / 2)
            y = int(bbox.ymin * h + bbox.height * h / 2)
            if neutral_x is None:
                neutral_x, neutral_y = x, y
            dx = x - neutral_x
            dy = y - neutral_y
            threshold = 35
            color = (0, 0, 255) if abs(dx) <= threshold and abs(dy) <= threshold else (0, 255, 0)
            x_min = int(bbox.xmin * w)
            y_min = int(bbox.ymin * h)
            box_width = int(bbox.width * w)
            box_height = int(bbox.height * h)
            cv2.rectangle(frame, (x_min, y_min), (x_min + box_width, y_min + box_height), color, 4)
            move_cooldown += 1
            if move_cooldown > 10:
                moved = False
                if dx > threshold and not is_wall(player_posx, player_posy, 'right'):
                    player_posx = min(player_posx + 1, maze_w - 1)
                    moved = True
                elif dx < -threshold and not is_wall(player_posx, player_posy, 'left'):
                    player_posx = max(player_posx - 1, 0)
                    moved = True
                elif dy > threshold and not is_wall(player_posx, player_posy, 'down'):
                    player_posy = min(player_posy + 1, maze_h - 1)
                    moved = True
                elif dy < -threshold and not is_wall(player_posx, player_posy, 'up'):
                    player_posy = max(player_posy - 1, 0)
                    moved = True
                if moved:
                    # keep player inside bounds (safety)
                    player_posx = max(0, min(player_posx, maze_w - 1))
                    player_posy = max(0, min(player_posy, maze_h - 1))
                move_cooldown = 0

    player_pos = (player_posx, player_posy)
    if player_pos == (goal_posx, goal_posy):
        score += 1
        print(f"Score: {score}")
        player_posx = player_posy = 0

    # Dessin Pygame
    draw_maze(window)
    pygame.display.flip()

    # Affichage OpenCV
    cv2.imshow("Face Control", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        running = False

    # Événements Pygame
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                running = False
            elif event.key == K_r:
                random.seed(SEED)
                for x in range(maze_w):
                    for y in range(maze_h):
                        maze[x][y] = {'visited': False, 'walls': {'up': True, 'down': True, 'left': True, 'right': True}}
                generate_maze_dfs()
                player_posx = player_posy = 0

    clock.tick(30)

# Nettoyage
cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()
