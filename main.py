import pygame
import random
import sys

# -------------------- Initialization --------------------
pygame.init()

# -------------------- Constants --------------------
WIDTH, HEIGHT = 1000, 619
FPS = 60
MIN_SPAWN_DISTANCE = 150

# Object Sizes
PLAYER_SIZE = 50
ENEMY_SIZE = 60
APPLE_SIZE = 30
POTION_SIZE = 35

# Image Size Dictionary
IMAGE_SIZES = {
    'player': (PLAYER_SIZE + 8, PLAYER_SIZE),
    'enemy': (ENEMY_SIZE, ENEMY_SIZE - 13),
    'apple': (APPLE_SIZE, APPLE_SIZE + 8),
    'heart': (35, 30),
    'potions': {
        'kill_all': (30, 57),
        'ghost_mode': (30, 54),
        'speed_boost': (35, 40)
    },
    'background': (WIDTH, HEIGHT)
}

# Colors (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Speeds
BASE_PLAYER_SPEED = 5
BASE_ENEMY_SPEED = 3
player_speed = BASE_PLAYER_SPEED
enemy_speed = BASE_ENEMY_SPEED

# Events
DIFFICULTY_EVENT = pygame.USEREVENT + 1
ENEMY_SPAWN_EVENT = pygame.USEREVENT + 2
POTION_SPAWN_EVENT = pygame.USEREVENT + 3
DIFFICULTY_EVENT_TIME = 15000  # milliseconds
ENEMY_SPAWN_EVENT_TIME = 3000  # milliseconds
POTION_SPAWN_EVENT_TIME = 15000  # milliseconds
pygame.time.set_timer(DIFFICULTY_EVENT, DIFFICULTY_EVENT_TIME)
pygame.time.set_timer(ENEMY_SPAWN_EVENT, ENEMY_SPAWN_EVENT_TIME)
pygame.time.set_timer(POTION_SPAWN_EVENT, POTION_SPAWN_EVENT_TIME)

# -------------------- Screen Setup --------------------
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Freaking Survivor Game")
clock = pygame.time.Clock()

# -------------------- Fonts --------------------
def load_fonts():
    return {
        'main': pygame.font.SysFont(None, 48),
        'countdown': pygame.font.SysFont(None, 72),
        'title': pygame.font.SysFont(None, 120)
    }
fonts = load_fonts()

# -------------------- Sounds --------------------
pygame.mixer.init()
pygame.mixer.music.load("sounds/main_sound.ogg")
sound_pickup = pygame.mixer.Sound("sounds/potion_pickup.wav")
sound_gameover = pygame.mixer.Sound("sounds/game_over.mp3")

# -------------------- Load Images --------------------
def load_and_scale(path, size):
    return pygame.transform.scale(pygame.image.load(path).convert_alpha(), size)

def load_images():
    return {
        #'background': load_and_scale("images/game_background.jpg", IMAGE_SIZES['background']),
        'player': load_and_scale("images/player_image.png", IMAGE_SIZES['player']),
        'enemy': load_and_scale("images/enemy_image.png", IMAGE_SIZES['enemy']),
        'apple': load_and_scale("images/apple_image.png", IMAGE_SIZES['apple']),
        'heart': load_and_scale("images/heart_image.png", IMAGE_SIZES['heart']),
        'potions': {
            key: load_and_scale(f"images/{key}_potion_image.png", size)
            for key, size in IMAGE_SIZES['potions'].items()
        }
    }
images = load_images()

# -------------------- Game State Variables --------------------
game_state = "start"
running = True

timer_start = 0
paused_total_duration = 0
pause_start_time = 0
gameover_time = 0

GAMEOVER_INPUT_DELAY = 500  # milliseconds

# Player & Game Stats
score = 0
hearts = 3
apples_collected = 0
player_rect = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)
apple_rect = pygame.Rect(random.randint(0, WIDTH - APPLE_SIZE), random.randint(0, HEIGHT - APPLE_SIZE), APPLE_SIZE, APPLE_SIZE)

# Enemies & Potions
enemies = []
potions = []

# Power-ups
power_active = False
power_type = None
power_timer = 0
boosted = False
last_hit_time = 0
invincibility_ms = 1000
POTION_TYPES = ['kill_all', 'ghost_mode', 'speed_boost']

# Game Over sound flag
gameover_sound_played = False

# -------------------- Helper Functions --------------------
def draw_hearts():
    for i in range(hearts):
        screen.blit(images['heart'], (15 + i * 40, 15))

def draw_score():
    text = fonts['main'].render(str(score), True, RED)
    screen.blit(text, (WIDTH - text.get_width() - 50, 18))
    screen.blit(images['apple'], (WIDTH - 40, 10))

def draw_timer():
    if game_state == "play":
        elapsed = pygame.time.get_ticks() - timer_start - paused_total_duration
    elif game_state == "pause":
        elapsed = pause_start_time - timer_start - paused_total_duration
    elif game_state == "gameover":
        elapsed = gameover_time - timer_start - paused_total_duration
    else:
        elapsed = 0
    mins, secs = divmod(elapsed // 1000, 60)
    time_text = fonts['main'].render(f"{mins:02}:{secs:02}", True, WHITE)
    screen.blit(time_text, (10, HEIGHT - time_text.get_height() - 10))

def spawn_enemy():
    while True:
        x, y = random.randint(0, WIDTH - ENEMY_SIZE), random.randint(0, HEIGHT - ENEMY_SIZE)
        if abs(x - player_rect.x) >= MIN_SPAWN_DISTANCE or abs(y - player_rect.y) >= MIN_SPAWN_DISTANCE:
            return pygame.Rect(x, y, ENEMY_SIZE, ENEMY_SIZE)

def spawn_potion():
    kind = random.choice(POTION_TYPES)
    size = IMAGE_SIZES['potions'][kind]
    x, y = random.randint(0, WIDTH - size[0]), random.randint(0, HEIGHT - size[1])
    return {'rect': pygame.Rect(x, y, *size), 'type': kind}

def move_enemy(enemy):
    direction = pygame.math.Vector2(player_rect.center) - pygame.math.Vector2(enemy.center)
    if direction.length() != 0:
        direction.normalize_ip()
        new_position = pygame.math.Vector2(enemy.center) + direction * enemy_speed
        enemy.center = (int(new_position.x), int(new_position.y))

def separate_enemies(enemies):
    # Prevent enemies from overlapping by pushing them apart
    for i in range(len(enemies)):
        for j in range(i + 1, len(enemies)):
            e1 = enemies[i]
            e2 = enemies[j]
            distance_x = e1.centerx - e2.centerx
            distance_y = e1.centery - e2.centery
            distance_sq = distance_x**2 + distance_y**2
            min_dist = ENEMY_SIZE + 5

            if 0 < distance_sq < min_dist**2:
                distance = distance_sq ** 0.5
                overlap = (min_dist - distance) / 2
                dx = distance_x / distance
                dy = distance_y / distance

                e1.x += int(dx * overlap)
                e1.y += int(dy * overlap)
                e2.x -= int(dx * overlap)
                e2.y -= int(dy * overlap)

                e1.clamp_ip(screen.get_rect())
                e2.clamp_ip(screen.get_rect())

def activate_power(potion):
    global power_active, power_type, power_timer, boosted, enemies, player_speed
    power_active = True
    power_type = potion['type']
    power_timer = pygame.time.get_ticks()
    if power_type == 'kill_all':
        enemies.clear()
    elif power_type == 'speed_boost' and not boosted:
        player_speed += 4
        boosted = True

def reset_power():
    global power_active, power_type, boosted, player_speed
    power_active = False
    if power_type == 'speed_boost' and boosted:
        player_speed -= 4
        boosted = False
    power_type = None

def draw_powerup_countdown():
    if power_active:
        time_left = max(0, 5 - (pygame.time.get_ticks() - power_timer) // 1000)
        countdown_text = fonts['countdown'].render(str(time_left), True, GREEN)
        screen.blit(countdown_text, (
            WIDTH // 2 - countdown_text.get_width() // 2,
            HEIGHT // 2 - countdown_text.get_height() // 2
        ))

def draw_frozen_game_objects():
    # Draw the last frame's objects frozen (for game over screen)
    screen.blit(images['player'], player_rect)
    screen.blit(images['apple'], apple_rect)
    for enemy in enemies:
        screen.blit(images['enemy'], enemy)
    for potion in potions:
        screen.blit(images['potions'][potion['type']], potion['rect'])
    draw_hearts()
    draw_score()
    draw_timer()

# -------------------- Main Game Loop --------------------
while running:
    clock.tick(FPS)
    # screen.blit(images['background'], (0, 0))
    screen.fill((50,120,50))

    if game_state == "start":
        # Draw main title and start prompt
        title_text = fonts['title'].render("Freaking Survivor Game", True, GREEN)
        prompt_text = fonts['main'].render("Press Any Key to Start", True, GREEN)
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 2 - 80))
        screen.blit(prompt_text, (WIDTH // 2 - prompt_text.get_width() // 2, HEIGHT // 2 + 10))
        pygame.display.flip()

        gameover_sound_played = False  # reset for next round

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                game_state = "play"
                timer_start = pygame.time.get_ticks()
                pygame.mixer.music.play(-1)

                # Reset all game variables on start
                player_speed = BASE_PLAYER_SPEED
                enemy_speed = BASE_ENEMY_SPEED
                score = 0
                hearts = 3
                apples_collected = 0
                player_rect.x, player_rect.y = WIDTH // 2, HEIGHT // 2
                apple_rect = pygame.Rect(random.randint(0, WIDTH - APPLE_SIZE), random.randint(0, HEIGHT - APPLE_SIZE), APPLE_SIZE, APPLE_SIZE)
                enemies.clear()
                potions.clear()
                power_active = False
                power_type = None
                power_timer = 0
                boosted = False
                last_hit_time = 0
                paused_total_duration = 0

    elif game_state == "play":
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                game_state = "pause"
                pause_start_time = pygame.time.get_ticks()
                pygame.mixer.music.pause()
            elif event.type == ENEMY_SPAWN_EVENT:
                if not (power_active and power_type == 'kill_all'):
                    enemies.append(spawn_enemy())
            elif event.type == POTION_SPAWN_EVENT:
                if not power_active and not potions:
                    potions.append(spawn_potion())
            elif event.type == DIFFICULTY_EVENT:
                player_speed += 0.3
                enemy_speed += 0.3

        # Handle movement
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            player_rect.y -= player_speed
        if keys[pygame.K_s]:
            player_rect.y += player_speed
        if keys[pygame.K_a]:
            player_rect.x -= player_speed
        if keys[pygame.K_d]:
            player_rect.x += player_speed
        player_rect.clamp_ip(screen.get_rect())

        # Apple collection
        if player_rect.colliderect(apple_rect):
            score += 1
            apples_collected += 1
            if apples_collected >= 20:
                hearts += 1
                apples_collected = 0
            apple_rect = pygame.Rect(random.randint(0, WIDTH - APPLE_SIZE), random.randint(0, HEIGHT - APPLE_SIZE), APPLE_SIZE, APPLE_SIZE)

        # Enemy movement and collision with smaller collision boxes
        smaller_player = player_rect.inflate(-player_rect.width * 0.3, -player_rect.height * 0.3)
        for enemy in enemies[:]:
            if power_type != 'ghost_mode':
                move_enemy(enemy)
            smaller_enemy = enemy.inflate(-enemy.width * 0.3, -enemy.height * 0.3)
            if smaller_player.colliderect(smaller_enemy):
                now = pygame.time.get_ticks()
                if now - last_hit_time >= invincibility_ms:
                    hearts -= 1
                    last_hit_time = now
                    enemies.remove(enemy)
                    if hearts <= 0:
                        game_state = "gameover"
                        gameover_time = pygame.time.get_ticks()
                        pygame.mixer.music.stop()

        # Separate enemies so they don't overlap
        separate_enemies(enemies)

        # Power-up collection
        for potion in potions[:]:
            if player_rect.colliderect(potion['rect']):
                sound_pickup.play()
                activate_power(potion)
                potions.remove(potion)

        # Power-up timeout
        if power_active and pygame.time.get_ticks() - power_timer > 5000:
            reset_power()

        # Drawing
        screen.blit(images['player'], player_rect)
        screen.blit(images['apple'], apple_rect)
        for enemy in enemies:
            screen.blit(images['enemy'], enemy)
        for potion in potions:
            screen.blit(images['potions'][potion['type']], potion['rect'])

        draw_hearts()
        draw_score()
        draw_timer()
        draw_powerup_countdown()

        pygame.display.flip()

    elif game_state == "pause":
        pause_text = fonts['main'].render("Game Paused - Press P to Resume", True, GREEN)
        screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused_duration = pygame.time.get_ticks() - pause_start_time
                paused_total_duration += paused_duration

                # Adjust power timer by paused duration to keep power-up time accurate
                if power_active:
                    power_timer += paused_duration

                game_state = "play"
                pygame.mixer.music.unpause()

    elif game_state == "gameover":
        # Play game over sound only once
        if not gameover_sound_played:
            sound_gameover.play()
            gameover_sound_played = True

        # Draw frozen game objects behind the game over text
        draw_frozen_game_objects()

        over_text = fonts['title'].render("GAME OVER", True, RED)
        restart_text = fonts['main'].render("Press any key to restart", True, WHITE)
        screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 80))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 20))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if pygame.time.get_ticks() - gameover_time >= GAMEOVER_INPUT_DELAY:
                    # Reset all variables for new game start
                    game_state = "play"
                    player_speed = BASE_PLAYER_SPEED
                    enemy_speed = BASE_ENEMY_SPEED
                    score = 0
                    hearts = 3
                    apples_collected = 0
                    enemies.clear()
                    potions.clear()
                    power_active = False
                    power_type = None
                    power_timer = 0
                    boosted = False
                    last_hit_time = 0
                    player_rect.x, player_rect.y = WIDTH // 2, HEIGHT // 2
                    apple_rect = pygame.Rect(random.randint(0, WIDTH - APPLE_SIZE), random.randint(0, HEIGHT - APPLE_SIZE), APPLE_SIZE, APPLE_SIZE)
                    timer_start = pygame.time.get_ticks()
                    paused_total_duration = 0
                    pygame.mixer.music.play(-1)
                    gameover_sound_played = False

pygame.quit()
sys.exit()