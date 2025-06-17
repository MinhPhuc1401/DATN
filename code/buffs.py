import pygame
from os.path import join
import random
import os

BUFF_DEFINITIONS = {
    'speed_boost': {
        'name': 'Speed Boost',
        'item_image': join('images', 'effects', 'buffs_item', 'speed_item.png'),
        'effect_folder': join('images', 'effects', 'buffs_effects', 'speed'),
        'duration': 10000,
        'effect_type': 'speed',
        'effect_value': 1.5,
        'description': 'Increases movement speed.',
        'animation_speed': 0.2
    },
    'damage_boost': {
        'name': 'Damage Boost',
        'item_image': join('images', 'effects', 'buffs_item', 'damage_item.png'),
        'effect_folder': join('images', 'effects', 'buffs_effects', 'damage'),
        'duration': 10000,
        'effect_type': 'damage',
        'effect_value': 2.0,
        'description': 'Increases bullet damage.',
        'animation_speed': 0.2
    },
    'health_regen': {
        'name': 'Instant Heal',
        'item_image': join('images', 'effects', 'buffs_item', 'health_item.png'),
        'effect_folder': join('images', 'effects', 'buffs_effects', 'health'),
        'duration': 3000,
        'effect_type': 'instant_heal',
        'effect_value': 25,
        'description': 'Instantly heals 25 HP.',
        'animation_speed': 0.2
    }
}

def load_effect_frames(folder_path):
    frames = []
    try:
        files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
        files.sort(key=lambda x: int(x.split('.')[0]))
        
        for file in files:
            frame_path = os.path.join(folder_path, file)
            try:
                frame = pygame.image.load(frame_path).convert_alpha()
                frames.append(frame)
            except pygame.error as e:
                print(f"Error loading frame {file}: {e}")
                
    except FileNotFoundError:
        print(f"Effect folder not found: {folder_path}")
    except ValueError as e:
        print(f"Error parsing frame numbers in {folder_path}: {e}")
        
    return frames

def get_random_buff_type():
    if not BUFF_DEFINITIONS:
        return None
    return random.choice(list(BUFF_DEFINITIONS.keys()))

class BuffItem(pygame.sprite.Sprite):
    def __init__(self, pos, buff_type_key, groups):
        super().__init__(groups)
        self.buff_type_key = buff_type_key
        self.buff_data = BUFF_DEFINITIONS.get(buff_type_key)
        
        if not self.buff_data:
            print(f"Error: Buff type key '{buff_type_key}' not found in BUFF_DEFINITIONS.")
            self.kill()
            return

        try:
            self.image = pygame.image.load(self.buff_data['item_image']).convert_alpha()
        except pygame.error as e:
            print(f"Error loading buff item image for '{buff_type_key}': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((0, 255, 255))
            
        self.rect = self.image.get_frect(center = pos)
        self.hitbox_rect = self.rect.inflate(-10, -10) 

    def update(self, dt):
        pass

class ActiveBuff:
    def __init__(self, buff_type_key):
        self.buff_type_key = buff_type_key
        self.buff_data = BUFF_DEFINITIONS.get(buff_type_key)
        if not self.buff_data:
            print(f"Error: Active buff type key '{buff_type_key}' not found.")
            self.is_active = False
            return
            
        self.start_time = pygame.time.get_ticks()
        self.duration = self.buff_data['duration']
        self.effect_type = self.buff_data['effect_type']
        self.effect_value = self.buff_data['effect_value']
        
        self.effect_frames = load_effect_frames(self.buff_data['effect_folder'])
        self.current_frame = 0
        self.animation_speed = self.buff_data.get('animation_speed', 0.2)
        self.frame_time = 0
        
        self.is_active = True
        
    def update_animation(self, dt):
        if not self.effect_frames:
            return None
            
        self.frame_time += dt
        if self.frame_time >= self.animation_speed:
            self.frame_time = 0
            self.current_frame = (self.current_frame + 1) % len(self.effect_frames)
        
        return self.effect_frames[self.current_frame]
        
    def is_expired(self):
        if not self.is_active: return True
        return pygame.time.get_ticks() - self.start_time >= self.duration

    def get_remaining_time(self):
        if not self.is_active: return 0
        remaining = self.duration - (pygame.time.get_ticks() - self.start_time)
        return max(0, remaining)

