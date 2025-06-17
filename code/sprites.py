import pygame
from .settings import *
from math import degrees, atan2, cos, sin, pi as PI, radians
import random

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft=pos)
        self.ground = True

class CollisionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(topleft=pos)

class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        super().__init__(groups)
        self.player = player
        self.distance = 100
        self.player_direction = pygame.math.Vector2()
        self.original_image = self.player.game.gun_image
        self.image = self.original_image
        self.rect = self.image.get_rect(center=self.player.rect.center)

    def get_direction(self):
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        player_screen_center = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
        self.player_direction = mouse_pos - player_screen_center
        if self.player_direction.length() != 0:
            self.player_direction = self.player_direction.normalize()

    def rotate_gun(self):
        if self.player_direction.length_squared() == 0:
            return

        angle = degrees(atan2(-self.player_direction.y, self.player_direction.x))
        flip = self.player_direction.x < 0
        image = pygame.transform.flip(self.original_image, False, True) if flip else self.original_image
        rotated_image = pygame.transform.rotate(image, angle)
        offset = self.player_direction * self.distance
        
        self.image = rotated_image
        self.rect = self.image.get_rect(center=self.player.rect.center + offset)

    def update(self, _):
        self.get_direction()
        self.rotate_gun()

class Bullet(pygame.sprite.Sprite):
    def __init__(self, surf, pos, direction, groups, damage=BULLET_DAMAGE):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_frect(center=pos)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = BULLET_LIFETIME
        self.direction = direction
        self.speed = BULLET_SPEED
        self.damage = damage

    def update(self, dt):
        self.rect.center += self.direction * self.speed * dt
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, collision_sprites, health):
        super().__init__(groups)
        self.player = player
        self.frames = frames['idle'] if isinstance(frames, dict) and 'idle' in frames else frames if isinstance(frames, list) else []
        self.frame_index = 0
        self.image = self.frames[self.frame_index] if self.frames else pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        self.animation_speed = ENEMY_ANIMATION_SPEED
        self.rect = self.image.get_frect(bottomleft=pos)
        self.hitbox_rect = self.rect.inflate(-self.rect.width * 0.4, -self.rect.height * 0.5)
        self.hitbox_rect.bottom = self.rect.bottom
        self.collision_sprites = collision_sprites
        self.direction = pygame.math.Vector2()
        self.max_health = health
        self.health = health
        self.death_time = 0
        self.death_animation_duration = ENEMY_DEATH_DURATION
        self.is_triggered = False
        self.vision_range = ENEMY_DEFAULT_VISION_RANGE
        self.speed = ENEMY_DEFAULT_SPEED

    def animate(self, dt):
        if self.frames:
            self.frame_index += self.animation_speed * dt
            self.image = self.frames[int(self.frame_index) % len(self.frames)]

    def collision(self, direction_axis):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction_axis == 'horizontal':
                    if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                if direction_axis == 'vertical':
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top
                    if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom

    def take_damage(self, amount):
        if self.death_time > 0: return False
        self.health = max(0, self.health - amount)
        if self.health == 0:
            self.start_death_animation()
            return True
        return False

    def start_death_animation(self):
        self.death_time = pygame.time.get_ticks()
        self.speed = 0

    def death_timer(self):
        if self.death_time > 0 and pygame.time.get_ticks() - self.death_time >= self.death_animation_duration:
            self.kill()

    def get_health_percentage(self):
        return (self.health / self.max_health) * 100 if self.max_health > 0 else 0

    def distance_to_player(self):
        return pygame.math.Vector2(self.player.rect.center).distance_to(pygame.math.Vector2(self.rect.center))

    def move_towards_player(self, dt, speed_multiplier=1.0):
        if self.death_time != 0: return

        distance = self.distance_to_player()
        if not self.is_triggered and distance <= self.vision_range:
            self.is_triggered = True

        if self.is_triggered:
            player_pos = pygame.math.Vector2(self.player.rect.center)
            enemy_pos = pygame.math.Vector2(self.rect.center)
            self.direction = (player_pos - enemy_pos).normalize() if (player_pos - enemy_pos).length_squared() > 0 else pygame.math.Vector2()
            
            self.hitbox_rect.x += self.direction.x * self.speed * speed_multiplier * dt
            self.collision('horizontal')
            self.hitbox_rect.y += self.direction.y * self.speed * speed_multiplier * dt
            self.collision('vertical')
            self.rect.bottomleft = self.hitbox_rect.bottomleft
        else:
            self.direction = pygame.math.Vector2()

    def update(self, dt):
        if self.death_time == 0:
            self.animate(dt)
        else:
            self.death_timer()

class MeleeEnemy(Enemy):
    def __init__(self, pos, frames, groups, player, collision_sprites, health=MELEE_ENEMY_HEALTH):
        super().__init__(pos, frames, groups, player, collision_sprites, health)
        self.speed = MELEE_ENEMY_SPEED
        self.vision_range = MELEE_ENEMY_VISION_RANGE
        self.contact_damage = MELEE_ENEMY_CONTACT_DAMAGE
        self.is_player_hit_this_attack = False
        self.damage_cooldown = MELEE_ENEMY_DAMAGE_COOLDOWN
        self.last_damage_time = 0
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt):
        super().update(dt)
        if self.death_time == 0:
            self.move_towards_player(dt)
            current_time = pygame.time.get_ticks()
            if pygame.sprite.collide_mask(self, self.player):
                if current_time - self.last_damage_time >= self.damage_cooldown:
                    self.player.take_damage(self.contact_damage)
                    self.last_damage_time = current_time

class RangedEnemy(Enemy):
    def __init__(self, pos, frames, groups, player, collision_sprites, health=RANGED_ENEMY_HEALTH):
        super().__init__(pos, frames, groups, player, collision_sprites, health)
        self.attack_direction = pygame.math.Vector2()
        
        self.shoot_cooldown = RANGED_ENEMY_SHOOT_COOLDOWN
        self.delay_attack_duration = RANGED_ENEMY_DELAY_ATTACK
        self.last_shoot_time = 0
        self.can_shoot = True
        self.speed = RANGED_ENEMY_SPEED
        self.vision_range = RANGED_ENEMY_VISION_RANGE
        self.is_player_hit_this_attack = False
        
        self.aiming_duration = RANGED_ENEMY_AIMING_DURATION
        self.laser_duration = RANGED_ENEMY_LASER_DURATION
        self.attack_phase = 'idle'
        self.phase_start_time = 0
        self.laser_visual_width = RANGED_ENEMY_LASER_WIDTH
        self.laser_damage = RANGED_ENEMY_LASER_DAMAGE

    def move_normally(self, dt, speed_multiplier=1.0):
        if self.death_time != 0: return

        if (self.attack_phase in ('idle', 'cooldown') or not self.is_triggered) and self.distance_to_player() > self.vision_range:            
            self.move_towards_player(dt, speed_multiplier)
        elif self.attack_phase in ('idle', 'cooldown'): 
            self.direction = pygame.math.Vector2()

    def update_attack_direction_and_state(self):
        self.player_world_pos = pygame.math.Vector2(self.player.rect.center)
        self.enemy_world_pos = pygame.math.Vector2(self.rect.center)
        
        if self.attack_phase == 'aiming':
            if (self.player_world_pos - self.enemy_world_pos).length_squared() > 0:
                self.attack_direction = (self.player_world_pos - self.enemy_world_pos).normalize()
            else:
                self.attack_direction = pygame.math.Vector2(1,0)

    def attack_logic(self, dt):
        if self.death_time != 0: return

        self.update_attack_direction_and_state()
        current_time = pygame.time.get_ticks()
        distance = self.distance_to_player()

        if not self.is_triggered and distance <= self.vision_range:
            self.is_triggered = True

        # Attack logic
        if self.is_triggered:
            if self.attack_phase == 'idle':
                if self.can_shoot and distance <= self.vision_range:
                    self.start_aiming()
                else:
                    self.move_normally(dt) 
            
            elif self.attack_phase == 'aiming':
                if current_time - self.phase_start_time >= self.aiming_duration:
                    self.start_delaying()
            
            elif self.attack_phase == 'delaying':
                if current_time - self.phase_start_time >= self.delay_attack_duration:
                    self.start_firing()
            
            elif self.attack_phase == 'firing':
                if current_time - self.phase_start_time >= self.laser_duration:
                    self.end_firing_and_cooldown()
                else:
                    if not self.is_player_hit_this_attack:
                        if self.check_laser_collision():
                            self.player.take_damage(self.laser_damage)
                            self.is_player_hit_this_attack = True
            
            elif self.attack_phase == 'cooldown':
                self.move_normally(dt)
                if current_time - self.last_shoot_time >= self.shoot_cooldown:
                    self.can_shoot = True
                    self.attack_phase = 'idle'

    def start_aiming(self):
        self.attack_phase = 'aiming'
        self.phase_start_time = pygame.time.get_ticks()
        self.can_shoot = False
        if (self.player_world_pos - self.enemy_world_pos).length_squared() > 0:
            self.attack_direction = (self.player_world_pos - self.enemy_world_pos).normalize()
        else:
            self.attack_direction = pygame.math.Vector2(1,0)

    def start_delaying(self):
        self.attack_phase = 'delaying'
        self.phase_start_time = pygame.time.get_ticks()

    def start_firing(self):
        self.attack_phase = 'firing'
        self.phase_start_time = pygame.time.get_ticks()
        self.is_player_hit_this_attack = False

    def end_firing_and_cooldown(self):
        self.attack_phase = 'cooldown'
        self.last_shoot_time = pygame.time.get_ticks()

    def draw_attack(self):
        if self.attack_phase not in ('aiming', 'delaying', 'firing') or self.attack_direction.length_squared() == 0:
            return None, None

        color = None
        thickness = 0
        length = self.vision_range * 2

        if self.attack_phase == 'aiming':
            color = (255, 255, 0, 100)
            thickness = max(1, int(self.laser_visual_width / 6))
        elif self.attack_phase == 'delaying':
            color = (255, 150, 0, 180)
            thickness = max(2, int(self.laser_visual_width / 3))
        elif self.attack_phase == 'firing':
            color = (255, 0, 0, 220)
            thickness = self.laser_visual_width
        
        if color and thickness > 0:
            line_surf = pygame.Surface((length, thickness), pygame.SRCALPHA)
            line_surf.fill((0,0,0,0))
            pygame.draw.line(line_surf, color, (0, thickness // 2), (length, thickness // 2), thickness)
            max_dim = int(length + thickness) * 2
            final_surf = pygame.Surface((max_dim, max_dim), pygame.SRCALPHA)
            final_surf.fill((0,0,0,0))

            center_of_final_surf = (max_dim // 2, max_dim // 2)
            end_point_on_final_surf = (center_of_final_surf[0] + self.attack_direction.x * length,
                                       center_of_final_surf[1] + self.attack_direction.y * length)
            pygame.draw.line(final_surf, color, center_of_final_surf, end_point_on_final_surf, thickness)            
            world_topleft = (self.rect.centerx - center_of_final_surf[0], 
                             self.rect.centery - center_of_final_surf[1])

            return final_surf, world_topleft
            
        return None, None

    def check_laser_collision(self):
        if self.attack_phase != 'firing' or self.attack_direction.length_squared() == 0:
            return False
        
        player_hitbox = self.player.hitbox_rect
        enemy_center = pygame.math.Vector2(self.rect.center)        
        vec_ep = pygame.math.Vector2(player_hitbox.center) - enemy_center
        projection_length = vec_ep.dot(self.attack_direction)
        
        if not (0 <= projection_length <= self.vision_range):
            return False
            
        perpendicular_distance = (vec_ep - projection_length * self.attack_direction).length()       
        effective_collision_dist = (self.laser_visual_width / 2) + (min(player_hitbox.width, player_hitbox.height) / 2)
        
        if perpendicular_distance < effective_collision_dist:
            return True
        return False

    def update(self, dt):
        super().update(dt)
        if self.death_time == 0:
            self.attack_logic(dt)

class ChargerEnemy(Enemy):
    def __init__(self, pos, frames, groups, player, collision_sprites, health=CHARGER_ENEMY_HEALTH):
        super().__init__(pos, frames, groups, player, collision_sprites, health)
        
        self.attack_phase = 'idle'
        self.vision_range = CHARGER_ENEMY_VISION_RANGE
        
        self.normal_speed = CHARGER_ENEMY_NORMAL_SPEED
        self.charge_actual_speed = CHARGER_ENEMY_CHARGE_SPEED
        self.current_speed = self.normal_speed
        self.speed = self.normal_speed

        self.locking_duration = CHARGER_ENEMY_CHARGE_TIME
        self.delay_duration = CHARGER_ENEMY_DELAY_ATTACK
        self.charge_move_duration = CHARGER_ENEMY_CHARGE_DURATION
        self.charge_cooldown_duration = CHARGER_ENEMY_CHARGE_COOLDOWN

        self.phase_start_time = 0
        self.last_charge_end_time = 0
        
        self.attack_indicator_radius = CHARGER_ENEMY_ATTACK_RADIUS
        self.charge_damage = CHARGER_ENEMY_CHARGE_DAMAGE

        self.locked_target_pos = pygame.math.Vector2()
        self.charge_move_direction = pygame.math.Vector2()
        
        self.can_attack = True
        self.is_player_hit_this_charge = False

    def move_standard(self, dt): 
        if self.death_time != 0: return

        if self.distance_to_player() > self.vision_range:
            self.move_towards_player(dt)
        else:
            self.direction = pygame.math.Vector2()

    def update_state_and_positions(self):
        self.player_world_pos = pygame.math.Vector2(self.player.rect.center)
        self.enemy_world_pos = pygame.math.Vector2(self.rect.center)
        
        if self.attack_phase == 'locking':
            self.locked_target_pos = self.player_world_pos 
            if (self.locked_target_pos - self.enemy_world_pos).length_squared() > 0:
                self.charge_move_direction = (self.locked_target_pos - self.enemy_world_pos).normalize()
            else:
                self.charge_move_direction = pygame.math.Vector2(1,0) 

    def attack_and_movement_logic(self, dt):
        if self.death_time != 0: return

        self.update_state_and_positions()
        current_time = pygame.time.get_ticks()
        distance = self.distance_to_player()

        if not self.is_triggered and distance <= self.vision_range:
            self.is_triggered = True

        if self.is_triggered:
            if self.attack_phase == 'idle':
                self.current_speed = self.normal_speed
                if self.can_attack and distance <= self.vision_range:
                    self.start_locking_phase()
                else:
                    self.move_standard(dt) 

            elif self.attack_phase == 'locking':
                self.current_speed = self.normal_speed * 0.5 
                if self.charge_move_direction.length_squared() > 0:
                    self.hitbox_rect.x += self.charge_move_direction.x * self.current_speed * dt
                    self.collision('horizontal')
                    self.hitbox_rect.y += self.charge_move_direction.y * self.current_speed * dt
                    self.collision('vertical')
                    self.rect.center = self.hitbox_rect.center
                else: 
                    self.direction = pygame.math.Vector2()

                if current_time - self.phase_start_time >= self.locking_duration:
                    self.start_delaying_phase()

            elif self.attack_phase == 'delaying':
                self.current_speed = 0 
                self.direction = pygame.math.Vector2()
                if current_time - self.phase_start_time >= self.delay_duration:
                    self.start_charging_phase()

            elif self.attack_phase == 'charging':
                self.current_speed = self.charge_actual_speed
                self.execute_charge_move(dt)
                self.check_charge_hit_player()
                if current_time - self.phase_start_time >= self.charge_move_duration or \
                self.enemy_world_pos.distance_to(self.locked_target_pos) < self.current_speed * dt * 0.5 : 
                    self.end_charge_and_cooldown()
            
            elif self.attack_phase == 'cooldown':
                self.current_speed = self.normal_speed
                self.move_standard(dt) 
                if current_time - self.last_charge_end_time >= self.charge_cooldown_duration:
                    self.can_attack = True
                    self.attack_phase = 'idle'
    
    def start_locking_phase(self):
        self.attack_phase = 'locking'
        self.phase_start_time = pygame.time.get_ticks()
        self.can_attack = False 
        self.locked_target_pos = pygame.math.Vector2(self.player.rect.center)
        if (self.locked_target_pos - self.enemy_world_pos).length_squared() > 0:
            self.charge_move_direction = (self.locked_target_pos - self.enemy_world_pos).normalize()
        else:
            self.charge_move_direction = pygame.math.Vector2(1,0)
            
    def start_delaying_phase(self):
        self.attack_phase = 'delaying'
        self.phase_start_time = pygame.time.get_ticks()

    def start_charging_phase(self):
        self.attack_phase = 'charging'
        self.phase_start_time = pygame.time.get_ticks()
        self.is_player_hit_this_charge = False 

    def end_charge_and_cooldown(self):
        self.attack_phase = 'cooldown'
        self.last_charge_end_time = pygame.time.get_ticks()
        self.current_speed = self.normal_speed

    def execute_charge_move(self, dt):
        if self.charge_move_direction.length_squared() == 0: 
            self.end_charge_and_cooldown() 
            return

        self.hitbox_rect.x += self.charge_move_direction.x * self.current_speed * dt
        self.hitbox_rect.y += self.charge_move_direction.y * self.current_speed * dt
        self.collision('horizontal')
        self.rect.center = self.hitbox_rect.center
        
    def check_charge_hit_player(self):
        if not self.is_player_hit_this_charge:
            if pygame.sprite.collide_mask(self, self.player):
                self.player.take_damage(self.charge_damage)
                self.is_player_hit_this_charge = True

    def draw_attack_indicator(self):
        if self.attack_phase not in ('locking', 'delaying', 'charging'):
            return None, None
            
        indicator_diameter = self.attack_indicator_radius * 2
        indicator_center_world = None 
        color = None
        line_thickness = 0 

        if self.attack_phase == 'locking':
            color = (255, 255, 0, 100)  
            line_thickness = 3 
            indicator_center_world = self.player_world_pos 
        elif self.attack_phase == 'delaying':
            color = (255, 100, 0, 180) 
            line_thickness = 0 
            indicator_center_world = self.locked_target_pos 
        elif self.attack_phase == 'charging':
            color = (200, 0, 0, 150) 
            line_thickness = 0
            indicator_center_world = self.locked_target_pos

        if color and indicator_center_world:
            indicator_surf = pygame.Surface((indicator_diameter, indicator_diameter), pygame.SRCALPHA)
            indicator_surf.fill((0,0,0,0)) 
            pygame.draw.circle(indicator_surf, color, 
                               (self.attack_indicator_radius, self.attack_indicator_radius), 
                               self.attack_indicator_radius, 
                               line_thickness) 
            
            indicator_world_topleft = (indicator_center_world.x - self.attack_indicator_radius, 
                                       indicator_center_world.y - self.attack_indicator_radius)
            
            return indicator_surf, indicator_world_topleft
            
        return None, None

    def update(self, dt):
        super().update(dt) 
        if self.death_time == 0: 
            self.attack_and_movement_logic(dt)
            
class BossEnemy(Enemy):
    def __init__(self, pos, frames, groups, player, collision_sprites, damaging_zone_group, all_sprites_group, bullet_group):
        super().__init__(pos, frames, groups, player, collision_sprites, health=BOSS_HEALTH)
        self.damaging_zone_group = damaging_zone_group
        self.all_sprites_group = all_sprites_group
        self.bullet_group = bullet_group
        self.is_triggered = False
        self.game = self.player.game

        self.all_frames = frames
        self.area_effect_frames = self.game.boss_skill_frames.get('skill2', [])
        self.fireball_frames = self.game.boss_skill_frames.get('skill3', [])

        self.vision_range = BOSS_VISION_RANGE
        self.speed = BOSS_SPEED

        self.animation_states = {
            'idle': 'idle',
            'summon': 'skill1',
            'area_attack': 'skill2',
            'fireball': 'skill3',
            'death': 'death'
        }
        self.current_frames_key = 'idle'
        
        # Death animation
        self.is_dying = False
        self.death_frame_index = 0
        self.death_animation_complete = False

        # Skill system setup
        self.current_skill = None
        self.skill_phase = 'idle'
        self.skill_start_time = 0
        self.time_since_last_skill = 0
        self.time_between_skills = BOSS_TIME_BETWEEN_SKILLS

        # Available skills in order
        self.available_skills = ['summon', 'area_attack', 'fireball']
        self.current_skill_index = 0

        # Summon skill attributes
        self.summon_positions = []
        self.enemy_types = ['skeleton', 'blob', 'bat']
        self.summoned_enemies = []

        # Area attack skill attributes
        self.damage_squares = []
        self.player_stationary_time = 0
        self.player_move_threshold = 50

        # Fireball skill attributes
        self.fireball_count = 0
        self.last_fireball_time = 0

    def update_animation_state(self, dt):
        if self.is_dying:
            self.current_frames_key = 'death'
        elif self.current_skill and self.skill_phase in ['warning', 'active']:
            self.current_frames_key = self.animation_states.get(self.current_skill, 'idle')
        else:
            self.current_frames_key = 'idle'

        # Update frames and image with bottomleft position
        if self.current_frames_key in self.all_frames and self.all_frames[self.current_frames_key]:
            self.frames = self.all_frames[self.current_frames_key]
            old_bottomleft = self.rect.bottomleft
            self.frame_index = (self.frame_index + self.animation_speed * dt) % len(self.frames)
            self.image = self.frames[int(self.frame_index)]
            self.rect = self.image.get_frect(bottomleft=old_bottomleft)

    def take_damage(self, amount):
        if self.death_time > 0: return False
        
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.start_death_animation()
            return True
        return False

    def start_death_animation(self):
        if not self.is_dying:
            self.is_dying = True
            self.death_frame_index = 0
            self.current_frames_key = 'death'
            self.speed = 0
            self.current_skill = None
            print("Boss death animation started")

    def update_death_animation(self, dt):
        if not self.is_dying:
            return

        death_frames = self.all_frames.get('death', [])
        if not death_frames:
            self.death_animation_complete = True
            return

        # Update frame index
        self.death_frame_index += self.animation_speed * dt
        frame_number = int(self.death_frame_index)
        
        # Check if animation is complete
        if frame_number >= len(death_frames):
            self.death_animation_complete = True
            return
        
        # Update image to current death frame
        self.image = death_frames[frame_number]

    def update(self, dt):
        # Handle death animation
        if self.is_dying:
            self.update_death_animation(dt)
            return

        if not self.is_triggered:
            if self.distance_to_player() <= self.vision_range:
                self.is_triggered = True
                print("Boss has been triggered!")
            return

        self.update_animation_state(dt)   
        self.update_movement(dt)
        self.update_skills(dt)

    def shoot_fireball(self):
        if self.death_time > 0: return
        
        to_player = pygame.math.Vector2(self.player.rect.center) - pygame.math.Vector2(self.rect.center)
        if to_player.length_squared() > 0:
            direction = to_player.normalize()
        else:
            direction = pygame.math.Vector2(1, 0)  # Default direction if at same position
            
        # Create fireball sprite
        if hasattr(self, 'fireball_frames') and self.fireball_frames:
            print(f"Boss has {len(self.fireball_frames)} frames for fireball animation")
            
            # Create a simple sprite for the fireball
            fireball = pygame.sprite.Sprite()
            fireball.frames = self.fireball_frames
            fireball.frame_index = 0
            fireball.animation_speed = 0.2
            fireball.image = self.fireball_frames[0]
            fireball.rect = fireball.image.get_rect(center=self.rect.center)
            fireball.direction = direction
            fireball.speed = BOSS_FIREBALL_SPEED
            fireball.damage = BOSS_FIREBALL_DAMAGE
            fireball.distance_traveled = 0
            fireball.max_distance = self.vision_range * 2  # Maximum travel distance
            fireball.mask = pygame.mask.from_surface(fireball.image)
            fireball.has_hit_player = False
            
            def update_fireball(dt):
                fireball.frame_index = (fireball.frame_index + fireball.animation_speed) % len(fireball.frames)
                fireball.image = fireball.frames[int(fireball.frame_index)]
                fireball.mask = pygame.mask.from_surface(fireball.image)
                
                movement = fireball.direction * fireball.speed * dt
                fireball.rect.x += movement.x
                fireball.rect.y += movement.y
                fireball.distance_traveled += movement.length()
                
                if not fireball.has_hit_player and pygame.sprite.collide_mask(fireball, self.player):
                    self.player.take_damage(fireball.damage)
                    fireball.has_hit_player = True
                    fireball.kill()
                
                if fireball.distance_traveled >= fireball.max_distance:
                    fireball.kill()
            
            fireball.update = update_fireball
            self.all_sprites_group.add(fireball)
            print("Created simple fireball sprite")
        else:
            print("No fireball_frames available for fireball")

    def draw_area_attack(self, surface_to_draw_on, camera_offset):
        if self.current_skill != 'area_attack' or not self.damage_squares:
            return
        
        for square in self.damage_squares:
            screen_pos = (
                int(square['pos'].x + camera_offset.x),
                int(square['pos'].y + camera_offset.y)
            )
            
            if self.skill_phase == 'warning':
                warning_surf = pygame.Surface((TILE_SIZE * 4, TILE_SIZE * 4), pygame.SRCALPHA)
                
                pygame.draw.circle(warning_surf, (255, 0, 0, square['warning_alpha']), 
                                (TILE_SIZE * 2, TILE_SIZE * 2), TILE_SIZE * 1.9)
                
                surface_to_draw_on.blit(warning_surf, 
                                    (screen_pos[0] - TILE_SIZE * 2, screen_pos[1] - TILE_SIZE * 2))
                
            elif self.skill_phase == 'active':
                if hasattr(self, 'area_effect_frames') and self.area_effect_frames:
                    square['current_frame'] = (square['current_frame'] + square['animation_speed']) % len(self.area_effect_frames)
                    current_frame = self.area_effect_frames[int(square['current_frame'])]
                    
                    if current_frame.get_size() != (TILE_SIZE * 4, TILE_SIZE * 4):
                        current_frame = pygame.transform.scale(current_frame, (TILE_SIZE * 4, TILE_SIZE * 4))
                    
                    surface_to_draw_on.blit(current_frame,
                                        (screen_pos[0] - TILE_SIZE * 2, screen_pos[1] - TILE_SIZE * 2))

    def execute_area_attack(self):
        if self.skill_phase == 'warning':
            if pygame.time.get_ticks() - self.skill_start_time >= BOSS_ZONES_WARNING_DURATION:
                self.skill_phase = 'active'
                self.skill_start_time = pygame.time.get_ticks()

        elif self.skill_phase == 'active':
            current_time = pygame.time.get_ticks()
            for square in self.damage_squares:
                if square['rect'].colliderect(self.player.hitbox_rect):
                    if current_time - square['last_damage_time'] >= square['damage_cooldown']:
                        self.player.take_damage(BOSS_ZONE_DAMAGE_PER_TICK)
                        square['last_damage_time'] = current_time

            if current_time - self.skill_start_time >= BOSS_ZONES_ACTIVE_DURATION:
                self.skill_phase = 'cooldown'
                self.skill_start_time = current_time

        elif self.skill_phase == 'cooldown':
            if pygame.time.get_ticks() - self.skill_start_time >= BOSS_SKILL_COOLDOWN_AFTER_ZONES:
                self.current_skill = None
                self.skill_phase = 'idle'

    def execute_fireball(self):
        current_time = pygame.time.get_ticks()
        
        if self.skill_phase == 'warning':
            if current_time - self.skill_start_time >= BOSS_FIREBALL_WARNING_DURATION:
                self.skill_phase = 'active'
                self.skill_start_time = current_time
                self.last_fireball_time = current_time
                
        elif self.skill_phase == 'active':
            if current_time - self.last_fireball_time >= BOSS_FIREBALL_DELAY:
                if self.fireball_count < BOSS_FIREBALL_COUNT:
                    self.shoot_fireball()
                    self.last_fireball_time = current_time
                    self.fireball_count += 1
                else:
                    self.skill_phase = 'cooldown'
                    self.skill_start_time = current_time
                    
        elif self.skill_phase == 'cooldown':
            if current_time - self.skill_start_time >= BOSS_FIREBALL_COOLDOWN:
                self.current_skill = None
                self.skill_phase = 'idle'
                self.fireball_count = 0

    def update_movement(self, dt):
        if self.death_time > 0 or self.is_dying: return
        # Only move when not performing skills
        if self.current_skill is None and self.skill_phase == 'idle':
            distance = self.distance_to_player()
            ideal_distance = self.vision_range * 0.7 
            
            if abs(distance - ideal_distance) > 5: 
                player_pos = pygame.math.Vector2(self.player.rect.center)
                boss_pos = pygame.math.Vector2(self.rect.center)
                to_player = player_pos - boss_pos
                
                if to_player.length_squared() > 0:
                    self.direction = to_player.normalize()
                    
                    if distance > ideal_distance:
                        # Move towards player   
                        self.hitbox_rect.x += self.direction.x * self.speed * dt
                        self.collision('horizontal')
                        self.hitbox_rect.y += self.direction.y * self.speed * dt
                        self.collision('vertical')
                    else:
                        # Move away from player
                        self.hitbox_rect.x -= self.direction.x * self.speed * dt
                        self.direction.x *= -1
                        self.collision('horizontal')
                        self.direction.x *= -1
                        
                        self.hitbox_rect.y -= self.direction.y * self.speed * dt
                        self.direction.y *= -1
                        self.collision('vertical')
                        self.direction.y *= -1
                    
                    self.rect.bottomleft = self.hitbox_rect.bottomleft

    def update_skills(self, dt):
        if self.death_time > 0: return
        current_time = pygame.time.get_ticks()

        current_player_pos = pygame.math.Vector2(self.player.rect.center)
        if not hasattr(self, 'last_player_pos'):
            self.last_player_pos = current_player_pos
            self.player_stationary_time = current_time
        
        player_movement = (current_player_pos - self.last_player_pos).length()
        if player_movement > self.player_move_threshold:
            self.player_stationary_time = current_time
        self.last_player_pos = current_player_pos

        if self.skill_phase == 'idle':
            self.time_since_last_skill += dt * 1000
            if self.time_since_last_skill >= self.time_between_skills:
                next_skill = self.choose_next_skill()
                print(f"Choosing next skill: {next_skill}")
                
                self.current_skill = next_skill
                if self.current_skill:
                    self.skill_phase = 'warning'
                    self.skill_start_time = current_time
                    self.time_since_last_skill = 0
                    print(f"Starting skill {self.current_skill} in warning phase")
                    
                    if self.current_skill == 'summon':
                        self.prepare_summon_positions()
                    elif self.current_skill == 'area_attack':
                        print("Preparing area attack")
                        self.prepare_area_attack()
                        print(f"Area attack prepared with {len(self.damage_squares)} squares")
                    elif self.current_skill == 'fireball':
                        self.fireball_count = 0
                        self.last_fireball_time = current_time

        elif self.skill_phase == 'warning':
            warning_duration = 1000
            if current_time - self.skill_start_time >= warning_duration:
                print(f"Transitioning {self.current_skill} from warning to active phase")
                self.skill_phase = 'active'
                self.skill_start_time = current_time

        elif self.skill_phase == 'active':
            if self.current_skill == 'summon':
                self.execute_summon()
                self.skill_phase = 'cooldown'
                self.time_between_skills = 2000 
            elif self.current_skill == 'area_attack':
                self.execute_area_attack()
            elif self.current_skill == 'fireball':
                self.execute_fireball()

        elif self.skill_phase == 'cooldown':
            if current_time - self.skill_start_time >= self.time_between_skills:
                self.skill_phase = 'idle'
                self.current_skill = None

    def prepare_summon_positions(self):
        # Calculate 3 positions around the boss
        angles = [0, 120, 240]
        distance = TILE_SIZE * 3
        self.summon_positions = []
        boss_pos = pygame.math.Vector2(self.rect.center)
        
        for angle in angles:
            rad = radians(angle)
            pos = boss_pos + pygame.math.Vector2(cos(rad), sin(rad)) * distance
            self.summon_positions.append(pos)

    def execute_summon(self):
        from random import choice
        for pos in self.summon_positions:
            enemy_type = choice(self.enemy_types)
            enemy_config = self.game.enemy_data[enemy_type]
            
            enemy = enemy_config['class'](
                pos=pos,
                frames=self.game.enemy_frames[enemy_type],
                groups=(self.game.all_sprites, self.game.enemy_sprites),
                player=self.player,
                collision_sprites=self.game.collision_sprites,
                health=enemy_config['health']
            )
            
            # Trigger the enemy immediately
            if hasattr(enemy, 'is_triggered'):
                enemy.is_triggered = True
            self.summoned_enemies.append(enemy)

    def prepare_area_attack(self):
        self.damage_squares = []
        player_pos = pygame.math.Vector2(self.player.rect.center)
        
        for _ in range(BOSS_ZONE_COUNT):
            angle = random.uniform(0, 2 * PI)
            distance = random.uniform(TILE_SIZE * 4, TILE_SIZE * 10)
            
            offset = pygame.math.Vector2(cos(angle) * distance, sin(angle) * distance)
            pos = player_pos + offset
            
            square = {
                'pos': pos,
                'rect': pygame.Rect(pos.x - TILE_SIZE, pos.y - TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2),
                'active': False,
                'warning_alpha': 128,
                'current_frame': 0,
                'animation_speed': 0.2,
                'damage_cooldown': BOSS_ZONE_TICK_INTERVAL,
                'last_damage_time': 0
            }
            self.damage_squares.append(square)

    def choose_next_skill(self):
        skill_name = self.available_skills[self.current_skill_index]
        self.current_skill_index = (self.current_skill_index + 1) % len(self.available_skills)
        print(f"Boss choosing skill: {skill_name}")
        return skill_name

    def draw_active_skill_effects(self, surface_to_draw_on, camera_offset):
        if self.current_skill == 'area_attack':
            self.draw_area_attack(surface_to_draw_on, camera_offset)
            