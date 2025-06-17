from .settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.screen = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player, target_pos):
        self.offset.x = -(target_pos[0] - WIDTH / 2)
        self.offset.y = -(target_pos[1] - HEIGHT / 2)
        
        ground_sprites = [sprite for sprite in self if hasattr(sprite, 'ground')]
        player_sprite = player
        
        if player and hasattr(player, 'gun'):
            other_sprites = [sprite for sprite in self if not hasattr(sprite, 'ground') 
                           and sprite != player 
                           and not isinstance(sprite, type(player.gun))]
            gun_sprite = player.gun
        else:
            other_sprites = [sprite for sprite in self if not hasattr(sprite, 'ground') 
                           and sprite != player]
            gun_sprite = None
        
        for layer in [ground_sprites, other_sprites]:
            for sprite in sorted(layer, key = lambda sprite: sprite.rect.centery):
                self.screen.blit(sprite.image, sprite.rect.topleft + self.offset)
        
        if player and hasattr(player, 'draw_buff_effects'):
            player.draw_buff_effects(self.screen, self.offset)
        
        if player_sprite:
            self.screen.blit(player_sprite.image, player_sprite.rect.topleft + self.offset)
        
        if gun_sprite:
            self.screen.blit(gun_sprite.image, gun_sprite.rect.topleft + self.offset)