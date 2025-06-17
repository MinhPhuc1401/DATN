import pygame
import os
from .settings import * 
from .buffs import BUFF_DEFINITIONS, ActiveBuff 

class Afterimage:
    def __init__(self, pos, image, lifetime=PLAYER_AFTERIMAGE_LIFETIME):
        self.pos = pygame.math.Vector2(pos)
        self.image = image.copy()
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.alpha = PLAYER_AFTERIMAGE_ALPHA
        
        color_overlay = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        color_overlay.fill((255, 255, 255, self.alpha))
        self.image.blit(color_overlay, (0, 0), special_flags=pygame.BLEND_ADD)
    
    def update(self, dt):
        self.lifetime -= dt * 1000
        if self.lifetime > 0:
            fade_factor = self.lifetime / self.max_lifetime
            self.image.set_alpha(int(self.alpha * fade_factor))
        return self.lifetime <= 0

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites):
        super().__init__(groups)
        
        # Animation states
        self.animation_states = {
            'idle': 'idle',
            'walk': 'walk',
            'death': 'death'
        }
        
        # Direction tracking
        self.current_direction = 'down'
        self.last_movement_direction = 'down'
        self.current_state = 'idle'
        self.frame_index = 0
        self.animation_speed = PLAYER_ANIMATION_SPEED       
        self.active_buffs = []
        self.buff_image_modifiers = {}
        
        self.load_images()
        self.load_buff_image_modifiers()
        
        if self.frames['idle']['down']:
            self.image = self.frames['idle']['down'][0]
        else:
            self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.image.fill((0, 255, 0))
            print("Warning: Using placeholder player sprite")
            
        self.rect = self.image.get_frect(center = pos)
        self.hitbox_rect = self.rect.inflate(-60, -90)
        self.collision_sprites = collision_sprites
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = PLAYER_SPEED
        
        # Dash system
        self.can_dash = True
        self.dash_time = pygame.time.get_ticks()
        self.dash_cooldown = PLAYER_DASH_COOLDOWN
        self.dash_duration = PLAYER_DASH_DURATION
        self.old_speed = self.speed
        self.is_dashing = False
        self.afterimages = []
        self.dash_speed_current = 0
        self.dash_start_speed = self.speed
        self.dash_target_speed = self.speed * PLAYER_DASH_SPEED_MULTIPLIER
        
        # Health system
        self.max_health = PLAYER_HEALTH
        self.health = PLAYER_HEALTH
        self.is_dying = False
        self.death_animation_complete = False
        
        # Ammo system
        self.magazine_size = PLAYER_MAGAZINE_SIZE
        self.current_ammo = self.magazine_size
        self.reloading = False
        self.reload_start_time = 0
        self.reload_duration = PLAYER_RELOAD_TIME
        
        # Combat stats
        self.base_bullet_damage = BULLET_DAMAGE
        self.current_bullet_damage = self.base_bullet_damage
        self.health_regen_amount = 0

    def load_images(self):
        self.frames = {
            state: {
                direction: []
                for direction in ['up', 'down', 'left', 'right']
            }
            for state in self.animation_states.keys()
        }
        
        # Load frames for each animation state and direction
        for state, folder_name in self.animation_states.items():
            try:
                base_folder_path = os.path.join('images', 'player', folder_name)
                for direction in ['up', 'down', 'left', 'right']:
                    dir_folder_path = os.path.join(base_folder_path, direction)
                    if not os.path.exists(dir_folder_path):
                        print(f"Warning: Direction folder not found: {dir_folder_path}")
                        continue
                        
                    for _, _, files in os.walk(dir_folder_path):
                        for file_name in sorted(files, key=lambda name: int(name.split('.')[0])):
                            if file_name.endswith('.png'):
                                path = os.path.join(dir_folder_path, file_name)
                                surf = pygame.image.load(path).convert_alpha()
                                self.frames[state][direction].append(surf)
                        break
                    
                    if not self.frames[state][direction]:
                        print(f"Warning: No frames loaded for player {state}/{direction} animation")
                        
            except FileNotFoundError as e:
                print(f"Warning: Animation folder not found: {e}")
            except ValueError as e:
                print(f"Error loading player frames: {e}")

    def load_buff_image_modifiers(self):
        for buff_key, buff_data in BUFF_DEFINITIONS.items():
            modifier_path = buff_data.get('player_image_modifier')
            if modifier_path:
                try:
                    self.buff_image_modifiers[buff_key] = pygame.image.load(modifier_path).convert_alpha()
                except pygame.error as e:
                    print(f"Warning: Could not load player buff modifier image for '{buff_key}' from '{modifier_path}': {e}")
                    self.buff_image_modifiers[buff_key] = None 

    def update_animation_state(self, dt):
        if self.is_dying:
            new_state = 'death'
        elif self.direction.length() > 0:
            new_state = 'walk'
            if abs(self.direction.x) > abs(self.direction.y):
                self.current_direction = 'right' if self.direction.x > 0 else 'left'
            else:
                self.current_direction = 'down' if self.direction.y > 0 else 'up'
            self.last_movement_direction = self.current_direction
        else:
            new_state = 'idle'
            self.current_direction = self.last_movement_direction

        if new_state != self.current_state:
            self.current_state = new_state
            self.frame_index = 0

        if self.frames[self.current_state][self.current_direction]:
            old_bottomleft = self.rect.bottomleft
            frames = self.frames[self.current_state][self.current_direction]
            self.frame_index = (self.frame_index + self.animation_speed * dt) % len(frames)
            self.image = frames[int(self.frame_index)]
            self.rect = self.image.get_frect(bottomleft=old_bottomleft)

            if self.is_dying and self.current_state == 'death' and int(self.frame_index) >= len(frames) - 1:
                self.death_animation_complete = True

    def animate(self, dt):
        self.update_animation_state(dt)
        
        for afterimage in self.afterimages[:]:
            afterimage.lifetime -= 1000 * dt
            if afterimage.lifetime <= 0:
                self.afterimages.remove(afterimage)
                
    def input(self, dt):
        if self.is_dying:
            return

        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        self.direction.y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()
            self.update_animation_state(dt)
        
        current_time = pygame.time.get_ticks()
        
        if keys[pygame.K_SPACE] and self.direction.length() > 0:
            if not self.is_dashing and current_time - self.dash_time >= self.dash_cooldown:
                self.start_dash()

        if keys[pygame.K_r] and not self.reloading and self.current_ammo < self.magazine_size:
            self.start_reload()

    def start_dash(self):
        if not self.is_dashing and self.direction.length() > 0:
            self.is_dashing = True
            self.dash_time = pygame.time.get_ticks()
            self.dash_speed_current = self.speed
            self.old_speed = self.speed

    def start_reload(self):
        self.reloading = True
        self.reload_start_time = pygame.time.get_ticks()
        print("Player reloading...")

    def update_reload(self):
        if self.reloading:
            current_time = pygame.time.get_ticks()
            if current_time - self.reload_start_time >= self.reload_duration:
                self.current_ammo = self.magazine_size
                self.reloading = False
                print("Player reload complete.")

    def dash(self, dt):
        current_time = pygame.time.get_ticks()
        dash_elapsed = current_time - self.dash_time
        
        if dash_elapsed < self.dash_duration:
            progress = dash_elapsed / self.dash_duration
            
            if progress < 0.5:
                ease_factor = 2 * progress * progress
            else:
                progress = 2 * progress - 1
                ease_factor = 1 - (1 - progress) * (1 - progress)
            
            target_speed = self.dash_target_speed
            self.speed = self.dash_start_speed + (target_speed - self.dash_start_speed) * ease_factor
            
            if current_time % int(max(5, 20 - self.speed/100)) < 5:
                alpha = int(150 * (1 - progress))
                afterimage = Afterimage(
                    self.rect.topleft,
                    self.image,
                    400,
                )
                afterimage.image.set_alpha(alpha)
                self.afterimages.append(afterimage)
            
            self.hitbox_rect.x += self.direction.x * self.speed * dt
            self.collision('horizontal')
            self.hitbox_rect.y += self.direction.y * self.speed * dt
            self.collision('vertical')
            self.rect.center = self.hitbox_rect.center
        else:
            self.is_dashing = False
            self.speed = self.old_speed

    def move(self, dt):
        if self.is_dashing:
            self.dash(dt)
        else:
            self.hitbox_rect.x += self.direction.x * self.speed * dt
            self.collision('horizontal')
            self.hitbox_rect.y += self.direction.y * self.speed * dt
            self.collision('vertical')
            self.rect.center = self.hitbox_rect.center
    
    def collision(self, direction):
        for sprite in self.collision_sprites:
            if self.hitbox_rect.colliderect(sprite.rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: 
                        self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: 
                        self.hitbox_rect.left = sprite.rect.right
                if direction == 'vertical':
                    if self.direction.y > 0: 
                        self.hitbox_rect.bottom = sprite.rect.top
                    if self.direction.y < 0: 
                        self.hitbox_rect.top = sprite.rect.bottom    
    
    def update_afterimages(self, dt):
        for afterimage in self.afterimages[:]:
            if afterimage.update(dt):
                self.afterimages.remove(afterimage)
    
    def draw_afterimages(self, screen, camera_offset):
        for afterimage in self.afterimages:
            screen_pos = afterimage.pos + camera_offset
            alpha = int((afterimage.lifetime / afterimage.max_lifetime) * 255)
            afterimage.image.set_alpha(alpha)
            screen.blit(afterimage.image, screen_pos)
            
        if self.is_dying and hasattr(self, '_death_frames_loaded'):
            screen_pos = pygame.math.Vector2(self.rect.topleft) + camera_offset
            self.death_frame.set_alpha(self._death_alpha)
            screen.blit(self.death_frame, screen_pos)

    def take_damage(self, amount):
        if self.is_dying: return False
        
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            return True
        return False

    def get_health_percentage(self):
        if self.max_health == 0: return 0
        return (self.health / self.max_health) * 100

    def apply_buff(self, buff_type_key):
        buff_data = BUFF_DEFINITIONS.get(buff_type_key)
        if not buff_data:
            print(f"Error: Cannot apply unknown buff type key: {buff_type_key}")
            return

        if buff_data['effect_type'] == 'instant_heal':
            heal_amount = buff_data['effect_value']
            self.health = min(self.health + heal_amount, self.max_health)
            print(f"Healed for {heal_amount} HP!")

        for active_buff in self.active_buffs:
            if active_buff.buff_type_key == buff_type_key:
                active_buff.start_time = pygame.time.get_ticks() 
                print(f"Refreshed buff: {buff_data['name']}")
                return 

        new_buff = ActiveBuff(buff_type_key)
        if new_buff.is_active: 
            self.active_buffs.append(new_buff)
            print(f"Applied new buff: {buff_data['name']}")

    def update_buffs(self, dt):        
        self.active_buffs = [buff for buff in self.active_buffs if not buff.is_expired()]
        self.reset_stats() 

        for buff in self.active_buffs:
            if buff.effect_type == 'speed':
                self.speed *= buff.effect_value 
            elif buff.effect_type == 'damage':
                self.current_bullet_damage *= buff.effect_value
            elif buff.effect_type == 'health_regen':
                self.health += buff.effect_value * dt 
                self.health = min(self.health, self.max_health) 

        self.speed = max(0, self.speed)
        self.current_bullet_damage = max(0, self.current_bullet_damage)

    def reset_stats(self):
        self.speed = self.old_speed
        self.current_bullet_damage = self.base_bullet_damage

    def get_modified_damage(self, base_damage):
        return self.current_bullet_damage

    def draw_buff_effects(self, screen, camera_offset):
        for active_buff in self.active_buffs:
            if active_buff.is_active:
                current_frame = active_buff.update_animation(1/60)
                if current_frame:
                    frame_rect = current_frame.get_rect(center=self.rect.center)
                    screen_pos = (frame_rect.x + camera_offset.x, frame_rect.y + camera_offset.y)
                    screen.blit(current_frame, screen_pos)

    def start_death_animation(self):
        if not self.is_dying:
            self.is_dying = True
            self.frame_index = 0
            self.current_state = 'death'  # Use death animation
            self.speed = 0  # Stop all movement
            print("Player death animation started")

    def update_death_animation(self, dt):
        if not self.is_dying:
            return

        if not hasattr(self, '_death_frames_loaded'):
            self.death_frame = self.frames['death'][self.current_direction][-1].copy()
            self._death_alpha = 255
            self._death_frames_loaded = True
        
        self._death_alpha = max(0, self._death_alpha - 300 * dt)  # Fade out in about 0.85 seconds
        self.image = self.death_frame.copy()
        self.image.set_alpha(self._death_alpha)
        
        if self._death_alpha <= 0:
            self.death_animation_complete = True

    def update(self, dt):
        if not self.is_dying:
            self.input(dt)
            self.move(dt)
            self.animate(dt)
            self.update_buffs(dt)
            self.update_reload()
        else:
            self.update_animation_state(dt)

