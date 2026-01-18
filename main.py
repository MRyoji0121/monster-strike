import pygame
import math
import sys

# --- 1. 定数・色定義 ---
WHITE, BLACK, YELLOW, RED, GREEN, PURPLE = (
    255, 255, 255), (0, 0, 0), (255, 255, 0), (255, 0, 0), (0, 255, 0), (255, 0, 255)
BG_UI = (15, 15, 25)
SCREEN_WIDTH, SCREEN_HEIGHT = 400, 600
FRICTION, STOP_THRESHOLD, SS_TURN = 0.982, 0.5, 12
ORDER_LABELS = ["1st", "2nd", "3rd", "4th"]

LEVEL_DATA = [
    {"name": "STAGE 1", "hp": 200000000, "pos": (
        200, 150), "attack": 3, "bar_color": GREEN},
    {"name": "STAGE 2", "hp": 500000000, "pos": (
        200, 120), "attack": 3, "bar_color": YELLOW},
    {"name": "FINAL STAGE", "hp": 1200000000, "pos": (
        200, 180), "attack": 2, "bar_color": (255, 100, 0)}
]

# --- 2. クラス定義 ---

class Effect:
  def __init__(self, x, y, color):
    self.x, self.y, self.color = x, y, color
    self.timer, self.max_timer, self.active = 0, 20, True

  def update(self):
    self.timer += 1
    if self.timer >= self.max_timer: self.active = False

  def draw(self, screen):
    ratio = self.timer / self.max_timer
    radius = int(10 + 40 * ratio)
    alpha = int(255 * (1 - ratio))
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*self.color, alpha), (radius, radius), radius)
    screen.blit(s, (self.x - radius, self.y - radius))

class Player:
  def __init__(self, x, y, index, img, game_ref):
    self.start_pos = (
        x, y); self.img = img; self.radius = 20; self.index = index; self.game = game_ref; self.reset()

  def reset(self):
    self.x, self.y = self.start_pos; self.vx, self.vy = 0, 0; self.ss_phase = 0; self.ss_ready = False

  def update(self):
    if self.ss_phase == 1: return
    if self.vx != 0 or self.vy != 0:
      self.x += self.vx; self.y += self.vy; self.vx *= FRICTION; self.vy *= FRICTION
      if math.hypot(
          self.vx, self.vy) < STOP_THRESHOLD: self.vx, self.vy = 0, 0
      if self.x < self.radius or self.x > SCREEN_WIDTH - self.radius: self.vx *= -1
      if self.y < self.radius or self.y > 480 - self.radius: self.vy *= -1

  def draw(self, screen, current_turn_idx):
    draw_img = self.img.copy()
    if self.ss_phase == 2: draw_img.fill(
        (255, 0, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(draw_img, draw_img.get_rect(
        center=(int(self.x), int(self.y))))
    # 順番表示を縁取り付きで
    label_col = YELLOW if self.index == current_turn_idx else WHITE
    self.game.draw_text_with_outline(
        ORDER_LABELS[self.index], self.game.font_ui, label_col, int(self.x), int(self.y - 30))
    if self.ss_ready: pygame.draw.circle(
        screen, RED, (int(self.x), int(self.y)), self.radius + 4, 3)

class Enemy:
  def __init__(self, img):
    self.base_img = pygame.transform.smoothscale(
        img, (140, 140)); self.radius = 60; self.hp = 0

  def set_level(self, data):
    self.x, self.y, self.hp, self.max_hp, self.attack_timer, self.bar_col = data["pos"][
        0], data["pos"][1], data["hp"], data["hp"], data["attack"], data["bar_color"]

class EnemyBullet:
  def __init__(self, x, y, tx, ty):
    self.x, self.y = x, y
    angle = math.atan2(ty - y, tx - x)
    self.vx, self.vy = math.cos(angle) * 7.5, math.sin(angle) * 7.5
    self.active = True

  def update(self):
    self.x += self.vx; self.y += self.vy
    if not (0 <= self.x <= SCREEN_WIDTH and 0 <=
            self.y <= SCREEN_HEIGHT): self.active = False

  def draw(self, screen):
    pygame.draw.circle(screen, (100, 0, 150),
                       (int(self.x), int(self.y)), 12)
    pygame.draw.circle(screen, PURPLE, (int(self.x), int(self.y)), 8)

# --- 3. ゲーム管理クラス ---

class Game:
  def __init__(self):
    pygame.init()
    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    self.clock = pygame.time.Clock()
    self.load_assets()
    self.state, self.current_level_idx = "TITLE", 0
    self.enemy = Enemy(self.img_enemy)
    self.players = [Player(80, 420, 0, self.player_thumb, self), Player(160, 380, 1, self.player_thumb, self),
                    Player(240, 420, 2, self.player_thumb, self), Player(320, 440, 3, self.player_thumb, self)]
    self.init_game_vars()

  def load_assets(self):
    def load_or_dummy(name, size, color):
      try: return pygame.transform.smoothscale(pygame.image.load(name).convert_alpha(), size)
      except: s = pygame.Surface(size, pygame.SRCALPHA); s.fill(color); return s
    self.img_player = load_or_dummy('image_0.png', (40, 40), WHITE)
    self.player_thumb = self.img_player
    self.img_arrow = load_or_dummy('image_1.png', (35, 90), YELLOW)
    self.img_icon = load_or_dummy('image_2.png', (50, 50), WHITE)
    self.img_bg = pygame.transform.smoothscale(load_or_dummy(
        'image_3.png', (400, 600), (30, 30, 35)), (400, 600))
    self.img_enemy = load_or_dummy('image_4.png', (140, 140), GREEN)

    # フォント設定 (太いインパクトのあるフォントを指定)
    f_name = "impact"
    self.font_main = pygame.font.SysFont(f_name, 26)
    self.font_big = pygame.font.SysFont(f_name, 56)
    self.font_ui = pygame.font.SysFont("arialrounded", 18, True)

  def draw_text_with_outline(self, text, font, color, x, y, outline_color=BLACK):
    """本家風の縁取り文字を描画する関数"""
    text_surface = font.render(text, True, color)
    outline_surface = font.render(text, True, outline_color)
    rect = text_surface.get_rect(center=(x, y))
    # 上下左右に少しずらして黒文字を描画（縁取り）
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
      self.screen.blit(outline_surface, rect.move(dx, dy))
    self.screen.blit(text_surface, rect)

  def init_game_vars(self):
    self.enemy.set_level(LEVEL_DATA[self.current_level_idx])
    for p in self.players: p.reset()
    self.enemy_bullets, self.effects = [], []
    self.turn_index, self.ss_charge, self.is_moving, self.is_dragging, self.ss_actor, self.ss_timer, self.current_hp, self.max_hp = 0, [
        0, 0, 0, 0], False, False, None, 0, 100000, 100000

  def damage_enemy(self, amount, x=None, y=None):
    if self.enemy.hp <= 0: return
    self.enemy.hp -= amount
    if x and y: self.effects.append(Effect(x, y, YELLOW))
    if self.enemy.hp <= 0:
      self.enemy.hp, self.ss_actor, self.state = 0, None, "CLEAR_RESULT"
      self.enemy_bullets = []
      for i in range(5): self.effects.append(
          Effect(self.enemy.x, self.enemy.y, RED))

  def update(self):
    if self.state != "PLAYING": return
    all_stopped = True
    for p in self.players:
      p.update()
      if p.vx != 0 or p.vy != 0 or p.ss_phase == 1: all_stopped = False
      if self.enemy.hp > 0:
        dist = math.hypot(p.x - self.enemy.x, p.y - self.enemy.y)
        if dist < p.radius + self.enemy.radius:
          spd = math.hypot(p.vx, p.vy)
          if p.ss_ready and p.ss_phase == 0: p.ss_phase, p.vx, p.vy, self.ss_actor, self.ss_timer = 1, 0, 0, p, 80
          elif p.ss_phase in [0, 2] and spd > 1.2:
            self.damage_enemy(
                2000000 if p.ss_phase == 0 else 8000000, p.x, p.y)
            angle = math.atan2(
                p.y - self.enemy.y, p.x - self.enemy.x)
            p.vx, p.vy = math.cos(
                angle) * spd, math.sin(angle) * spd

    if self.ss_actor:
      if self.enemy.hp <= 0: self.ss_actor = None; return
      self.ss_timer -= 1
      if self.ss_timer % 4 == 0: self.damage_enemy(
          7000000, self.ss_actor.x + 20, self.ss_actor.y)
      if self.ss_timer <= 0:
        self.ss_actor.ss_phase, angle = 2, math.atan2(
            self.enemy.y - self.ss_actor.y, self.enemy.x - self.ss_actor.x)
        self.ss_actor.vx, self.ss_actor.vy, self.ss_actor = math.cos(
            angle) * 15, math.sin(angle) * 15, None

    for eb in self.enemy_bullets[:]:
      eb.update()
      for p in self.players:
        if math.hypot(eb.x - p.x, eb.y - p.y) < p.radius + 6:
          self.current_hp -= 6000; self.effects.append(Effect(eb.x, eb.y, PURPLE)); eb.active = False; break
      if not eb.active: self.enemy_bullets.remove(eb)

    for ef in self.effects[:]:
      ef.update()
      if not ef.active: self.effects.remove(ef)

    if self.is_moving and all_stopped:
      self.is_moving, self.turn_index = False, (self.turn_index + 1) % 4
      for p in self.players: p.ss_phase, p.ss_ready = 0, False
      self.enemy.attack_timer -= 1
      if self.enemy.attack_timer <= 0:
        for p in self.players: self.enemy_bullets.append(
            EnemyBullet(self.enemy.x, self.enemy.y, p.x, p.y))
        self.enemy.attack_timer = 3

  def draw_ui(self):
    pygame.draw.rect(self.screen, BG_UI, (0, 480, 400, 120))
    pygame.draw.line(self.screen, (100, 100, 120), (0, 480), (400, 480), 3)
    hp_rect = pygame.Rect(40, 490, 320, 15); pygame.draw.rect(
        self.screen, (40, 40, 50), hp_rect, 0, 5)
    pygame.draw.rect(self.screen, GREEN, (40, 490, max(
        0, 320 * (self.current_hp / self.max_hp)), 15), 0, 5)
    self.draw_text_with_outline(
        f"{int(self.current_hp)} / {int(self.max_hp)}", self.font_ui, WHITE, 200, 497)
    for i in range(4):
      x = 10 + i * 98; panel_rect = pygame.Rect(x, 510, 90, 80); color = (
          60, 60, 80) if i != self.turn_index else (120, 110, 40)
      pygame.draw.rect(self.screen, color, panel_rect, 0, 10)
      pygame.draw.rect(self.screen, WHITE if i == self.turn_index else (
          80, 80, 100), panel_rect, 2, 10)
      self.screen.blit(pygame.transform.smoothscale(
          self.img_icon, (45, 45)), self.img_icon.get_rect(center=(x + 45, 545)))
      txt = "OK" if self.ss_charge[i] >= SS_TURN else str(
          SS_TURN - self.ss_charge[i])
      self.draw_text_with_outline(
          f"SS: {txt}", self.font_ui, YELLOW if txt == "OK" else (180, 180, 180), x + 45, 575)

  def draw(self):
    self.screen.blit(self.img_bg, (0, 0))
    if self.state == "TITLE":
      ov = pygame.Surface((400, 600), pygame.SRCALPHA); ov.fill(
          (0, 0, 0, 210)); self.screen.blit(ov, (0, 0))
      self.draw_text_with_outline(
          "MONSTER CLONE", self.font_big, WHITE, 200, 230)
      self.draw_text_with_outline(
          "TAP TO START", self.font_main, YELLOW, 200, 310)
    elif self.state in ["PLAYING", "CLEAR_RESULT"]:
      if self.enemy.hp > 0:
        self.screen.blit(self.enemy.base_img, self.enemy.base_img.get_rect(
            center=(int(self.enemy.x), int(self.enemy.y))))
        pygame.draw.rect(self.screen, (50, 50, 50),
                         (40, 15, 320, 10), 0, 5)
        pygame.draw.rect(self.screen, self.enemy.bar_col, (40, 15,
                         320 * (self.enemy.hp / self.enemy.max_hp), 10), 0, 5)
        self.draw_text_with_outline(
            f"BOSS x {3 - self.current_level_idx}", self.font_ui, WHITE, 330, 10)
        self.draw_text_with_outline(str(self.enemy.attack_timer), self.font_big, RED, int(
            self.enemy.x + 65), int(self.enemy.y - 70))
      for p in self.players: p.draw(self.screen, self.turn_index)
      for eb in self.enemy_bullets: eb.draw(self.screen)
      for ef in self.effects: ef.draw(self.screen)
      self.draw_ui()
      if self.is_dragging:
        m = pygame.mouse.get_pos(
        ); dx, dy = m[0] - self.drag_start[0], m[1] - self.drag_start[1]
        angle = math.degrees(math.atan2(-dy, -dx)) + 90
        ar = pygame.transform.rotate(self.img_arrow, -angle)
        self.screen.blit(ar, ar.get_rect(
            center=(self.players[self.turn_index].x, self.players[self.turn_index].y)))
      if self.ss_actor and self.ss_timer > 30: self.draw_text_with_outline(
          "STRIKE SHOT!", self.font_big, PURPLE, 200, 260)
      if self.state == "CLEAR_RESULT":
        ov = pygame.Surface((400, 600), pygame.SRCALPHA); ov.fill(
            (0, 0, 0, 180)); self.screen.blit(ov, (0, 0))
        self.draw_text_with_outline(
            "STAGE CLEAR!", self.font_big, YELLOW, 200, 260)
    pygame.display.flip()

  def run(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
          if self.state == "TITLE": self.state = "PLAYING"
          elif self.state == "CLEAR_RESULT": self.current_level_idx = (self.current_level_idx + 1) % len(LEVEL_DATA); self.init_game_vars(); self.state = "PLAYING"
          elif self.state == "PLAYING" and not self.is_moving:
            pos = event.pos
            for i in range(4):
              if pygame.Rect(10 + i * 98, 510, 90, 80).collidepoint(pos) and i == self.turn_index:
                if self.ss_charge[i] >= SS_TURN:
                  self.players[i].ss_ready = not self.players[i].ss_ready
            p = self.players[self.turn_index]
            if math.hypot(
                pos[0] - p.x, pos[1] - p.y) < 45: self.is_dragging, self.drag_start = True, pos
        if event.type == pygame.MOUSEBUTTONUP and self.is_dragging:
          m = pygame.mouse.get_pos(
          ); dx, dy = self.drag_start[0] - m[0], self.drag_start[1] - m[1]
          if math.hypot(dx, dy) > 12:
            p = self.players[self.turn_index]; p.vx, p.vy, self.is_moving, self.is_dragging = dx * \
                0.26, dy * 0.26, True, False
            if p.ss_ready: self.ss_charge[self.turn_index] = 0
            else: self.ss_charge = [min(SS_TURN, c + 1) for c in self.ss_charge]
      self.update(); self.draw(); self.clock.tick(60)

if __name__ == "__main__": Game().run()
