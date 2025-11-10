import pygame, time, sys
pygame.init()
window = pygame.display.set_mode((400,300))
window.fill((10,100,200))  # Couleur test (bleu)
pygame.display.flip()
time.sleep(10)
pygame.quit()