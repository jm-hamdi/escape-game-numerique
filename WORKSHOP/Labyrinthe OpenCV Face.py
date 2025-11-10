import random
import pygame
import sys
import cv2
import mediapipe as mp
from pygame.locals import *
import os

# =========================
# CONFIGURATION (modifiable)
# =========================
SEED = 10         # <-- changez cette valeur pour obtenir un autre labyrinthe reproduisible
tile_size_target = 50   # taille de tuile cible (sera ajustée pour fullscreen)
player_image_path = "player.png"  # chemin vers l'image du joueur
show_maze = True        # True pour afficher le labyrinthe

# =========================
# INITIALISATIONS
# =========================
random.seed(SEED)

mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(0.5)
cap = cv2.VideoCapture(0)

neutral_x, neutral_y = None, None
move_cooldown = 0
score = 0
player_posx = player_posy = 0
touched = []

pygame.init()

# Demander le mode plein écran puis récupérer la résolution réelle
info = pygame.display.Info()
screen_w, screen_h = info.current_w, info.current_h
# Créer la fenêtre en plein écran
window = pygame.display.set_mode((screen_w, screen_h), pygame.FULLSCREEN)
pygame.display.set_caption("Maze Face Control (fullscreen)")

# Calculer tile_size pour garder la même "longueur" (nombre de tuiles horizontales similaire)
# On considère "longueur" = largeur visible en tiles pour l'ancienne résolution 400x300
# Ancienne largeur en tiles = 400 / tile_size_target. On conserve ce nombre de tiles horizontales.
ref_width = 400
ref_tile_count_x = max(1, ref_width // tile_size_target)
tile_size = max(8, screen_w // ref_tile_count_x)  # au moins 8 px par tuile

# Calculer le nombre de tuiles en x/y (border)
border_x = screen_w // tile_size
border_y = screen_h // tile_size

goal_posx = border_x - 1
goal_posy = border_y - 1
player_pos = (player_posx, player_posy)
goal_pos = (goal_posx, goal_posy)

# Charger l'image du joueur (fallback si absent : surface rect)
if os.path.exists(player_image_path):
    player_image = pygame.image.load(player_image_path).convert_alpha()
    player_image = pygame.transform.scale(player_image, (tile_size, tile_size))
else:
    player_image = pygame.Surface((tile_size, tile_size))
    player_image.fill((0, 0, 255))  # bleu si pas d'image

# =========================
# MAZE: initialisation et génération (DFS)
# =========================
maze_w, maze_h = border_x, border_y
maze = [[{'visited': False, 'walls': {'up': True, 'down': True, 'left': True, 'right': True}}
         for _ in range(maze_h)] for _ in range(maze_w)]

def generate_maze_dfs(x=0, y=0):
    maze[x][y]['visited'] = True
    directions = ['up', 'down', 'left', 'right']
    random.shuffle(directions)
    for direction in directions:
        nx, ny = x, y
        if direction == 'up': ny -= 1
        elif direction == 'down': ny += 1
        elif direction == 'left': nx -= 1
        elif direction == 'right': nx += 1
        if 0 <= nx < maze_w and 0 <= ny < maze_h and not maze[nx][ny]['visited']:
            maze[x][y]['walls'][direction] = False
            opposite = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
            maze[nx][ny]['walls'][opposite[direction]] = False
            generate_maze_dfs(nx, ny)

generate_maze_dfs()

def is_wall(x, y, direction):
    if not (0 <= x < maze_w and 0 <= y < maze_h):
        return True
    return direction not in maze[x][y]['walls'] or maze[x][y]['walls'][direction]

# =========================
# DESSIN
# =========================
def draw_maze(surface):
    if not show_maze:
        # dessiner uniquement le joueur sur fond
        surface.blit(player_image, (player_posx * tile_size, player_posy * tile_size))
        return

    # fond (changer ici la couleur si besoin)
    surface.fill((30, 30, 30))  # foncé
    for x in range(maze_w):
        for y in range(maze_h):
            rect_color = (50, 200, 200) if (x, y) in touched else (0, 0, 0)
            if (x, y) == (goal_posx, goal_posy):
                rect_color = (255, 0, 0)
            pygame.draw.rect(surface, rect_color, (x * tile_size, y * tile_size, tile_size, tile_size))
            walls = maze[x][y]['walls']
            if walls.get('right', True):
                pygame.draw.line(surface, (100, 100, 100),
                                 (x * tile_size + tile_size, y * tile_size),
                                 (x * tile_size + tile_size, y * tile_size + tile_size), max(1, 0))
            if walls.get('down', True):
                pygame.draw.line(surface, (100, 100, 100),
                                 (x * tile_size, y * tile_size + tile_size),
                                 (x * tile_size + tile_size, y * tile_size + tile_size), max(1, 0))

    surface.blit(player_image, (player_posx * tile_size, player_posy * tile_size))

# =========================
# BOUCLE PRINCIPALE
# =========================
clock = pygame.time.Clock()
running = True
while running:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
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

            color = (0,0,255) if abs(dx) <= threshold and abs(dy) <= threshold else (0,255,0)
            x_min = int(bbox.xmin * w)
            y_min = int(bbox.ymin * h)
            box_width = int(bbox.width * w)
            box_height = int(bbox.height * h)
            cv2.rectangle(frame, (x_min, y_min), (x_min+box_width, y_min+box_height), color, 4)

            move_cooldown += 1
            if move_cooldown > 10:
                if dx > threshold and not is_wall(player_posx, player_posy,'right'):
                    player_posx = min(player_posx + 1, maze_w - 1)
                elif dx < -threshold and not is_wall(player_posx, player_posy,'left'):
                    player_posx = max(player_posx - 1, 0)
                elif dy > threshold and not is_wall(player_posx, player_posy,'down'):
                    player_posy = min(player_posy + 1, maze_h - 1)
                elif dy < -threshold and not is_wall(player_posx, player_posy,'up'):
                    player_posy = max(player_posy - 1, 0)
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
                # reseed et regénérer le labyrinthe (utile en runtime)
                random.seed(SEED)
                for x in range(maze_w):
                    for y in range(maze_h):
                        maze[x][y] = {'visited': False, 'walls': {'up': True, 'down': True, 'left': True, 'right': True}}
                generate_maze_dfs()
                player_posx = player_posy = 0

    clock.tick(30)  # limiter à ~30 FPS

# Nettoyage
cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()
