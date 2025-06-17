from .settings import *
import pygame
import requests
from .player import Player
from .sprites import *
from .buffs import *
from .levels import *
from .groups import *
from .config import MISTRAL_API_KEY, MISTRAL_API_URL
import math

class ChatBox:
    def __init__(self):
        box_width = 800
        box_height = 180
        self.rect = pygame.Rect(
            (WIDTH - box_width) // 2,
            HEIGHT - box_height - 50,
            box_width,
            box_height
        )
        
        response_height = 300
        self.response_rect = pygame.Rect(
            (WIDTH - box_width) // 2,
            self.rect.top - response_height - 30,
            box_width,
            response_height
        )
        
        # Visual settings
        self.active = False
        self.text = ''
        self.cursor_pos = 0
        self.font = pygame.font.Font(None, 40)
        self.response_font = pygame.font.Font(None, 36)
        self.color_active = pygame.Color('black')
        self.color_inactive = pygame.Color('gray15')
        self.color = self.color_inactive
        self.text_color = pygame.Color('white')
        self.max_chars = 300
        self.line_spacing = 40
        self.margin = 25

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and not pygame.key.get_mods() & pygame.KMOD_SHIFT:
                if not self.active: 
                    self.active = True
                    self.color = self.color_active
                    self.text = ''
                    self.cursor_pos = 0
                    return True
                else:
                    if self.text:
                        user_input = self.text  
                        self.text = ''
                        self.cursor_pos = 0
                        return user_input
                    else:
                        self.active = False
                        self.color = self.color_inactive
                        return False
            
            if self.active:
                if event.key == pygame.K_ESCAPE:
                    self.active = False
                    self.color = self.color_inactive
                    self.text = ''
                    self.cursor_pos = 0
                    return False
                elif event.key == pygame.K_BACKSPACE:
                    if self.cursor_pos > 0:
                        self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                        self.cursor_pos -= 1
                elif event.key == pygame.K_DELETE:
                    if self.cursor_pos < len(self.text):
                        self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
                elif event.key == pygame.K_LEFT:
                    self.cursor_pos = max(0, self.cursor_pos - 1)
                elif event.key == pygame.K_RIGHT:
                    self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
                elif event.key == pygame.K_RETURN and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if len(self.text) + 1 < self.max_chars:
                        self.text = self.text[:self.cursor_pos] + '\\n' + self.text[self.cursor_pos:]
                        self.cursor_pos += 2
                elif len(self.text) < self.max_chars:
                    new_text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    
                    lines = new_text.split('\\n')
                    current_line = lines[-1] if lines else ""
                    
                    if self.font.size(current_line + event.unicode)[0] > self.rect.width - 2 * self.margin:
                        new_text = self.text[:self.cursor_pos] + '\\n' + event.unicode + self.text[self.cursor_pos:]
                        self.cursor_pos += 2
                    
                    self.text = new_text
                    self.cursor_pos += len(event.unicode)
            return True
        return False

    def draw(self, screen, last_response):
        if not self.active:
            return

        pygame.draw.rect(screen, self.color, self.rect, border_radius=10)
        pygame.draw.rect(screen, pygame.Color('gray30'), self.rect, 2, border_radius=10)

        lines = self.text.split('\\n')
        y_offset = self.rect.top + self.margin
        x_pos = self.rect.left + self.margin
        cursor_drawn = False

        total_height = len(lines) * self.line_spacing
        if total_height > self.rect.height - 2 * self.margin:
            scroll_offset = total_height - (self.rect.height - 2 * self.margin)
            y_offset -= scroll_offset

        chars_before_cursor = 0
        for i, line in enumerate(lines):
            wrapped_line = self._wrap_line(line, self.rect.width - 2 * self.margin)
            
            for wrapped_segment in wrapped_line:
                if not cursor_drawn and chars_before_cursor + len(wrapped_segment) >= self.cursor_pos:
                    cursor_x = x_pos + self.font.size(wrapped_segment[:self.cursor_pos - chars_before_cursor])[0]
                    cursor_y = y_offset
                    cursor_drawn = True
                
                if y_offset + self.line_spacing <= self.rect.bottom - self.margin:
                    text_surface = self.font.render(wrapped_segment, True, self.text_color)
                    screen.blit(text_surface, (x_pos, y_offset))
                
                y_offset += self.line_spacing
                chars_before_cursor += len(wrapped_segment)
            
            chars_before_cursor += 2

        if cursor_drawn:
            pygame.draw.line(screen, self.text_color, 
                           (cursor_x, cursor_y), 
                           (cursor_x, cursor_y + self.font.get_height()), 2)

        response_surface = pygame.Surface(self.response_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(response_surface, (0, 0, 0, 180), response_surface.get_rect(), border_radius=10)
        screen.blit(response_surface, self.response_rect)
        pygame.draw.rect(screen, pygame.Color('gray30'), self.response_rect, 2, border_radius=10)

        wrapped_text = self._wrap_text(last_response, self.response_rect.width - 2 * self.margin)
        y_offset = self.response_rect.top + self.margin
        
        total_height = len(wrapped_text) * self.line_spacing
        if total_height > self.response_rect.height - 2 * self.margin:
            scroll_offset = total_height - (self.response_rect.height - 2 * self.margin)
            y_offset -= scroll_offset
        
        for line in wrapped_text:
            text_surf = self.response_font.render(line, True, self.text_color)
            if (y_offset + self.line_spacing > self.response_rect.top and 
                y_offset < self.response_rect.bottom - self.margin):
                screen.blit(text_surf, (self.response_rect.left + self.margin, y_offset))
            y_offset += self.line_spacing

    def _wrap_line(self, text, max_width):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width = self.font.size(test_line)[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    current_word = word
                    while current_word:
                        for i in range(len(current_word), 0, -1):
                            if self.font.size(current_word[:i])[0] <= max_width:
                                lines.append(current_word[:i])
                                current_word = current_word[i:]
                                break
                        if not i:
                            lines.append(current_word)
                            break
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [""]

    def _wrap_text(self, text, max_width):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width, _ = self.response_font.size(test_line)
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        return lines

class GameAI:
    def __init__(self, player, enemy_sprites):
        self.player = player
        self.enemy_sprites = enemy_sprites
        self.chat_box = ChatBox()
        self.last_response = "Hi! I'm your game assistant. How can I help you?"

        self.api_url = MISTRAL_API_URL
        self.headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }

        self.game_mechanics_knowledge = {
            'player_mechanics': {
                'stats': {
                    'health': 100,
                    'speed': 400,
                    'animation_speed': 8
                },
                'abilities': {
                    'dash': {
                        'description': 'Quick dash in movement direction',
                        'cooldown': 2000,  # 2 seconds
                        'duration': 200,  # 0.2 seconds
                        'speed_multiplier': 6,
                        'afterimage': {
                            'alpha': 150,
                            'lifetime': 200  # 0.2 seconds
                        }
                    }
                },
                'combat': {
                    'gun': {
                        'damage': 10,
                        'speed': 1500,
                        'lifetime': 1000,  # 1 second - bullets disappear after this time if they don't hit anything
                        'cooldown': 200,  # 0.2 seconds
                        'magazine_size': 6,
                        'reload_time': 1500  # 1.5 seconds
                    }
                }
            },

            'buff_mechanics': {
            'speed_boost': {
                    'description': 'Increases movement speed',
                    'duration': 10000,  # 10 seconds
                'effect': 'Increases movement speed by 50%',
                    'drop_chance': 0.30  # 30% chance from enemy drops
                },
            'damage_boost': {
                    'description': 'Increases bullet damage',
                    'duration': 10000,  # 10 seconds
                'effect': 'Doubles bullet damage',
                    'drop_chance': 0.30
                },
            'health_regen': {
                    'description': 'Restores health',
                    'duration': 0,  # Instant effect
                'effect': 'Instantly heals 25 HP',
                    'drop_chance': 0.30
                }
            },

            'enemy_mechanics': {
                'melee_enemy': {
                    'name': 'Skeleton',
                    'stats': {
                        'health': 30,
                        'speed': 250,
                        'vision_range': 1000,
                        'damage': 80,
                        'damage_cooldown': 1000  # 1 second
                    },
                    'behavior': {
                        'movement': 'Moves directly towards the player when in vision range',
                        'attack': 'Deals damage on contact with player, has 1 second cooldown',
                        'trigger': 'Activates when player enters 1000 unit vision range'
                    }
                },
                
                'ranged_enemy': {
                    'name': 'Blob',
                    'stats': {
                        'health': 20,
                        'speed': 300,
                        'vision_range': 1000,
                        'damage': 40,
                        'shoot_cooldown': 2000,  # 2 seconds
                        'laser_width': 100
                    },
                    'behavior': {
                        'movement': 'Moves normally when not attacking',
                        'attack_phases': {
                            'aiming': 'Aims at player for 500ms',
                            'delaying': 'Prepares to shoot for 500ms',
                            'firing': 'Fires laser for 200ms',
                            'cooldown': '2 second cooldown between shots'
                        },
                        'trigger': 'Activates when player enters 1000 unit vision range'
                    }
                },
                
                'charger_enemy': {
                    'name': 'Bat',
                    'stats': {
                        'health': 20,
                        'normal_speed': 280,
                        'charge_speed': 2800,
                        'vision_range': 1000,
                        'damage': 40,
                        'charge_cooldown': 1500  # 1.5 seconds
                    },
                    'behavior': {
                        'movement': 'Moves normally when not attacking',
                        'attack_phases': {
                            'locking': 'Locks onto player position for 1000ms',
                            'delaying': 'Prepares to charge for 500ms',
                            'charging': 'Charges at high speed for 800ms',
                            'cooldown': '1.5 second cooldown between charges'
                        },
                        'attack_indicator': 'Shows warning circle: yellow -> orange -> red',
                        'trigger': 'Activates when player enters 1000 unit vision range'
                    }
                },
                
                'boss': {
                    'name': 'Boss',
                    'stats': {
                        'health': 600,
                        'speed': 150,
                        'vision_range': 1000,
                        'time_between_skills': 2000  # 2 seconds
                    },
                    'skills': {
                        'summon': {
                            'description': 'Summons 3 random enemies (skeleton, blob, bat) around itself',
                            'cooldown': 2000  # 2 seconds
                        },
                        'area_attack': {
                            'description': 'Creates 12 damage zones around the player',
                            'damage': 30,
                            'damage_interval': 1000,  # 1 second
                            'phases': {
                                'warning': 'Warning phase for damage zones',
                                'active': 'Deals damage for 6 seconds',
                                'cooldown': 'Skill cooldown'
                            }
                        },
                        'fireball': {
                            'description': 'Shoots fireball towards the player',
                            'phases': {
                                'warning': 'Warning before shooting',
                                'active': 'Shoots fireball',
                                'cooldown': 'Skill cooldown'
                            }
                        }
                    },
                    'behavior': {
                        'movement': 'Moves to maintain ideal distance from player',
                        'skill_rotation': 'Uses skills in order: summon -> area_attack -> fireball',
                        'trigger': 'Activates when player enters 1000 unit vision range'
                    }
                },
                
                'common_traits': {
                    'health_bar': 'Shows health bar when taking damage',
                    'death_animation': 'Has death animation',
                    'buff_drop': '30% chance to drop buff on death (except boss)',
                    'vision': 'Only attacks when player is in vision range'
                }
            },

            'general_tips': {
                'combat': [
                    'Keep moving to avoid enemy attacks',
                    'Use dash ability to escape dangerous situations',
                    'Reload your gun when safe, not during combat',
                    'Prioritize ranged enemies as they can attack from a distance',
                    'Watch out for charger enemies - they move very fast when charging'
                ],
                'boss_fight': [
                    'Boss has 3 skills: summon, area attack, and fireball',
                    'Area attack creates 12 damage zones around you',
                    'Fireball can be dodged by moving perpendicular to its path',
                    'When boss summons enemies, focus on clearing them first',
                    'Boss takes 2 seconds between each skill use'
                ],
                'survival': [
                    'Always keep track of your ammo count',
                    'Use cover and obstacles to avoid enemy attacks',
                    'Don\'t get surrounded by multiple enemies',
                    'Save dash for emergency situations',
                    'Collect buffs whenever possible to maintain advantages'
                ]
            }
        }

    def generate_response(self, user_input):
        try:
            # Add game context to the input
            game_context = self.get_game_context()
            
            # Format messages for Mistral API
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful game assistant. Keep your responses very short and concise, maximum 1-2 sentences."
                },
                {
                    "role": "user",
                    "content": f"Game Context: {game_context}\n\nUser Question: {user_input}"
                }
            ]
            
            payload = {
                "model": "mistral-small",
                "messages": messages,
                    "temperature": 0.7,
                "max_tokens": 100,
                "top_p": 0.95,
                "stream": False
            }
            
            print("\n=== API Request Details ===")
            print(f"URL: {self.api_url}")
            print(f"Headers: {self.headers}")
            print(f"Payload: {payload}")
            
            # Make API request
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            print("\n=== API Response Details ===")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Content: {response.text}")
            
            if response.status_code == 401:
                return "Sorry, I'm having trouble authenticating. Please check the API key."
            elif response.status_code == 400:
                return "Sorry, I'm having trouble processing your request. Please try again."
            elif response.status_code != 200:
                return f"Sorry, I'm having trouble connecting (Error {response.status_code}). Please try again later."
            
            # Parse response
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                generated_text = result['choices'][0]['message']['content']
            else:
                generated_text = str(result)
            
            # Clean up response
            generated_text = generated_text.strip()
            
            return generated_text if generated_text else "I'm not sure how to respond to that."
            
        except requests.exceptions.RequestException as e:
            print(f"\n=== API Request Error ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            return "Sorry, I'm having trouble connecting right now. Try again later!"
        except Exception as e:
            print(f"\n=== General Error ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            return "Sorry, I'm having trouble thinking right now. Try again later!"

    def get_nearest_enemy_direction(self):
        if not self.enemy_sprites or not self.player:
            return "No enemies nearby"
            
        player_pos = self.player.rect.center
        nearest_dist = float('inf')
        nearest_enemy = None
        
        for enemy in self.enemy_sprites:
            enemy_pos = enemy.rect.center
            dx = enemy_pos[0] - player_pos[0]
            dy = enemy_pos[1] - player_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5
            
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_enemy = (dx, dy)
        
        if nearest_enemy is None:
            return "No valid enemy positions found"
            
        dx, dy = nearest_enemy
        # Determine direction based on angle
        angle = math.degrees(math.atan2(dy, dx))
        
        # Convert angle to direction
        if -22.5 <= angle < 22.5:
            direction = "right"
        elif 22.5 <= angle < 67.5:
            direction = "bottom-right"
        elif 67.5 <= angle < 112.5:
            direction = "bottom"
        elif 112.5 <= angle < 157.5:
            direction = "bottom-left"
        elif 157.5 <= angle < 180 or -180 <= angle < -157.5:
            direction = "left"
        elif -157.5 <= angle < -112.5:
            direction = "top-left"
        elif -112.5 <= angle < -67.5:
            direction = "top"
        else:  # -67.5 <= angle < -22.5
            direction = "top-right"
            
        return f"Nearest enemy is to the {direction}"

    def get_game_context(self):
        if not self.player:
            return "No game state available"
        
        context = []
        # === CURRENT GAME STATE ===
        context.append("=== CURRENT GAME STATE ===")
        
        # Enemies
        if self.enemy_sprites:
            enemy_counts = {}
            for enemy in self.enemy_sprites:
                enemy_type = enemy.__class__.__name__.lower()
                enemy_counts[enemy_type] = enemy_counts.get(enemy_type, 0) + 1
            enemy_info = [f"{count} {etype}" for etype, count in enemy_counts.items()]
            context.append(f"Enemies Remaining: {', '.join(enemy_info)}")
            # Add nearest enemy direction
            context.append(self.get_nearest_enemy_direction())
        else:
            context.append("No enemies remaining")
            
        # Buffs on map
        if hasattr(self.player, 'game') and hasattr(self.player.game, 'buff_item_sprites'):
            buffs_on_map = list(self.player.game.buff_item_sprites)
            if buffs_on_map:
                buff_types = [buff.buff_type_key for buff in buffs_on_map]
                context.append(f"Buffs Available: {', '.join(buff_types)}")
            else:
                context.append("No buffs available on map")
        else:
            context.append("No buffs available on map")
            
        # === GAME MECHANICS ===
        context.append("\n=== GAME MECHANICS ===")
        context.append(str(self.game_mechanics_knowledge))
        return "\n".join(context)

    def handle_events(self, event):
        result = self.chat_box.handle_event(event)
        if isinstance(result, str):
            self.last_response = self.generate_response(result)
        return result

    def draw(self, screen):
        if self.chat_box.active:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            self.chat_box.draw(screen, self.last_response)
