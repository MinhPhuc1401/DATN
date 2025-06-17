import pygame
import sys
import random
from pytmx.util_pygame import load_pygame

from .settings import *
from .player import Player
from .sprites import Sprite, CollisionSprite, Gun, Bullet, Enemy, MeleeEnemy, RangedEnemy, ChargerEnemy, BossEnemy
from .groups import AllSprites
from .levels import get_level_data, TOTAL_LEVELS
from .ai_chatbot import GameAI
from .buffs import BUFF_DEFINITIONS, get_random_buff_type, BuffItem, ActiveBuff

class Button:
    def __init__(self, x, y, width, height, text, font, text_color=(220, 220, 220), color=(60, 60, 60), hover_color=(80, 80, 80)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.text_surface = self.font.render(text, True, text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2, border_radius=12)
        screen.blit(self.text_surface, self.text_rect)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                return True
        return False

class Game:
    def __init__(self, level=1):
        pygame.init()        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('The Monster Hunter')
        self.clock = pygame.time.Clock()
        self.running = True
        self.player_died = False 
        self.is_paused = False
        self.waiting_for_continue = False
        
        self.level = min(max(level, 1), TOTAL_LEVELS)
        self.player_won = False
        self.level_data = get_level_data(self.level)
        
        self.setup_sprite_groups()
        self.setup_game_state()
        self.setup_audio()
        self.setup_ui()
        
        self.load_images()
        self.setup()
        
        self.game_ai = GameAI(self.player, self.enemy_sprites)
        
        if self.level_data.get('is_boss_level', False):
            self.spawn_boss_if_ready()
        else:
            self.spawn_enemy()

        self.hud_font_large = pygame.font.Font(None, 42) 
        self.hud_font = pygame.font.Font(None, 30) 

    def setup_sprite_groups(self):
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()   
        self.enemy_sprites = pygame.sprite.Group()   
        self.buff_item_sprites = pygame.sprite.Group()
        self.damaging_zone_sprites = pygame.sprite.Group()

    def setup_game_state(self):
        self.can_attack = True
        self.attack_time = 0
        self.attack_cooldown = GAME_ATTACK_COOLDOWN
        self.spawn_positions = []
        self.enemies_killed_this_level = 0
        self.initial_enemy_count = 0
        self.boss = None
        self.boss_skill_visuals = None

    def setup_audio(self):
        self.shoot_sound = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.hit_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.reload_sound = pygame.mixer.Sound(join('audio', 'reload.wav'))
        
        # Buff sounds
        self.speed_buff_sound = pygame.mixer.Sound(join('audio', 'speed.wav'))
        self.damage_buff_sound = pygame.mixer.Sound(join('audio', 'damage.wav'))
        self.health_buff_sound = pygame.mixer.Sound(join('audio', 'heal.wav'))
        
        # Chọn nhạc nền dựa vào loại màn chơi
        if self.level_data.get('is_boss_level', False):
            self.music = pygame.mixer.Sound(join('audio', 'final_battle.wav'))
        else:
            self.music = pygame.mixer.Sound(join('audio', 'battle.wav'))
        
        self.setup_audio_volumes()
        self.music_channel = self.music.play(-1)

    def setup_audio_volumes(self):
        self.shoot_sound.set_volume(0.3)
        self.hit_sound.set_volume(0.3)
        self.reload_sound.set_volume(0.6)
        
        # Buff sound volumes
        self.speed_buff_sound.set_volume(0.5)
        self.damage_buff_sound.set_volume(0.5)
        self.health_buff_sound.set_volume(0.5)
        
        self.music.set_volume(0.5)

    def setup_ui(self):
        self.return_to_menu = False 
        self.current_level_display = self.level 
        self.button_font = pygame.font.Font(None, 50)
        self.hud_font = pygame.font.Font(None, 30)

    def check_win_condition(self): 
        if not self.player_died:
            if self.level_data.get('is_boss_level', False):
                if self.boss and self.boss.health <= 0 and hasattr(self.boss, 'death_animation_complete') and self.boss.death_animation_complete:
                    self.waiting_for_continue = True
                    self.player_won = True
            elif len(self.enemy_sprites) == 0 and not any(enemy.health > 0 for enemy in self.enemy_sprites):
                self.waiting_for_continue = True
                self.player_won = True

    def load_images(self):
        # Load bullet and gun images
        self.bullet_surf = pygame.image.load(join('images', 'weapons', 'bullet.png')).convert_alpha()
        self.gun_image = pygame.image.load(join('images', 'weapons', 'gun.png')).convert_alpha()
        
        # Load enemy frames
        self.enemy_frames = {}
        self.enemy_data = {
            'skeleton': {'class': MeleeEnemy, 'health': 30, 'frames_folder': 'skeleton'}, 
            'blob': {'class': RangedEnemy, 'health': 20, 'frames_folder': 'blob'},   
            'bat': {'class': ChargerEnemy, 'health': 20, 'frames_folder': 'bat'}   
        }
        
        for enemy_key, data in self.enemy_data.items(): 
            self.enemy_frames[enemy_key] = []
            folder_name = data['frames_folder']
            try:
                for folder_path, _, file_names in walk(join('images', 'enemies', folder_name)):
                    if not file_names: continue 
                    for file_name in sorted(file_names, key = lambda name: int(name.split('.')[0])):
                        path = join(folder_path, file_name)
                        surf = pygame.image.load(path).convert_alpha()
                        self.enemy_frames[enemy_key].append(surf)
            except (FileNotFoundError, ValueError):
                pass

        # Load boss animation frames
        boss_animation_folders = {
            'idle': 'idle',
            'skill1': 'skill1',
            'skill2': 'skill2',
            'skill3': 'skill3',
            'death': 'death'
        }
        
        self.boss_frames = {state: [] for state in boss_animation_folders.keys()}
        
        for state, folder_name in boss_animation_folders.items():
            try:
                folder_path = join('images', 'enemies', 'boss', folder_name)
                for _, _, files in walk(folder_path):
                    for file_name in sorted(files, key=lambda name: int(name.split('.')[0])):
                        if file_name.endswith('.png'):
                            path = join(folder_path, file_name)
                            surf = pygame.image.load(path).convert_alpha()
                            self.boss_frames[state].append(surf)
                    break
            except (FileNotFoundError, ValueError) as e:
                print(f"Error loading boss {state} frames: {e}")
                surf = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2))
                surf.fill((255, 0, 0))
                self.boss_frames[state] = [surf]

        # Load boss skill effect frames
        boss_skill_folders = {
            'skill2': 'skill2',  # damage zone effect
            'skill3': 'skill3'   # fireball projectile
        }
        
        self.boss_skill_frames = {skill: [] for skill in boss_skill_folders.keys()}
        
        for skill, folder_name in boss_skill_folders.items():
            try:
                folder_path = join('images', 'effects', 'boss_skills', folder_name)
                for _, _, files in walk(folder_path):
                    for file_name in sorted(files, key=lambda name: int(name.split('.')[0])):
                        if file_name.endswith('.png'):
                            path = join(folder_path, file_name)
                            surf = pygame.image.load(path).convert_alpha()
                            self.boss_skill_frames[skill].append(surf)
                    break
            except (FileNotFoundError, ValueError) as e:
                print(f"Error loading boss skill {skill} frames: {e}")
                self.boss_skill_frames[skill] = []

    def setup(self):
        self.clear_sprites()
        self.load_map()
        
    def clear_sprites(self):
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.enemy_sprites.empty()
        self.bullet_sprites.empty()
        self.buff_item_sprites.empty()
        self.spawn_positions.clear()
        self.boss = None
        self.boss_spawn_position = None

    def load_map(self):
        try:
            map_data = load_pygame(join('data', 'maps', f'level_{self.level}.tmx'))
        except FileNotFoundError:
            map_data = load_pygame(join('data', 'maps', 'world.tmx'))

        self.load_map_layers(map_data)
        self.load_entities(map_data)

    def load_map_layers(self, map_data):
        for x, y, image in map_data.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
            
        if map_data.get_layer_by_name('Objects'): 
            for x, y, image in map_data.get_layer_by_name('Objects').tiles():
                Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        
        if map_data.get_layer_by_name('Collisions'): 
            for obj in map_data.get_layer_by_name('Collisions'):
                collision_surf = pygame.Surface((obj.width, obj.height))
                collision_surf.fill((255, 0, 0))
                CollisionSprite((obj.x, obj.y), collision_surf, self.collision_sprites)

    def load_entities(self, map_data):
        if map_data.get_layer_by_name('Entities'): 
            for obj in map_data.get_layer_by_name('Entities'):
                if obj.name == 'Player':
                    self.player_initial_pos = (obj.x, obj.y)
                    self.player = Player(self.player_initial_pos, self.all_sprites, self.collision_sprites)
                    self.player.game = self
                    self.gun = Gun(self.player, self.all_sprites)
                elif obj.name == 'Boss':
                    self.boss_spawn_position = (obj.x, obj.y)
                else:
                    self.spawn_positions.append((obj.x, obj.y))

    def spawn_boss_if_ready(self):
        if not self.boss and len(self.enemy_sprites) == 0:
            spawn_pos = self.boss_spawn_position if self.boss_spawn_position else (WIDTH / 2, HEIGHT / 2)
            
            if not self.boss_frames['idle']:
                surf = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 2))
                surf.fill((255, 0, 0))
                self.boss_frames['idle'] = [surf]
                for state in ['skill1', 'skill2', 'skill3', 'death']:
                    if not self.boss_frames[state]:
                        self.boss_frames[state] = self.boss_frames['idle'][:]

            self.boss = BossEnemy(
                pos=spawn_pos,
                frames=self.boss_frames,
                groups=[self.all_sprites, self.enemy_sprites],
                player=self.player,
                collision_sprites=self.collision_sprites,
                damaging_zone_group=self.damaging_zone_sprites,
                all_sprites_group=self.all_sprites,
                bullet_group=self.bullet_sprites
            )
            self.boss.game = self
            self.initial_enemy_count = 1
            self.enemies_killed_this_level = 0
            return True
        return False

    def spawn_enemy(self):
        if not self.level_data or not hasattr(self, 'player') or not self.spawn_positions:
            return

        enemies_to_spawn = []
        if specific_enemies := self.level_data.get('specific_enemies'):
            for enemy_type, count in specific_enemies:
                if enemy_type in self.enemy_data and self.enemy_frames.get(enemy_type):
                    enemies_to_spawn.extend([enemy_type] * count)

        if random_config := self.level_data.get('random_enemies_config'):
            count = random_config.get('count', 0)
            pool = [ptype for ptype in random_config.get('pool', []) 
                   if ptype in self.enemy_data and self.enemy_frames.get(ptype)]
            if pool and count > 0:
                enemies_to_spawn.extend(random.choice(pool) for _ in range(count))

        if not enemies_to_spawn:
            return

        spawn_positions = random.sample(self.spawn_positions, len(self.spawn_positions))
        num_to_spawn = min(len(enemies_to_spawn), len(spawn_positions))
        self.initial_enemy_count = num_to_spawn

        for i in range(num_to_spawn):
            enemy_type = enemies_to_spawn[i]
            position = spawn_positions[i % len(spawn_positions)]
            enemy_config = self.enemy_data[enemy_type]
            
            enemy_config['class'](
                pos=position,
                frames=self.enemy_frames[enemy_type],
                groups=(self.all_sprites, self.enemy_sprites),
                player=self.player,
                collision_sprites=self.collision_sprites,
                health=enemy_config['health']
            )

    def handle_input(self):
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.game_ai.handle_events(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if self.player.current_ammo < self.player.magazine_size and not self.player.is_dying:
                        self.reload_sound.play()
                        self.player.start_reload()
        
        self.handle_shooting(mouse_buttons)
        self.handle_movement(keys)

    def handle_shooting(self, mouse_buttons):
        if mouse_buttons[0] and self.can_attack and not self.player.reloading:
            if self.player.current_ammo > 0:
                direction = self.gun.player_direction
                if direction.length() > 0:
                    Bullet(
                        self.bullet_surf,
                        self.gun.rect.center,
                        direction.normalize(),
                        [self.all_sprites, self.bullet_sprites],
                        self.player.get_modified_damage(BULLET_DAMAGE)
                    )
                    self.can_attack = False
                    self.attack_time = pygame.time.get_ticks()
                    self.shoot_sound.play()
                    self.player.current_ammo -= 1
            # Auto reload when out of ammo
            elif not self.player.reloading and not self.player.is_dying:
                self.reload_sound.play()
                self.player.start_reload()

    def handle_movement(self, keys):
        if not self.player.is_dying:
            self.player.direction.x = keys[pygame.K_d] - keys[pygame.K_a]
            self.player.direction.y = keys[pygame.K_s] - keys[pygame.K_w]

    def update(self, dt):
        if not self.is_paused and not self.waiting_for_continue and not self.game_ai.chat_box.active:
            self.update_attack_timer()
            self.handle_input()
            self.all_sprites.update(dt)
            self.handle_collisions()
            self.check_win_condition()

    def update_attack_timer(self):
        if not self.can_attack:
            if pygame.time.get_ticks() - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

    def handle_collisions(self):
        self.handle_bullet_collisions()
        self.handle_player_collisions()

    def handle_bullet_collisions(self):
        for bullet in self.bullet_sprites:
            hit_enemies = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False, pygame.sprite.collide_mask)
            if hit_enemies:
                bullet.kill()
                enemy = hit_enemies[0]
                if enemy.health > 0:
                    self.hit_sound.play()
                    if enemy.take_damage(bullet.damage):
                        self.handle_enemy_death(enemy)

    def handle_enemy_death(self, enemy):
        # Only drop buff for normal enemies, not boss
        if not isinstance(enemy, BossEnemy) and random.random() < BUFF_DROP_CHANCE:
            buff_type = get_random_buff_type()
            if buff_type:
                BuffItem(enemy.rect.center, buff_type, (self.all_sprites, self.buff_item_sprites))

        if self.level == TOTAL_LEVELS and len(self.enemy_sprites) == 0 and not self.boss:
            self.spawn_boss_if_ready()

    def handle_player_collisions(self):
        if self.player.health <= 0 and not self.player.is_dying:
            self.player.start_death_animation()
            return

        if self.player.is_dying and self.player.death_animation_complete:
            self.waiting_for_continue = True
            self.player_died = True
            return

        picked_up_buffs = pygame.sprite.spritecollide(self.player, self.buff_item_sprites, True, pygame.sprite.collide_mask)
        for buff in picked_up_buffs:
            if buff.buff_data and hasattr(self.player, 'apply_buff'):
                # Play sound for each buff type
                if buff.buff_type_key == 'speed_boost':
                    self.speed_buff_sound.play()
                elif buff.buff_type_key == 'damage_boost':
                    self.damage_buff_sound.play()
                elif buff.buff_type_key == 'health_regen':
                    self.health_buff_sound.play()
                
                self.player.apply_buff(buff.buff_type_key)

    def draw(self):
        self.screen.fill('black')
        
        if hasattr(self, 'player') and self.player:
            self.all_sprites.custom_draw(self.player, self.player.rect.center)
            self.player.draw_afterimages(self.screen, self.all_sprites.offset)
        else:
            self.all_sprites.custom_draw(None, (WIDTH/2, HEIGHT/2))
            
        self.draw_enemy_attacks()
        self.draw_enemy_health_bars()
        self.draw_hud()
        self.game_ai.draw(self.screen)

        if self.waiting_for_continue:
            self.draw_continue_message()
            
        pygame.display.flip()

    def draw_enemy_attacks(self):
        for enemy in self.enemy_sprites:
            if enemy.health <= 0:
                continue
                
            if isinstance(enemy, RangedEnemy):
                surf, pos = enemy.draw_attack()
            elif isinstance(enemy, ChargerEnemy):
                surf, pos = enemy.draw_attack_indicator()
            elif isinstance(enemy, BossEnemy):
                enemy.draw_active_skill_effects(self.screen, self.all_sprites.offset)
                continue
            else:
                continue
                
            if surf and pos:
                screen_pos = (pos[0] + self.all_sprites.offset.x, pos[1] + self.all_sprites.offset.y)
                self.screen.blit(surf, screen_pos)

    def draw_enemy_health_bars(self):
        for enemy in self.enemy_sprites:
            if enemy.health > 0 and enemy.health < enemy.max_health:
                health_percent = enemy.get_health_percentage() / 100
                bar_width = enemy.rect.width * 0.8
                bar_height = 7
                bar_pos_x = enemy.rect.centerx - bar_width / 2
                bar_pos_y = enemy.rect.top - bar_height - 5
                
                screen_pos_x = bar_pos_x + self.all_sprites.offset.x
                screen_pos_y = bar_pos_y + self.all_sprites.offset.y

                self.draw_health_bar(self.screen, (screen_pos_x, screen_pos_y), 
                                   (bar_width, bar_height), (200,200,200), (0,255,0), health_percent)

    def draw_health_bar(self, surf, pos, size, border_color, bar_color, progress):
        pygame.draw.rect(surf, border_color, (*pos, *size), 2)
        inner_pos = (pos[0] + 1, pos[1] + 1)
        inner_size = ((size[0] - 2) * max(0, progress), size[1] - 2)
        pygame.draw.rect(surf, bar_color, (*inner_pos, *inner_size))

    def draw_hud(self):
        # Player Health
        health_percent = self.player.get_health_percentage() / 100
        health_pos = (20, HEIGHT - 50)
        health_size = (250, 30)
        self.draw_health_bar(self.screen, health_pos, health_size, (200,200,200), (255,0,0), health_percent)
        
        # Health text
        health_text = self.hud_font_large.render(f'HP: {int(self.player.health)}/{self.player.max_health}', True, (255,255,255))
        self.screen.blit(health_text, (health_pos[0] + health_size[0] + 10, health_pos[1]))

        # Game Info
        enemies_text = self.hud_font_large.render(f'Enemies Left: {len(self.enemy_sprites)}', True, (255,255,255))
        self.screen.blit(enemies_text, (20, 20))
        
        # Level text
        level_text = self.hud_font_large.render(f'Level: {self.current_level_display}', True, (255,255,255))
        self.screen.blit(level_text, (WIDTH - 200, 20))

        # Status Messages (Dash & Reload)
        status_pos_y = 70
        
        # Dash Cooldown Status
        current_time = pygame.time.get_ticks()
        if hasattr(self.player, 'dash_time') and not self.player.is_dashing:
            if current_time - self.player.dash_time < self.player.dash_cooldown:
                dash_text = self.hud_font_large.render('Dash on Cooldown', True, (255, 200, 0))
                self.screen.blit(dash_text, (20, status_pos_y))
                status_pos_y += 40
        
        # Reload Status
        if self.player.reloading:
            reload_text = self.hud_font_large.render('Reloading...', True, (255, 200, 0))
            self.screen.blit(reload_text, (20, status_pos_y))
            status_pos_y += 40

        # Ammo
        ammo_text = self.hud_font_large.render(f'Ammo: {self.player.current_ammo}/{self.player.magazine_size}', True, (255,255,255))
        ammo_pos = (health_pos[0], health_pos[1] - 40)
        self.screen.blit(ammo_text, ammo_pos)

        # Active Buffs
        if hasattr(self.player, 'active_buffs'):
            for i, buff in enumerate(self.player.active_buffs):
                if hasattr(buff, 'is_active') and buff.is_active:
                    name = buff.buff_data.get('name', 'Unknown Buff')
                    time = buff.get_remaining_time() / 1000
                    
                    color = {
                        'speed_boost': (0, 150, 255),
                        'damage_boost': (255, 255, 0),
                        'health_regen': (255, 0, 0)
                    }.get(buff.buff_type_key, (255, 255, 255))

                    buff_text = self.hud_font.render(f'{name}: {time:.1f}s', True, color)
                    self.screen.blit(buff_text, (20, status_pos_y + i * 30))

    def draw_continue_message(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        if not hasattr(self, 'continue_button'):
            button_width = 300
            button_height = 60
            center_x = WIDTH // 2 - button_width // 2
            font = pygame.font.Font(None, 50)
            
            self.continue_button = Button(center_x, HEIGHT * 3/4, button_width, button_height, 
                                       "Continue", font)

        font = pygame.font.Font(None, 96)
        text = font.render("Enemies Defeated!" if self.player_won else "You Died!", True, (255, 255, 255))
        
        shadow_offset = 3
        shadow_color = (128, 128, 128)
        
        shadow_text = font.render("Enemies Defeated!" if self.player_won else "You Died!", True, shadow_color)
        shadow_rect = shadow_text.get_rect(center=(WIDTH/2 + shadow_offset, HEIGHT/3 + shadow_offset))
        self.screen.blit(shadow_text, shadow_rect)
        
        text_rect = text.get_rect(center=(WIDTH/2, HEIGHT/3))
        self.screen.blit(text, text_rect)

        self.continue_button.draw(self.screen)

    def handle_pause_state(self):
        if self.is_paused or self.waiting_for_continue or self.game_ai.chat_box.active:
            if self.music_channel and self.music_channel.get_busy():
                self.music_channel.pause()
        else:
            if self.music_channel:
                self.music_channel.unpause()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and not self.game_ai.chat_box.active:
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_r and self.player_died:
                        self.reset_game_state()
                        self.player_died = False
                        self.waiting_for_continue = False
                
                # Handle continue button in main loop
                if self.waiting_for_continue and hasattr(self, 'continue_button'):
                    if self.continue_button.handle_event(event):
                        self.waiting_for_continue = False
                        if self.player_won:
                            return "win"
                        else:
                            return "lose"
                            
                self.game_ai.handle_events(event)
            
            self.handle_pause_state()
            self.update(dt)
            self.draw()
                
        self.music.stop()
        return "menu"

    def reset_game_state(self):
        self.clear_sprites()
        self.level_data = get_level_data(self.level)
        
        # Change background music when reset game state
        if self.music_channel:
            self.music_channel.stop()
        if self.level_data.get('is_boss_level', False):
            self.music = pygame.mixer.Sound(join('audio', 'final_battle.wav'))
        else:
            self.music = pygame.mixer.Sound(join('audio', 'battle.wav'))
        self.music.set_volume(0.3)
        self.music_channel = self.music.play(-1)
        
        self.current_level_display = self.level
        self.setup()
        self.spawn_enemy()

        if hasattr(self, 'player') and self.player:
            self.player.health = self.player.max_health
            if hasattr(self.player, 'player_initial_pos'):
                self.player.rect.center = self.player.player_initial_pos
                self.player.hitbox_rect.center = self.player.rect.center
            else:
                self.player.rect.center = (WIDTH/2, HEIGHT/2)
                self.player.hitbox_rect.center = self.player.rect.center

            self.player.afterimages.clear()
            self.player.is_dashing = False
            
            if hasattr(self.player, 'active_buffs'):
                self.player.active_buffs.clear()
            if hasattr(self.player, 'reset_stats'):
                self.player.reset_stats()

            self.player.current_ammo = self.player.magazine_size
            self.player.reloading = False
            self.player.reload_start_time = 0

        self.can_attack = True
        self.attack_time = 0
        self.player_won = False
        self.player_died = False
        self.running = True