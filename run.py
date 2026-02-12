import pygame
import random
import math
import os
import cv2
import numpy as np
from collections import defaultdict

# ---------------- SETTINGS ----------------
WIDTH, HEIGHT = 1000, 700
BASE_SIZE = 150
FPS = 60
POWER_PER_OBJECT = 7
IMAGE_FOLDER = "fightvideo"
OUTPUT_FILE = "arena_output.mp4"
# ------------------------------------------

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Image Smash Arena")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 22)

# ---------------- VIDEO RECORDING ----------------
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
video = cv2.VideoWriter(
    OUTPUT_FILE,
    fourcc,
    FPS,
    (WIDTH, HEIGHT)
)
# -------------------------------------------------


# ---------------- LOAD IMAGES ----------------
image_surfaces = []

for filename in os.listdir(IMAGE_FOLDER):
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        path = os.path.join(IMAGE_FOLDER, filename)
        img = pygame.image.load(path).convert_alpha()
        image_surfaces.append(img)

if not image_surfaces:
    raise Exception("No images found in fightvideo folder!")

total_images = len(image_surfaces)

# Dynamic size
radius = BASE_SIZE / math.sqrt(total_images)
diameter = int(radius * 2)

GRID_SIZE = diameter


# ---------------- PARTICLE CLASS ----------------
class Particle:
    def __init__(self, image_surface, x, y):
        self.radius = radius
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.power = POWER_PER_OBJECT

        scaled = pygame.transform.smoothscale(
            image_surface, (diameter, diameter)
        ).convert_alpha()

        mask = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            mask,
            (255, 255, 255, 255),
            (diameter // 2, diameter // 2),
            diameter // 2
        )

        scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.image = scaled
        self.rect = self.image.get_rect(center=(self.x, self.y))

    def move(self):
        self.x += self.vx
        self.y += self.vy

        if self.x <= self.radius or self.x >= WIDTH - self.radius:
            self.vx *= -1
        if self.y <= self.radius or self.y >= HEIGHT - self.radius:
            self.vy *= -1

        self.rect.center = (self.x, self.y)

    def draw(self):
        screen.blit(self.image, self.rect)

        bar_width = self.radius * 2
        bar_height = 6
        ratio = self.power / POWER_PER_OBJECT

        bar_x = self.x - self.radius
        bar_y = self.y - self.radius - 12

        pygame.draw.rect(screen, (40, 40, 40),
                         (bar_x, bar_y, bar_width, bar_height))

        if ratio > 0.5:
            color = (0, 255, 0)
        elif ratio > 0.2:
            color = (255, 165, 0)
        else:
            color = (255, 0, 0)

        pygame.draw.rect(screen, color,
                         (bar_x, bar_y, bar_width * ratio, bar_height))


# ---------------- SAFE SPAWN ----------------
particles = []

def is_overlapping(new_x, new_y):
    for p in particles:
        dx = new_x - p.x
        dy = new_y - p.y
        distance_sq = dx * dx + dy * dy
        min_dist = radius + p.radius
        if distance_sq < min_dist * min_dist:
            return True
    return False


for img in image_surfaces:
    placed = False
    attempts = 0

    while not placed and attempts < 500:
        new_x = random.uniform(radius, WIDTH - radius)
        new_y = random.uniform(radius, HEIGHT - radius)

        if not is_overlapping(new_x, new_y):
            particles.append(Particle(img, new_x, new_y))
            placed = True

        attempts += 1


# ---------------- SPATIAL GRID ----------------
def build_spatial_grid():
    grid = defaultdict(list)
    for p in particles:
        cell_x = int(p.x // GRID_SIZE)
        cell_y = int(p.y // GRID_SIZE)
        grid[(cell_x, cell_y)].append(p)
    return grid


def check_collisions():
    grid = build_spatial_grid()
    checked_pairs = set()

    for (cell_x, cell_y), cell_particles in grid.items():
        neighbors = []

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbors.extend(grid.get((cell_x + dx, cell_y + dy), []))

        for p1 in cell_particles:
            for p2 in neighbors:

                if p1 is p2:
                    continue

                pair = tuple(sorted((id(p1), id(p2))))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                dx = p1.x - p2.x
                dy = p1.y - p2.y
                distance_sq = dx * dx + dy * dy
                min_dist = p1.radius + p2.radius

                if distance_sq < min_dist * min_dist:

                    p1.vx, p2.vx = p2.vx, p1.vx
                    p1.vy, p2.vy = p2.vy, p1.vy

                    if p1.power > 0:
                        p1.power -= 1
                    if p2.power > 0:
                        p2.power -= 1


# ---------------- MAIN LOOP ----------------
running = True
while running:
    clock.tick(FPS)
    screen.fill((10, 10, 15))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for p in particles:
        p.move()

    check_collisions()

    particles = [p for p in particles if p.power > 0]

    if len(particles) <= 1:
        running = False

    for p in particles:
        p.draw()

    counter_text = font.render(
        f"Alive: {len(particles)}", True, (255, 255, 255)
    )
    screen.blit(counter_text, (20, 20))

    pygame.display.flip()

    # -------- RECORD FRAME --------
    frame = pygame.surfarray.array3d(screen)
    frame = np.transpose(frame, (1, 0, 2))
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    video.write(frame)
    # ------------------------------

video.release()
pygame.quit()

print("Video saved as:", OUTPUT_FILE)
