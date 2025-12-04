"""Simple pinball-style arcade game built with pygame.

Controls
========
Left arrow / A: Activate left flipper
Right arrow / D: Activate right flipper
Space: Launch a new ball if none is active
Esc / Q: Quit
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple

import pygame


# Screen and gameplay constants
WIDTH, HEIGHT = 800, 1000
FPS = 60
GRAVITY = 900  # pixels per second squared
BALL_RADIUS = 12
FLIPPER_LENGTH = 110
FLIPPER_WIDTH = 18
FLIPPER_ANGLE = math.radians(25)
FLIPPER_REST_ANGLE = math.radians(-22)
FLIPPER_SPEED = math.radians(400)
BUMPER_RADIUS = 28
BUMPER_FORCE = 650
LAUNCH_FORCE = 720


Color = Tuple[int, int, int]
WHITE: Color = (235, 235, 235)
GREEN: Color = (80, 200, 120)
BLUE: Color = (115, 190, 255)
DARK: Color = (25, 25, 35)
YELLOW: Color = (255, 210, 90)
RED: Color = (230, 80, 80)
SHADOW: Color = (0, 0, 0)


@dataclass
class Flipper:
    pivot: pygame.math.Vector2
    is_left: bool
    color: Color
    angle: float = FLIPPER_REST_ANGLE
    activated: bool = False

    def update(self, dt: float) -> None:
        target_angle = FLIPPER_ANGLE if self.activated else FLIPPER_REST_ANGLE
        direction = 1 if target_angle > self.angle else -1
        if math.isclose(self.angle, target_angle, abs_tol=1e-3):
            self.angle = target_angle
            return
        self.angle += direction * FLIPPER_SPEED * dt
        if (direction > 0 and self.angle > target_angle) or (direction < 0 and self.angle < target_angle):
            self.angle = target_angle

    def toggle(self, active: bool) -> None:
        self.activated = active

    def get_tip(self) -> pygame.math.Vector2:
        direction = pygame.math.Vector2(math.cos(self.angle), math.sin(self.angle))
        if not self.is_left:
            direction.y *= -1
        return self.pivot + direction * FLIPPER_LENGTH

    def collide(self, ball: "Ball") -> bool:
        tip = self.get_tip()
        nearest = ball.position - self.pivot
        direction = (tip - self.pivot).normalize()
        projection_length = max(0, min(FLIPPER_LENGTH, nearest.dot(direction)))
        closest_point = self.pivot + direction * projection_length
        if (ball.position - closest_point).length() <= BALL_RADIUS + FLIPPER_WIDTH / 2:
            normal = (ball.position - closest_point).normalize()
            ball.velocity = ball.velocity.reflect(normal) + normal * 120
            ball.position += normal * 4
            ball.velocity.y -= 60 if self.is_left else 0
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        tip = self.get_tip()
        pygame.draw.line(surface, SHADOW, self.pivot + pygame.math.Vector2(3, 3), tip + pygame.math.Vector2(3, 3), FLIPPER_WIDTH)
        pygame.draw.line(surface, self.color, self.pivot, tip, FLIPPER_WIDTH)
        pygame.draw.circle(surface, self.color, self.pivot, FLIPPER_WIDTH // 2)


@dataclass
class Bumper:
    position: pygame.math.Vector2
    color: Color = BLUE
    value: int = 100

    def collide(self, ball: "Ball") -> bool:
        displacement = ball.position - self.position
        distance = displacement.length()
        if distance <= BUMPER_RADIUS + BALL_RADIUS:
            normal = displacement.normalize()
            impulse = normal * BUMPER_FORCE
            ball.velocity = ball.velocity.reflect(normal) + impulse * 0.4
            ball.position = self.position + normal * (BUMPER_RADIUS + BALL_RADIUS + 2)
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, SHADOW, self.position + pygame.math.Vector2(4, 6), BUMPER_RADIUS + 3)
        pygame.draw.circle(surface, self.color, self.position, BUMPER_RADIUS)
        pygame.draw.circle(surface, WHITE, self.position, 8)


@dataclass
class Ball:
    position: pygame.math.Vector2
    velocity: pygame.math.Vector2

    def update(self, dt: float) -> None:
        self.velocity.y += GRAVITY * dt
        self.position += self.velocity * dt
        self._handle_walls()

    def _handle_walls(self) -> None:
        if self.position.x - BALL_RADIUS < 20:
            self.position.x = 20 + BALL_RADIUS
            self.velocity.x = abs(self.velocity.x) * 0.92
        if self.position.x + BALL_RADIUS > WIDTH - 20:
            self.position.x = WIDTH - 20 - BALL_RADIUS
            self.velocity.x = -abs(self.velocity.x) * 0.92
        if self.position.y - BALL_RADIUS < 20:
            self.position.y = 20 + BALL_RADIUS
            self.velocity.y = abs(self.velocity.y) * 0.92

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, SHADOW, self.position + pygame.math.Vector2(3, 5), BALL_RADIUS)
        pygame.draw.circle(surface, YELLOW, self.position, BALL_RADIUS)


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pinball Arcade")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)

        self.left_flipper = Flipper(pivot=pygame.math.Vector2(270, 820), is_left=True, color=GREEN)
        self.right_flipper = Flipper(pivot=pygame.math.Vector2(530, 820), is_left=False, color=GREEN)
        self.bumpers = self._create_bumpers()
        self.ball: Ball | None = None
        self.score = 0

    def _create_bumpers(self) -> list[Bumper]:
        bumpers = []
        for y in (260, 360, 460):
            for x in (220, 320, 480, 580):
                bumpers.append(Bumper(position=pygame.math.Vector2(x, y), color=random.choice([BLUE, RED]), value=150))
        bumpers.append(Bumper(position=pygame.math.Vector2(WIDTH // 2, 560), color=BLUE, value=250))
        return bumpers

    def launch_ball(self) -> None:
        spawn = pygame.math.Vector2(WIDTH - 70, HEIGHT - 80)
        velocity = pygame.math.Vector2(random.uniform(-120, 120), -LAUNCH_FORCE)
        self.ball = Ball(position=spawn, velocity=velocity)

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.left_flipper.toggle(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.right_flipper.toggle(keys[pygame.K_RIGHT] or keys[pygame.K_d])

        self.left_flipper.update(dt)
        self.right_flipper.update(dt)

        if self.ball:
            self.ball.update(dt)
            self._handle_collisions()
            if self.ball.position.y - BALL_RADIUS > HEIGHT + 40:
                self.ball = None

    def _handle_collisions(self) -> None:
        if not self.ball:
            return
        for flipper in (self.left_flipper, self.right_flipper):
            flipper.collide(self.ball)
        for bumper in self.bumpers:
            if bumper.collide(self.ball):
                self.score += bumper.value

    def draw(self) -> None:
        self.screen.fill(DARK)
        self._draw_walls()
        for bumper in self.bumpers:
            bumper.draw(self.screen)
        self.left_flipper.draw(self.screen)
        self.right_flipper.draw(self.screen)
        if self.ball:
            self.ball.draw(self.screen)
        self._draw_hud()
        pygame.display.flip()

    def _draw_walls(self) -> None:
        pygame.draw.rect(self.screen, (50, 60, 70), pygame.Rect(10, 10, WIDTH - 20, HEIGHT - 20), 16)
        pygame.draw.rect(self.screen, (90, 100, 120), pygame.Rect(WIDTH - 120, HEIGHT - 170, 90, 160))
        pygame.draw.circle(self.screen, (70, 80, 95), (WIDTH - 75, HEIGHT - 190), 50, 8)

    def _draw_hud(self) -> None:
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        info_text = self.font.render("Space to launch, Arrow/A-D to flip", True, WHITE)
        self.screen.blit(score_text, (24, 24))
        self.screen.blit(info_text, (24, 54))
        if not self.ball:
            prompt = self.font.render("Press SPACE to launch a ball", True, WHITE)
            self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT - 70))

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    if event.key == pygame.K_SPACE and not self.ball:
                        self.launch_ball()

            self.update(dt)
            self.draw()

        pygame.quit()


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
