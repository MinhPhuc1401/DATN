import pygame
import sys
from code.main import Game  
from code.levels import TOTAL_LEVELS  
from code.settings import WIDTH, HEIGHT
from code.ai_chatbot import GameAI

class Button:
    def __init__(self, x, y, width, height, text, font, text_color=(220, 220, 220), color=(60, 60, 60), hover_color=(80, 80, 80)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        
        # Pre-render text
        self.text_surface = self.font.render(text, True, text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2, border_radius=12)  # Border
        screen.blit(self.text_surface, self.text_rect)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                return True
        return False

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("The Monster Hunter - Simulation")
        self.clock = pygame.time.Clock()
        
        self.current_level = 1
        self.game_state = "menu"
        
        # Load background images
        self.menu_bg = pygame.image.load('images/background/menu.png').convert()
        self.menu_bg = pygame.transform.scale(self.menu_bg, (WIDTH, HEIGHT))
        self.win_bg = pygame.image.load('images/background/win.png').convert()
        self.win_bg = pygame.transform.scale(self.win_bg, (WIDTH, HEIGHT))
        
        # Setup music
        self.menu_music = pygame.mixer.Sound('audio/music.wav')
        self.victory_music = pygame.mixer.Sound('audio/victory.wav')
        self.menu_music.set_volume(0.3)
        self.victory_music.set_volume(0.5)
        self.music_channel = None
        
        self.title_font = pygame.font.Font(None, 100)
        self.info_font = pygame.font.Font(None, 50)
        self.help_font = pygame.font.Font(None, 36)
        self.game_instance = None
        self.help_ai = None
        
        # Create buttons
        button_width = 300
        button_height = 60
        center_x = WIDTH // 2 - button_width // 2
        
        # Menu buttons
        self.start_button = Button(center_x, HEIGHT // 2 - 20, button_width, button_height, "Start Game", self.info_font)
        self.help_button = Button(center_x, HEIGHT // 2 + 60, button_width, button_height, "Help", self.info_font)
        self.quit_button = Button(center_x, HEIGHT // 2 + 140, button_width, button_height, "Quit Game", self.info_font)
        
        # Help screen button
        self.back_button = Button(center_x, HEIGHT - 100, button_width, button_height, "Back to Menu", self.info_font)
        self.activate_ai_button = Button(center_x, HEIGHT - 180, button_width, button_height, "Ask AI Assistant", self.info_font)
        
        # Level cleared buttons
        self.next_level_button = Button(center_x, HEIGHT // 2 + 30, button_width, button_height, "Next Level", self.info_font)
        self.menu_button_cleared = Button(center_x, HEIGHT // 2 + 110, button_width, button_height, "Return to Menu", self.info_font)
        
        # Game over buttons
        self.retry_button = Button(center_x, HEIGHT // 2 + 40, button_width, button_height, "Retry Level", self.info_font)
        self.menu_button_over = Button(center_x, HEIGHT // 2 + 120, button_width, button_height, "Return to Menu", self.info_font)
        
        # All levels complete buttons
        self.final_menu_button = Button(center_x, HEIGHT // 2 + 70, button_width, button_height, "Return to Menu", self.info_font)
        self.final_quit_button = Button(center_x, HEIGHT // 2 + 150, button_width, button_height, "Quit Game", self.info_font)

    def display_help(self):
        if not self.music_channel or not self.music_channel.get_busy():
            self.music_channel = self.menu_music.play(-1)
            
        self.screen.blit(self.menu_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 192))
        self.screen.blit(overlay, (0, 0))
        
        # Draw title
        title_text = self.title_font.render("How to Play", True, (220, 220, 220))
        title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        instructions = [
            "Controls:",
            "- WASD: Move your character",
            "- SPACE: Dash (with cooldown)",
            "- Left Mouse Button: Shoot",
            "- R: Reload weapon",
            "- ENTER: Open chat with AI Assistant",
            "",
            "Tips:",
            "- Watch your ammo count and reload when safe",
            "- Use dash to dodge enemy attacks",
            "- Collect power-ups dropped by defeated enemies",
            "- Chat with the AI Assistant for strategy tips",
            "",
        ]
        
        y_pos = 200
        for line in instructions:
            text = self.help_font.render(line, True, (220, 220, 220))
            text_rect = text.get_rect(center=(WIDTH // 2, y_pos))
            self.screen.blit(text, text_rect)
            y_pos += 40
        
        self.back_button.draw(self.screen)
        self.activate_ai_button.draw(self.screen)
        
        if self.help_ai and self.help_ai.chat_box.active:
            self.help_ai.draw(self.screen)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.back_button.handle_event(event):
                if self.help_ai:
                    self.help_ai.chat_box.active = False
                self.game_state = "menu"
                
            if self.activate_ai_button.handle_event(event):
                if not self.help_ai:
                    self.help_ai = GameAI(None, None)
                self.help_ai.chat_box.active = True
            
            # Handle chat box events if active
            if self.help_ai and self.help_ai.chat_box.active:
                self.help_ai.handle_events(event)

    def display_menu(self):
        if not self.music_channel or not self.music_channel.get_busy():
            self.music_channel = self.menu_music.play(-1)
            
        self.screen.blit(self.menu_bg, (0, 0))       
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        title_text_surf = self.title_font.render("The Monster Hunter", True, (220, 220, 220))
        title_rect = title_text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        self.screen.blit(title_text_surf, title_rect)
        self.start_button.draw(self.screen)
        self.help_button.draw(self.screen)
        self.quit_button.draw(self.screen)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if self.start_button.handle_event(event):
                self.current_level = 1
                self.game_state = "playing"
            if self.help_button.handle_event(event):
                self.game_state = "help"
            if self.quit_button.handle_event(event):
                pygame.quit()
                sys.exit()

    def display_level_cleared_screen(self):
        if not self.music_channel or not self.music_channel.get_busy():
            self.music_channel = self.menu_music.play(-1)
            
        self.screen.fill((30, 60, 30))
        cleared_text_surf = self.title_font.render(f"Level {self.current_level} Cleared!", True, (180, 255, 180))
        cleared_rect = cleared_text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        self.screen.blit(cleared_text_surf, cleared_rect)
        self.next_level_button.draw(self.screen)
        self.menu_button_cleared.draw(self.screen)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if self.next_level_button.handle_event(event):
                self.current_level += 1
                if self.current_level > TOTAL_LEVELS:
                    self.game_state = "all_levels_complete"
                else:
                    self.game_state = "playing"
            if self.menu_button_cleared.handle_event(event):
                self.game_state = "menu"
    
    def display_game_over_screen(self):
        if not self.music_channel or not self.music_channel.get_busy():
            self.music_channel = self.menu_music.play(-1)
            
        self.screen.fill((60, 30, 30))
        over_text_surf = self.title_font.render("Game Over", True, (255, 120, 120))
        level_info_surf = self.info_font.render(f"You reached Level {self.current_level}", True, (220, 220, 220))     
        over_rect = over_text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3 - 30))
        level_info_rect = level_info_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
        
        self.screen.blit(over_text_surf, over_rect)
        self.screen.blit(level_info_surf, level_info_rect)
        self.retry_button.draw(self.screen)
        self.menu_button_over.draw(self.screen)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if self.retry_button.handle_event(event):
                self.game_state = "playing"
            if self.menu_button_over.handle_event(event):
                self.game_state = "menu"

    def display_all_levels_complete_screen(self):
        if not self.music_channel or not self.music_channel.get_busy():
            self.music_channel = self.victory_music.play(-1)

        self.screen.blit(self.win_bg, (0, 0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        congrats_text_surf = self.title_font.render("Congratulations!", True, (200, 200, 255))
        info_text_surf = self.info_font.render("You have completed all levels!", True, (220, 220, 220))       
        congrats_rect = congrats_text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 3))
        info_rect = info_text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        
        self.screen.blit(congrats_text_surf, congrats_rect)
        self.screen.blit(info_text_surf, info_rect)        
        self.final_menu_button.draw(self.screen)
        self.final_quit_button.draw(self.screen)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if self.final_menu_button.handle_event(event):
                if self.music_channel:
                    self.music_channel.stop()
                self.music_channel = self.menu_music.play(-1)
                self.game_state = "menu"
            if self.final_quit_button.handle_event(event):
                pygame.quit()
                sys.exit()

    def run_simulation(self):
        while True:
            if self.game_state == "menu":
                self.display_menu()
            elif self.game_state == "help":
                self.display_help()
            elif self.game_state == "playing":
                if self.music_channel:
                    self.music_channel.stop()
                    self.music_channel = None
                
                print(f"Starting/Retrying Level {self.current_level}")
                if not self.game_instance:
                    self.game_instance = Game(level=self.current_level)
                game_outcome = self.game_instance.run()
                
                if game_outcome == "win":
                    if self.current_level == TOTAL_LEVELS:
                        self.game_state = "all_levels_complete"
                    else:
                        self.game_state = "level_cleared"
                elif game_outcome == "lose":
                    self.game_state = "game_over"
                elif game_outcome == "menu":
                    self.game_state = "menu"
                else:
                    print(f"Unknown game outcome: {game_outcome}. Returning to menu.")
                    self.game_state = "menu"
                
                if game_outcome in ["win", "lose", "menu"]:
                    self.game_instance = None
            elif self.game_state == "level_cleared":
                self.display_level_cleared_screen()
            elif self.game_state == "game_over":
                self.display_game_over_screen()
            elif self.game_state == "all_levels_complete":
                self.display_all_levels_complete_screen()
            
            self.clock.tick(60)

if __name__ == '__main__':
    simulation = Simulation()
    simulation.run_simulation()
