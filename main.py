import pygame
import math
import random
import sys

# --- 1. 定数・設定 ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FIXED_SPEED = 12
SS_TURN = 12
FRICTION = 0.98
STOP_THRESHOLD = 0.5

LEVEL_DATA = [
    {"name": "STAGE 1", "hp": 200000000, "pos": (200, 150), "attack": 3},
    {"name": "STAGE 2", "hp": 500000000, "pos": (200, 120), "attack": 3},
    {"name": "FINAL STAGE", "hp": 1200000000, "pos": (200, 180), "attack": 2}
]

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (255, 0, 255)

# --- 1. 定数・設定 ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FIXED_SPEED = 12  # 定速移動の速度
SS_TURN = 12

# ステージデータ
LEVEL_DATA = [
    {"name": "STAGE 1", "hp": 200000000, "pos": (200, 150), "attack": 3},
    {"name": "STAGE 2", "hp": 500000000, "pos": (200, 120), "attack": 3},
    {"name": "FINAL STAGE", "hp": 1200000000, "pos": (200, 180), "attack": 2}
]

# カラー
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (255, 0, 255)

# --- 2. クラス定義 ---
class Player:
  def __init__(self, x, y, index, img):
    self.start_pos = (x, y)
    self.img = img
    self.radius = 20
    self.index = index
    self.reset()

    def update(self):
      if self.ss_phase == 1: return  # 乱打中は停止

      if self.vx != 0 or self.vy != 0:
        # 1. 座標を更新
        self.x += self.vx
        self.y += self.vy

        # 2. 速度に摩擦を掛けて徐々に減速させる
        self.vx *= FRICTION
        self.vy *= FRICTION

        # 3. 速度が極低速になったら完全にゼロにする（停止判定）
        if math.hypot(self.vx, self.vy) < STOP_THRESHOLD:
          self.vx = 0
          self.vy = 0
          self.reflect_count = 0  # 反射カウントもリセット

        # 4. 壁反射（ここでは速度を落とさず向きだけ変える）
        if self.x < self.radius:
          self.x = self.radius
          self.vx *= -1
        elif self.x > SCREEN_WIDTH - self.radius:
          self.x = SCREEN_WIDTH - self.radius
          self.vx *= -1

        if self.y < self.radius:
          self.y = self.radius
          self.vy *= -1
        elif self.y > 490 - self.radius:  # UI手前
          self.y = 490 - self.radius
          self.vy *= -1

  def reset(self):
    self.x, self.y = self.start_pos
    self.vx, self.vy = 0, 0
    self.has_fired_combo = False
    self.ss_phase = 0  # 0:通常, 1:乱打, 2:追い打ち
    self.ss_ready = False
    self.reflect_count = 0

  def update(self):
    if self.ss_phase == 1: return  # 乱打中は停止

    if self.vx != 0 or self.vy != 0:
      # 定速ロジック：速度の向きを維持しつつ、大きさを固定
      speed = math.hypot(self.vx, self.vy)
      target_speed = FIXED_SPEED * 1.8 if self.ss_phase == 2 else FIXED_SPEED
      self.vx = (self.vx / speed) * target_speed
      self.vy = (self.vy / speed) * target_speed

      self.x += self.vx
      self.y += self.vy

      # 壁反射
      if self.x < self.radius or self.x > SCREEN_WIDTH - self.radius:
        self.vx *= -1
        self.reflect_count += 1
      if self.y < self.radius or self.y > 490 - self.radius:
        self.vy *= -1
        self.reflect_count += 1

      # JS版に合わせ一定回数で停止
      if self.reflect_count > 15:
        self.vx, self.vy = 0, 0
        self.reflect_count = 0

  def draw(self, screen):
    draw_img = self.img.copy()
    if self.ss_phase == 2:
      draw_img.fill((255, 0, 255, 150),
                    special_flags=pygame.BLEND_RGBA_MULT)
    rect = draw_img.get_rect(center=(int(self.x), int(self.y)))
    screen.blit(draw_img, rect)
    if self.ss_ready:
      pygame.draw.circle(
          screen, RED, (int(self.x), int(self.y)), self.radius + 4, 2)

class Enemy:
  def __init__(self, img):
    self.base_img = pygame.transform.smoothscale(img, (140, 140))
    self.radius = 60
    self.hp = 0

  def set_level(self, data):
    self.x, self.y = data["pos"]
    self.hp = data["hp"]
    self.max_hp = data["hp"]
    self.attack_timer = data["attack"]

# --- 3. ゲーム管理クラス ---

class Game:
  def __init__(self):
    pygame.init()
    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Monster Clone Overdrive")
    self.clock = pygame.time.Clock()
    self.load_assets()

    self.state = "TITLE"  # TITLE, PLAYING, CLEAR_RESULT
    self.current_level_idx = 0
    self.enemy = Enemy(self.img_enemy)
    self.players = [
        Player(80, 430, 0, self.player_thumb),
        Player(160, 380, 1, self.player_thumb),
        Player(240, 430, 2, self.player_thumb),
        Player(320, 450, 3, self.player_thumb)
    ]
    self.init_game_vars()

  def load_assets(self):
    def load_or_dummy(name, size, color):
      try: return pygame.transform.smoothscale(pygame.image.load(name).convert_alpha(), size)
      except:
        s = pygame.Surface(size, pygame.SRCALPHA); s.fill(color); return s

    self.img_player = load_or_dummy('image_0.png', (40, 40), WHITE)
    self.player_thumb = self.img_player
    self.img_arrow = load_or_dummy('image_1.png', (40, 100), YELLOW)
    self.img_icon = load_or_dummy('image_2.png', (50, 50), WHITE)
    self.img_bg = load_or_dummy('image_3.png', (40, 60), (30, 30, 30))
    self.img_bg = pygame.transform.smoothscale(self.img_bg, (400, 600))
    self.img_enemy = load_or_dummy('image_4.png', (140, 140), GREEN)

    self.font_main = pygame.font.SysFont("arial", 24, bold=True)
    self.font_big = pygame.font.SysFont("arial", 50, bold=True)
    self.font_ui = pygame.font.SysFont("arial", 18, bold=True)

  def init_game_vars(self):
    data = LEVEL_DATA[self.current_level_idx]
    self.enemy.set_level(data)
    for p in self.players: p.reset()
    self.turn_index = 0
    self.ss_charge = [SS_TURN] * 4
    self.is_moving = False
    self.is_dragging = False
    self.ss_actor = None
    self.ss_timer = 0
    self.current_hp = 100000
    self.max_hp = 100000

  def start_ss(self, player):
    player.ss_phase = 1
    player.vx = 0
    player.vy = 0
    self.ss_actor = player
    self.ss_timer = 80

  def damage_enemy(self, amount):
    if self.enemy.hp <= 0: return
    self.enemy.hp -= amount
    if self.enemy.hp <= 0:
      self.enemy.hp = 0
      self.ss_actor = None  # SS演出を即時破棄
      self.state = "CLEAR_RESULT"

  def update(self):
    if self.state != "PLAYING": return

    all_stopped = True
    for p in self.players:
      p.update()
      if p.vx != 0 or p.vy != 0 or p.ss_phase == 1:
        all_stopped = False

      # 衝突判定
      dist = math.hypot(p.x - self.enemy.x, p.y - self.enemy.y)
      if dist < p.radius + self.enemy.radius:
        if p.ss_ready and p.ss_phase == 0:
          self.start_ss(p)
        elif p.ss_phase == 0:
          angle = math.atan2(p.y - self.enemy.y, p.x - self.enemy.x)
          p.vx, p.vy = math.cos(
              angle) * FIXED_SPEED, math.sin(angle) * FIXED_SPEED
          self.damage_enemy(2000000)
        elif p.ss_phase == 2:
          self.damage_enemy(8000000)

    # SS乱打進行
    if self.ss_actor:
      self.ss_timer -= 1
      if self.ss_timer % 4 == 0:
        self.damage_enemy(7000000)
      if self.ss_timer <= 0:
        self.ss_actor.ss_phase = 2
        angle = math.atan2(self.enemy.y - self.ss_actor.y,
                           self.enemy.x - self.ss_actor.x)
        self.ss_actor.vx, self.ss_actor.vy = math.cos(
            angle) * 10, math.sin(angle) * 10
        self.ss_actor = None

    if self.is_moving and all_stopped:
      self.is_moving = False
      self.turn_index = (self.turn_index + 1) % 4
      for p in self.players:
        p.ss_phase, p.ss_ready = 0, False
      # 敵の攻撃
      self.enemy.attack_timer -= 1
      if self.enemy.attack_timer <= 0:
        self.current_hp -= 20000
        self.enemy.attack_timer = 3

  def draw_ui(self):
    # UI背景
    pygame.draw.rect(self.screen, (20, 20, 20), (0, 500, 400, 100))
    # 自チームHP
    pygame.draw.rect(self.screen, BLACK, (50, 505, 300, 12))
    hp_w = 300 * (self.current_hp / self.max_hp)
    pygame.draw.rect(self.screen, GREEN, (50, 505, max(0, hp_w), 12))

    for i in range(4):
      rect = pygame.Rect(55 + i * 80, 530, 50, 50)
      self.screen.blit(pygame.transform.smoothscale(
          self.img_icon, (50, 50)), rect)
      if i == self.turn_index:
        pygame.draw.rect(self.screen, YELLOW, rect, 3)

      ss_label = "OK" if self.ss_charge[i] >= SS_TURN else str(
          SS_TURN - self.ss_charge[i])
      col = YELLOW if ss_label == "OK" else WHITE
      txt = self.font_ui.render(ss_label, True, col)
      self.screen.blit(txt, (rect.x + 5, rect.y + 5))

  def draw(self):
    self.screen.blit(self.img_bg, (0, 0))

    if self.state == "TITLE":
      overlay = pygame.Surface((400, 600), pygame.SRCALPHA)
      overlay.fill((0, 0, 0, 180))
      self.screen.blit(overlay, (0, 0))
      title_txt = self.font_big.render("MONSTER CLONE", True, WHITE)
      sub_txt = self.font_main.render("Tap to Start", True, YELLOW)
      self.screen.blit(title_txt, (20, 200))
      self.screen.blit(sub_txt, (130, 300))

    elif self.state == "PLAYING" or self.state == "CLEAR_RESULT":
      # 敵
      if self.enemy.hp > 0:
        e_rect = self.enemy.base_img.get_rect(
            center=(int(self.enemy.x), int(self.enemy.y)))
        self.screen.blit(self.enemy.base_img, e_rect)
        # 敵HPバー
        pygame.draw.rect(self.screen, BLACK, (100, 30, 200, 8))
        pygame.draw.rect(self.screen, GREEN, (100, 30,
                         200 * (self.enemy.hp / self.enemy.max_hp), 8))

      for p in self.players: p.draw(self.screen)
      self.draw_ui()

      # ドラッグ矢印
      if self.is_dragging:
        m_pos = pygame.mouse.get_pos()
        dx, dy = self.drag_start[0] - \
            m_pos[0], self.drag_start[1] - m_pos[1]
        angle = math.degrees(math.atan2(dy, dx)) - 90
        rot_arrow = pygame.transform.rotate(
            pygame.transform.smoothscale(self.img_arrow, (30, 80)), -angle)
        self.screen.blit(rot_arrow, rot_arrow.get_rect(
            center=(self.players[self.turn_index].x, self.players[self.turn_index].y)))

      # SSカットイン
      if self.ss_actor and self.ss_timer > 30:
        pygame.draw.rect(self.screen, BLACK, (0, 250, 400, 70))
        ss_txt = self.font_big.render("STRIKE SHOT!", True, PURPLE)
        self.screen.blit(ss_txt, (35, 255))

      if self.state == "CLEAR_RESULT":
        overlay = pygame.Surface((400, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        res_txt = self.font_big.render("CLEAR!", True, YELLOW)
        next_txt = self.font_main.render(
            "Tap to Next Stage", True, WHITE)
        self.screen.blit(res_txt, (110, 250))
        self.screen.blit(next_txt, (100, 320))

    pygame.display.flip()

  def run(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT:
          pygame.quit()
          sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
          if self.state == "TITLE":
            self.state = "PLAYING"
          elif self.state == "CLEAR_RESULT":
            self.current_level_idx = (
                self.current_level_idx + 1) % len(LEVEL_DATA)
            self.init_game_vars()
            self.state = "PLAYING"
          elif self.state == "PLAYING" and not self.is_moving:
            # アイコンクリック判定
            pos = event.pos
            for i in range(4):
              if pygame.Rect(55 + i * 80, 530, 50, 50).collidepoint(pos) and i == self.turn_index:
                if self.ss_charge[i] >= SS_TURN:
                  self.players[i].ss_ready = not self.players[i].ss_ready

            p = self.players[self.turn_index]
            if math.hypot(pos[0] - p.x, pos[1] - p.y) < 40:
              self.is_dragging, self.drag_start = True, pos

        if event.type == pygame.MOUSEBUTTONUP and self.is_dragging:
          m_pos = pygame.mouse.get_pos()
          dx, dy = self.drag_start[0] - \
              m_pos[0], self.drag_start[1] - m_pos[1]
          if math.hypot(dx, dy) > 10:
            p = self.players[self.turn_index]
            p.vx, p.vy = dx * 0.2, dy * 0.2
            self.is_moving, self.is_dragging = True, False
            if p.ss_ready: self.ss_charge[self.turn_index] = 0
            else: self.ss_charge = [min(SS_TURN, c + 1) for c in self.ss_charge]

      self.update()
      self.draw()
      self.clock.tick(60)

if __name__ == "__main__":
  Game().run()
