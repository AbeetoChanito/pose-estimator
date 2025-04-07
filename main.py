import json

import pygame
import math
import sys
import threading

# === USER SETTINGS ===
with open("config.json") as config_file:
    config = json.load(config_file)

    FIELD_IMAGE_PATH = config["FIELD_IMAGE_PATH"] # Background image
    ROBOT_WIDTH = config["ROBOT_WIDTH"]
    ROBOT_HEIGHT = config["ROBOT_HEIGHT"]

WINDOW_SIZE = 700  # Window size
FIELD_WIDTH = 3600 / 25.4 + 4 # Field width in inches
IN_TO_PX = WINDOW_SIZE / FIELD_WIDTH # inches / pixel
# ======================

ROBOT_WIDTH *= IN_TO_PX
ROBOT_HEIGHT *= IN_TO_PX


pygame.init()
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
pygame.display.set_caption("Robot Field")
clock = pygame.time.Clock()

# Load and scale field image
field_img = pygame.image.load(FIELD_IMAGE_PATH).convert()
field_img = pygame.transform.scale(field_img, (WINDOW_SIZE, WINDOW_SIZE))

# Create transparent robot with a green border and red arrow
robot_orig = pygame.Surface((ROBOT_WIDTH, ROBOT_HEIGHT), pygame.SRCALPHA)
robot_orig.fill((0, 0, 0, 0))  # Fully transparent
pygame.draw.rect(robot_orig, (0, 255, 0, 255), robot_orig.get_rect(), width=2)  # Green border
pygame.draw.line(robot_orig, (255, 0, 0, 255), (ROBOT_WIDTH // 2, ROBOT_HEIGHT // 2), (ROBOT_WIDTH // 2, 10), width=3)  # Red arrow

robot_angle = 0
robot_pos = [WINDOW_SIZE // 2, WINDOW_SIZE // 2]  # Start in center
moving_robot = False
rotating_robot = False

# Thread-safe robot state update
robot_lock = threading.Lock()
stop_event = threading.Event()

def rotate_towards(target_pos, current_pos):
    dx = target_pos[0] - current_pos[0]
    dy = target_pos[1] - current_pos[1]
    angle = 90 - math.degrees(math.atan2(-dy, dx))  # Adjust to align arrow with top
    return angle

def blit_rotate_center(surf, image, top_left, angle):
    rotated_image = pygame.transform.rotate(image, -angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft=top_left).center)
    surf.blit(rotated_image, new_rect.topleft)

# Console input thread for x y theta
def input_thread():
    global robot_pos, robot_angle
    while not stop_event.is_set():
        try:
            user_input = sys.stdin.readline()
            if stop_event.is_set() or not user_input:
                break
            parts = user_input.strip().split()
            if len(parts) != 3 and len(parts) != 2:
                print("Invalid input, use format: x y theta")
                continue

            if len(parts) == 2:
                with robot_lock:
                    modifier = parts[0]
                    value = float(parts[1])
                    if modifier == "theta":
                        robot_angle = value
                    elif modifier == "x":
                        value *= IN_TO_PX
                        value += WINDOW_SIZE / 2
                        robot_pos[0] = value
                    elif modifier == "y":
                        value *= IN_TO_PX * -1
                        value += WINDOW_SIZE / 2
                        robot_pos[1] = value
                    else:
                        print("Invalid modifier, use format: modifier value")


            if len(parts) == 3:
                x, y, theta = map(float, parts)
                with robot_lock:
                    x *= IN_TO_PX
                    y *= IN_TO_PX * -1
                    x += WINDOW_SIZE / 2
                    y += WINDOW_SIZE / 2
                    robot_pos = [x, y]
                    robot_angle = theta
        except Exception as e:
            if not stop_event.is_set():
                print(f"Error: {e}")

# Start input thread
thread = threading.Thread(target=input_thread, daemon=True)
thread.start()

running = True
while running:
    screen.blit(field_img, (0, 0))

    mouse_buttons = pygame.mouse.get_pressed()
    keys = pygame.key.get_mods()
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if keys & pygame.KMOD_SHIFT:
                    rotating_robot = True
                else:
                    moving_robot = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                moving_robot = False
                rotating_robot = False

        elif event.type == pygame.MOUSEMOTION:
            if moving_robot and not (keys & pygame.KMOD_SHIFT):
                with robot_lock:
                    robot_pos = list(mouse_pos)
            elif rotating_robot:
                with robot_lock:
                    robot_angle = rotate_towards(mouse_pos, robot_pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                with robot_lock:
                    rx, ry = robot_pos
                    rx -= WINDOW_SIZE / 2
                    ry -= WINDOW_SIZE / 2
                    rx /= IN_TO_PX
                    ry /= IN_TO_PX * -1
                    ra = robot_angle
                    if ra < 0:
                        ra += 360
                    if ra >= 360:
                        ra -= 360

                    print(f"{rx:.2f} {ry:.2f} {ra:.2f}")

    # Draw robot with rotation
    with robot_lock:
        blit_rotate_center(
            screen,
            robot_orig,
            (robot_pos[0] - ROBOT_WIDTH // 2, robot_pos[1] - ROBOT_HEIGHT // 2),
            robot_angle,
        )

    pygame.display.flip()
    clock.tick(60)

# Clean up input thread on exit
stop_event.set()
pygame.quit()
sys.exit()
