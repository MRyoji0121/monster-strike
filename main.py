import pygame
import math
import sys
import random

WHITE, BLACK, YELLOW, RED, GREEN, PURPLE, CYAN, PINK = (255, 255, 255), (0, 0, 0), (
    255, 255, 0), (255, 0, 0), (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 105, 180)
BG_UI = (15, 15, 25)
SCREEN_WIDTH, SCREEN_HEIGHT = 400, 600
FRICTION, STOP_THRESHOLD, SS_TURN = 0.982, 0.5, 12
MAX_SPEED = 22.0
ORDER_LABELS = ["1st", "2nd", "3rd", "4th"]
WEAK_MULTIPLIER = 3.0
MAX_PLAYER_HP = 100000

LEVEL_DATA = [
    {"hp": 200000000, "pos": (200, 150), "attack": 3, "bar_color": GREEN},
    {"hp": 500000000, "pos": (200, 120), "attack": 3, "bar_color": YELLOW},
    {"hp": 1200000000, "pos": (200, 180), "attack": 2,
     "bar_color": (255, 100, 0)}
]

class DamageText:
  def __init__(self, x, y, amount, color, is_weak=False):
    self.x, self.y, self.amount, self.color, self.timer = x, y, amount, color, 35
    self.vx, self.vy, self.is_weak = random.uniform(-1.5, 1.5), -4, is_weak

  def update(self):
    self.x += self.vx; self.y += self.vy; self.vy += 0.15; self.timer -= 1

  def draw(self, screen, game_ref):
    font = game_ref.font_big if self.is_weak else game_ref.font_main
    game_ref.draw_text_with_outline(
        str(self.amount), font, self.color, int(self.x), int(self.y))

class Effect:
  def __init__(self, x, y, color, size=40, life=20):
    self.x, self.y, self.color, self.size, self.timer, self.max_timer = x, y, color, size, 0, life
    self.active = True

  def update(self):
    self.timer += 1
    if self.timer >= self.max_timer: self.active = False

  def draw(self, screen):
    ratio = self.timer / self.max_timer
    radius = int(5 + self.size * ratio)
    alpha = int(255 * (1 - ratio))
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*self.color, alpha), (radius, radius), radius)
    screen.blit(s, (self.x - radius, self.y - radius))

class LaserEffect:
  def __init__(self, x1, y1, x2, y2, color):
    self.start, self.end = (
        x1, y1), (x2, y2); self.color, self.timer, self.max_timer, self.active = color, 0, 15, True

  def update(self):
    self.timer += 1
    if self.timer >= self.max_timer: self.active = False

  def draw(self, screen):
    width = int(18 * (1 - self.timer / self.max_timer))
    if width > 0:
      pygame.draw.line(screen, WHITE, self.start, self.end, width + 4)
      pygame.draw.line(screen, self.color, self.start, self.end, width)

class HomingBullet:
  def __init__(self, x, y, target_enemy, color, damage):
    self.x, self.y = x, y; self.target = target_enemy; self.color = color; self.damage = damage
    self.speed, self.active = 12, True
    angle = random.uniform(0, math.pi * 2)
    self.vx, self.vy = math.cos(angle) * 10, math.sin(angle) * 10

  def update(self):
    dx, dy = self.target.weak_x - self.x, self.target.weak_y - self.y
    dist = math.hypot(dx, dy)
    if dist > 0:
      tx, ty = (dx / dist) * self.speed, (dy / dist) * self.speed
      self.vx += (tx - self.vx) * 0.25; self.vy += (ty - self.vy) * 0.25
    self.x += self.vx; self.y += self.vy
    if dist < 15 or math.hypot(self.target.x - self.x, self.target.y - self.y) < self.target.radius:
      self.active = False

  def draw(self, screen):
    pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 7)
    pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 5)

class Player:
  def __init__(self, x, y, index, img, game_ref):
    self.start_pos = (
        x, y); self.img = img; self.radius = 20; self.index = index; self.game = game_ref; self.reset()

  def reset(self):
    self.x, self.y = self.start_pos; self.vx, self.vy = 0, 0; self.ss_phase = 0; self.ss_ready = False; self.combo_used = False

  def update(self):
    if self.ss_phase == 1: return
    speed = math.hypot(self.vx, self.vy)
    if speed > 0:
      self.x += self.vx; self.y += self.vy; self.vx *= FRICTION; self.vy *= FRICTION
      if speed < STOP_THRESHOLD: self.vx, self.vy = 0, 0
      if self.x < self.radius: self.x = self.radius; self.vx *= -1
      elif self.x > SCREEN_WIDTH - self.radius: self.x = SCREEN_WIDTH - self.radius; self.vx *= -1
      if self.y < self.radius: self.y = self.radius; self.vy *= -1
      elif self.y > 480 - self.radius: self.y = 480 - self.radius; self.vy *= -1

  def draw(self, screen, current_turn_idx):
    draw_img = self.img.copy()
    if self.ss_phase == 2: draw_img.fill(
        (255, 0, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
    screen.blit(draw_img, draw_img.get_rect(
        center=(int(self.x), int(self.y))))
    if not self.combo_used and self.index != current_turn_idx:
      pygame.draw.circle(screen, CYAN if self.index % 2 == 0 else YELLOW, (int(
          self.x), int(self.y)), self.radius + 3, 2)
    label_col = YELLOW if self.index == current_turn_idx else WHITE
    self.game.draw_text_with_outline(
        ORDER_LABELS[self.index], self.game.font_ui, label_col, int(self.x), int(self.y - 30))
    if self.ss_ready: pygame.draw.circle(
        screen, RED, (int(self.x), int(self.y)), self.radius + 4, 3)

class Enemy:
  def __init__(self, img):
    self.base_img = pygame.transform.smoothscale(
        img, (140, 140)); self.radius = 60; self.hp = 0; self.weak_angle = 0; self.weak_radius = 18

  def set_level(self, data):
    self.x, self.y, self.hp, self.max_hp, self.attack_timer, self.bar_col = data["pos"][
        0], data["pos"][1], data["hp"], data["hp"], data["attack"], data["bar_color"]
    self.weak_angle = random.uniform(0, math.pi * 2)

  def update(self):
    self.weak_angle += 0.03
    self.weak_x, self.weak_y = self.x + \
        math.cos(self.weak_angle) * self.radius, self.y + \
        math.sin(self.weak_angle) * self.radius

  def draw(self, screen):
    screen.blit(self.base_img, self.base_img.get_rect(
        center=(int(self.x), int(self.y))))
    pts = [(self.weak_x + math.cos(self.weak_angle + i * (math.pi * 2 / 3)) * 12,
            self.weak_y + math.sin(self.weak_angle + i * (math.pi * 2 / 3)) * 12) for i in range(3)]
    pygame.draw.polygon(screen, YELLOW, pts); pygame.draw.circle(
        screen, WHITE, (int(self.weak_x), int(self.weak_y)), 14, 2)

class EnemyBullet:
  def __init__(self, x, y, tx, ty):
    a = math.atan2(ty - y, tx - x); self.x, self.y, self.vx, self.vy, self.active = x, y, math.cos(
        a) * 7.5, math.sin(a) * 7.5, True

  def update(self):
    self.x += self.vx; self.y += self.vy
    if not (0 <= self.x <= SCREEN_WIDTH and 0 <=
            self.y <= SCREEN_HEIGHT): self.active = False

class Game:
  def __init__(self):
    pygame.init()
    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    self.clock = pygame.time.Clock(); self.load_assets()
    self.state, self.current_level_idx = "TITLE", 0
    self.enemy = Enemy(self.img_enemy)
    self.players = [Player(80, 420, 0, self.player_thumb, self), Player(160, 380, 1, self.player_thumb, self),
                    Player(240, 420, 2, self.player_thumb, self), Player(320, 440, 3, self.player_thumb, self)]
    self.ss_charge = [0, 0, 0, 0]
    self.current_hp = MAX_PLAYER_HP
    self.init_game_vars()

  def load_assets(self):
    def load_or_dummy(name, size, color):
      try: return pygame.transform.smoothscale(pygame.image.load(name).convert_alpha(), size)
      except: s = pygame.Surface(size, pygame.SRCALPHA); s.fill(color); return s
    self.img_player, self.img_arrow, self.img_icon = load_or_dummy('asset/img/image_0.png', (40, 40), WHITE), load_or_dummy(
        'asset//img/image_1.png', (35, 90), YELLOW), load_or_dummy('asset/img/image_2.png', (50, 50), WHITE)
    self.player_thumb = self.img_player
    self.img_bg = pygame.transform.smoothscale(load_or_dummy(
        'asset/img/image_3.png', (400, 600), (30, 30, 35)), (400, 600))
    self.img_enemy = load_or_dummy('asset/img/image_4.png', (140, 140), GREEN)
    self.font_main, self.font_big, self.font_ui = pygame.font.SysFont(
        "impact", 26), pygame.font.SysFont("impact", 56), pygame.font.SysFont("arialrounded", 18, True)

  def draw_text_with_outline(self, text, font, color, x, y):
    text_s = font.render(text, True, color); outline_s = font.render(
        text, True, BLACK); r = text_s.get_rect(center=(x, y))
    for dx, dy in [(-2, 0), (2, 0), (0, -2),
                   (0, 2)]: self.screen.blit(outline_s, r.move(dx, dy))
    self.screen.blit(text_s, r)

  def init_game_vars(self):
    self.enemy.set_level(LEVEL_DATA[self.current_level_idx])
    self.enemy_bullets, self.effects, self.damage_texts, self.lasers, self.homings = [], [], [], [], []
    for p in self.players: p.reset()
    self.turn_index, self.is_moving, self.is_dragging, self.ss_actor, self.ss_timer = 0, False, False, None, 0

  def damage_enemy(self, amount, x, y, is_ss=False, is_weak=False, is_combo=False):
    if self.enemy.hp <= 0: return
    final_dmg = int(amount * (WEAK_MULTIPLIER if is_weak else 1.0))
    self.enemy.hp -= final_dmg
    col = CYAN if is_combo else (
        RED if is_weak else (YELLOW if is_ss else WHITE))
    self.damage_texts.append(DamageText(
        x, y, final_dmg, col, is_weak or is_ss))
    self.effects.append(Effect(x, y, col, 60 if is_weak else 30))
    if self.enemy.hp <= 0:
      self.state = "CLEAR_RESULT"
      for i in range(8): self.effects.append(Effect(
          self.enemy.x + random.randint(-30, 30), self.enemy.y + random.randint(-30, 30), RED, 80))

  def activate_friend_combo(self, p):
    p.combo_used = True
    dx_w, dy_w = self.enemy.weak_x - p.x, self.enemy.weak_y - p.y
    dist_w = math.hypot(dx_w, dy_w)
    laser_weak = dist_w < 50
    if p.index % 2 == 0:
      self.lasers.append(LaserEffect(
          p.x, p.y, self.enemy.x, self.enemy.y, CYAN))
      self.damage_enemy(11000000, self.enemy.x, self.enemy.y,
                        is_combo=True, is_weak=laser_weak)
      for _ in range(5): self.homings.append(
          HomingBullet(p.x, p.y, self.enemy, PINK, 600000))
    else:
      for _ in range(12): self.homings.append(
          HomingBullet(p.x, p.y, self.enemy, YELLOW, 1200000))
      self.lasers.append(LaserEffect(
          p.x, p.y, self.enemy.x, self.enemy.y, PINK))
      self.damage_enemy(5000000, self.enemy.x, self.enemy.y,
                        is_combo=True, is_weak=laser_weak)

  def update(self):
    if self.state != "PLAYING": return
    self.enemy.update(
    ); all_stopped, active_p = True, self.players[self.turn_index]
    for p in self.players:
      p.update()
      if p.vx != 0 or p.vy != 0 or p.ss_phase == 1: all_stopped = False
      if self.is_moving and p.index != self.turn_index and not p.combo_used:
        if math.hypot(active_p.x - p.x, active_p.y - p.y) < active_p.radius + p.radius:
          self.activate_friend_combo(p)
      if self.enemy.hp > 0:
        dw = math.hypot(p.x - self.enemy.weak_x,
                        p.y - self.enemy.weak_y)
        db = math.hypot(p.x - self.enemy.x, p.y - self.enemy.y)
        if dw < p.radius + self.enemy.weak_radius:
          spd = math.hypot(p.vx, p.vy)
          if spd > 1.0:
            self.damage_enemy(4500000, p.x, p.y,
                              p.ss_phase == 2, True)
            angle = math.atan2(
                p.y - self.enemy.weak_y, p.x - self.enemy.weak_x)
            p.vx, p.vy = math.cos(
                angle) * spd, math.sin(angle) * spd
        elif db < p.radius + self.enemy.radius:
          spd = math.hypot(p.vx, p.vy)
          if p.ss_ready and p.ss_phase == 0: p.ss_phase, p.vx, p.vy, self.ss_actor, self.ss_timer = 1, 0, 0, p, 80
          elif spd > 1.2:
            self.damage_enemy(3500000, p.x, p.y, p.ss_phase == 2)
            angle = math.atan2(
                p.y - self.enemy.y, p.x - self.enemy.x)
            p.vx, p.vy = math.cos(
                angle) * spd, math.sin(angle) * spd
    for h in self.homings[:]:
      h.update()
      if not h.active:
        hw = math.hypot(h.x - self.enemy.weak_x,
                        h.y - self.enemy.weak_y) < 25
        self.damage_enemy(h.damage, self.enemy.x,
                          self.enemy.y, is_combo=True, is_weak=hw)
        self.homings.remove(h)
    if self.ss_actor:
      self.ss_timer -= 1
      if self.ss_timer % 4 == 0: self.damage_enemy(
          15000000, self.ss_actor.x + random.randint(-20, 20), self.ss_actor.y, True)
      if self.ss_timer <= 0:
        a = math.atan2(self.enemy.y - self.ss_actor.y,
                       self.enemy.x - self.ss_actor.x)
        self.ss_actor.ss_phase, self.ss_actor.vx, self.ss_actor.vy, self.ss_actor = 2, math.cos(
            a) * MAX_SPEED, math.sin(a) * MAX_SPEED, None
    for eb in self.enemy_bullets[:]:
      eb.update()
      for p in self.players:
        if math.hypot(eb.x - p.x, eb.y - p.y) < p.radius + 6:
          self.current_hp -= 8000
          self.effects.append(Effect(eb.x, eb.y, PURPLE))
          eb.active = False; break
      if not eb.active: self.enemy_bullets.remove(eb)

    if self.current_hp <= 0: self.current_hp = 0; self.state = "GAME_OVER"

    for obj in self.effects + self.lasers + self.damage_texts: obj.update()
    self.effects, self.lasers, self.damage_texts = [e for e in self.effects if e.active], [
        l for l in self.lasers if l.active], [d for d in self.damage_texts if d.timer > 0]
    if self.is_moving and all_stopped:
      self.is_moving, self.turn_index = False, (self.turn_index + 1) % 4
      for p in self.players: p.ss_phase, p.ss_ready, p.combo_used = 0, False, False
      self.enemy.attack_timer -= 1
      if self.enemy.attack_timer <= 0:
        for p in self.players: self.enemy_bullets.append(
            EnemyBullet(self.enemy.x, self.enemy.y, p.x, p.y))
        self.enemy.attack_timer = 3

  def draw_ui(self):
    pygame.draw.rect(self.screen, BG_UI, (0, 480, 400, 120))
    hp_r = pygame.Rect(40, 490, 320, 15); pygame.draw.rect(
        self.screen, (40, 40, 50), hp_r, 0, 5)
    pygame.draw.rect(self.screen, GREEN if self.current_hp > 30000 else RED,
                     (40, 490, 320 * (self.current_hp / MAX_PLAYER_HP), 15), 0, 5)
    for i in range(4):
      x = 10 + i * 98; panel_rect = pygame.Rect(x, 510, 90, 80); color = (
          120, 110, 40) if i == self.turn_index else (60, 60, 80)
      pygame.draw.rect(self.screen, color, panel_rect, 0, 10); pygame.draw.rect(
          self.screen, WHITE if i == self.turn_index else (80, 80, 100), panel_rect, 2, 10)
      ic = pygame.transform.smoothscale(self.img_icon, (45, 45)); self.screen.blit(
          ic, ic.get_rect(center=(x + 45, 545)))
      txt = "OK" if self.ss_charge[i] >= SS_TURN else str(
          SS_TURN - self.ss_charge[i])
      self.draw_text_with_outline(
          f"SS: {txt}", self.font_ui, YELLOW if txt == "OK" else (180, 180, 180), x + 45, 575)

  def draw(self):
    self.screen.blit(self.img_bg, (0, 0))
    if self.state == "TITLE":
      ov = pygame.Surface((400, 600), pygame.SRCALPHA); ov.fill(
          (0, 0, 0, 210)); self.screen.blit(ov, (0, 0))
      self.draw_text_with_outline("MONSTER CLONE", self.font_big, WHITE, 200, 230); self.draw_text_with_outline(
          "TAP TO START", self.font_main, YELLOW, 200, 310)
    elif self.state in ["PLAYING", "CLEAR_RESULT", "GAME_OVER"]:
      if self.enemy.hp > 0:
        self.enemy.draw(self.screen)
        pygame.draw.rect(self.screen, (50, 50, 50), (40, 15, 320, 10), 0, 5); pygame.draw.rect(
            self.screen, self.enemy.bar_col, (40, 15, 320 * (self.enemy.hp / self.enemy.max_hp), 10), 0, 5)
      for p in self.players: p.draw(self.screen, self.turn_index)
      for l in self.lasers: l.draw(self.screen)
      for h in self.homings: h.draw(self.screen)
      for eb in self.enemy_bullets: pygame.draw.circle(self.screen, PURPLE, (int(eb.x), int(
          eb.y)), 10); pygame.draw.circle(self.screen, WHITE, (int(eb.x), int(eb.y)), 6)
      for e in self.effects: e.draw(self.screen)
      for d in self.damage_texts: d.draw(self.screen, self)
      self.draw_ui()
      if self.is_dragging:
        m = pygame.mouse.get_pos(); p = self.players[self.turn_index]
        rev_dx, rev_dy = self.drag_start[0] - \
            m[0], self.drag_start[1] - m[1]
        for j in range(1, 11):
          px, py = p.x + rev_dx * 0.15 * j, p.y + rev_dy * 0.15 * j
          if 0 < px < SCREEN_WIDTH and 0 < py < 480: pygame.draw.circle(
              self.screen, WHITE, (int(px), int(py)), 3)
        ar = pygame.transform.rotate(
            self.img_arrow, -math.degrees(math.atan2(-rev_dy, -rev_dx)) + 90)
        self.screen.blit(ar, ar.get_rect(center=(p.x, p.y)))
      if self.state == "CLEAR_RESULT":
        ov = pygame.Surface((400, 600), pygame.SRCALPHA); ov.fill(
            (0, 0, 0, 180)); self.screen.blit(ov, (0, 0))
        self.draw_text_with_outline(
            "STAGE CLEAR!", self.font_big, YELLOW, 200, 260)
      if self.state == "GAME_OVER":
        ov = pygame.Surface((400, 600), pygame.SRCALPHA); ov.fill(
            (0, 0, 0, 200)); self.screen.blit(ov, (0, 0))
        self.draw_text_with_outline("GAME OVER", self.font_big, RED, 200, 260); self.draw_text_with_outline(
            "TAP TO RESTART", self.font_main, WHITE, 200, 320)
    pygame.display.flip()

  def run(self):
    while True:
      for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
          if self.state == "TITLE": self.state = "PLAYING"
          elif self.state == "GAME_OVER":
            self.current_hp = MAX_PLAYER_HP; self.current_level_idx = 0; self.ss_charge = [
                0, 0, 0, 0]; self.init_game_vars(); self.state = "PLAYING"
          elif self.state == "CLEAR_RESULT":
            self.current_level_idx = (self.current_level_idx + 1) % len(
                LEVEL_DATA); self.init_game_vars(); self.state = "PLAYING"
          elif self.state == "PLAYING" and not self.is_moving:
            for i in range(4):
              if pygame.Rect(10 + i * 98, 510, 90, 80).collidepoint(event.pos) and i == self.turn_index:
                if self.ss_charge[i] >= SS_TURN:
                  self.players[i].ss_ready = not self.players[i].ss_ready
            p = self.players[self.turn_index]
            if math.hypot(
                event.pos[0] - p.x, event.pos[1] - p.y) < 45: self.is_dragging, self.drag_start = True, event.pos
        if event.type == pygame.MOUSEBUTTONUP and self.is_dragging:
          m = pygame.mouse.get_pos(
          ); dx, dy = self.drag_start[0] - m[0], self.drag_start[1] - m[1]
          dist = math.hypot(dx, dy)
          if dist > 12:
            power = min(dist * 0.28, MAX_SPEED)
            angle = math.atan2(dy, dx)
            p = self.players[self.turn_index]
            p.vx, p.vy = math.cos(
                angle) * power, math.sin(angle) * power
            self.is_moving, self.is_dragging = True, False
            if p.ss_ready: self.ss_charge[self.turn_index] = 0
            else: self.ss_charge = [min(SS_TURN, c + 1) for c in self.ss_charge]
          else: self.is_dragging = False
      self.update(); self.draw(); self.clock.tick(60)

if __name__ == "__main__": Game().run()
