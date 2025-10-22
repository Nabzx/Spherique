import pygame, sys, math, random, argparse, io
from PIL import Image
from collections import defaultdict

class Config:
    INPUT_IMAGE_PATH = "input_image.jpg"
    WIDTH, HEIGHT = 1000, 1000
    GRAVITY = pygame.math.Vector2(0, 981)
    BOUNCE_LOSS = 0.9
    COLLISION_DAMPING = 0.95
    MIN_RADIUS, MAX_RADIUS = 5, 28
    SPAWN_INTERVAL = 1
    FIXED_DT = 1 / 60.0
    TOTAL_STEPS = 1000
    SUBSTEPS = 8
    MAX_OBJECTS = 900
    CELL_SIZE = MAX_RADIUS * 2
    BG = (0, 0, 0)

class Ball:
    def __init__(self, position, radius, step_added, color=None):
        self.position = pygame.math.Vector2(position)
        self.old_position = pygame.math.Vector2(position)
        self.acceleration = pygame.math.Vector2(0, 0)
        self.radius = radius
        self.mass = math.pi * radius**2
        self.step_added = step_added
        self.color = color or (random.randint(80,255), random.randint(80,255), random.randint(80,255))

    def accelerate(self, force):
        if self.mass > 0:
            self.acceleration += force / self.mass

    def update(self, dt):
        velocity = self.position - self.old_position
        self.old_position = self.position.copy()
        self.position += velocity + self.acceleration * dt * dt
        self.acceleration.xy = (0, 0)

    def apply_constraints(self):
        velocity = self.position - self.old_position
        if self.position.x - self.radius < 0:
            self.position.x, velocity.x = self.radius, -velocity.x * Config.BOUNCE_LOSS
        elif self.position.x + self.radius > Config.WIDTH:
            self.position.x, velocity.x = Config.WIDTH - self.radius, -velocity.x * Config.BOUNCE_LOSS
        if self.position.y - self.radius < 0:
            self.position.y, velocity.y = self.radius, -velocity.y * Config.BOUNCE_LOSS
        elif self.position.y + self.radius > Config.HEIGHT:
            self.position.y, velocity.y = Config.HEIGHT - self.radius, -velocity.y * Config.BOUNCE_LOSS
        self.old_position = self.position - velocity * Config.COLLISION_DAMPING

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.position.x), int(self.position.y)), int(self.radius))

class Simulation:
    def __init__(self, headless=False):
        pygame.init()
        self.headless = headless
        if not headless:
            self.screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))
            pygame.display.set_caption("Physics Simulation")
            self.font = pygame.font.Font(None, 30)
            self.clock = pygame.time.Clock()
        self.balls, self.grid = [], defaultdict(list)
        self.current_step = 0
        self.input_image = None
        random.seed(42)
        try:
            self.input_image = Image.open(Config.INPUT_IMAGE_PATH).convert('RGB').resize((Config.WIDTH, Config.HEIGHT))
        except: 
            self.input_image = None

    def add_ball(self, ball):
        if len(self.balls) >= Config.MAX_OBJECTS:
            self.balls.pop(0)
        self.balls.append(ball)

    def get_cell(self, pos):
        return int(pos.x // Config.CELL_SIZE), int(pos.y // Config.CELL_SIZE)

    def update_grid(self):
        self.grid.clear()
        for b in self.balls:
            self.grid[self.get_cell(b.position)].append(b)

    def get_nearby(self, b):
        cx, cy = self.get_cell(b.position)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for n in self.grid.get((cx + dx, cy + dy), []):
                    yield n

    def solve_collisions(self):
        self.update_grid()
        for b1 in self.balls:
            for b2 in self.get_nearby(b1):
                if b1 is b2: continue
                delta = b1.position - b2.position
                dist_sq = delta.length_squared()
                min_d = b1.radius + b2.radius
                if 0 < dist_sq < min_d**2:
                    dist = math.sqrt(dist_sq)
                    normal = delta / dist
                    overlap = (min_d - dist) * 0.5
                    total_mass = b1.mass + b2.mass
                    ratio1, ratio2 = b2.mass/total_mass, b1.mass/total_mass
                    sep = normal * overlap
                    b1.position += sep * ratio1 * Config.COLLISION_DAMPING
                    b2.position -= sep * ratio2 * Config.COLLISION_DAMPING

    def update(self, dt):
        sub_dt = dt / Config.SUBSTEPS
        for _ in range(Config.SUBSTEPS):
            for b in self.balls: b.accelerate(Config.GRAVITY)
            self.solve_collisions()
            for b in self.balls: b.apply_constraints()
            for b in self.balls: b.update(sub_dt)

    def draw(self):
        self.screen.fill(Config.BG)
        for b in self.balls: b.draw(self.screen)
        t = self.font.render(f"Step {self.current_step}/{Config.TOTAL_STEPS} | {len(self.balls)} balls", True, (200,200,200))
        self.screen.blit(t, (10,10))
        pygame.display.flip()

    def calculate_positions(self):
        csv_buffer = io.StringIO()
        while self.current_step < Config.TOTAL_STEPS:
            if self.current_step % Config.SPAWN_INTERVAL == 0 and len(self.balls) < Config.MAX_OBJECTS:
                pos = (Config.WIDTH/2, Config.HEIGHT/2)
                radius = random.uniform(Config.MIN_RADIUS, Config.MAX_RADIUS)
                b = Ball(pos, radius, self.current_step)
                angle = random.uniform(0, 2*math.pi)
                v = pygame.math.Vector2(math.cos(angle)*40, math.sin(angle)*40)
                b.old_position = b.position - v * Config.FIXED_DT
                self.add_ball(b)
                csv_buffer.write(f"{self.current_step},{b.position.x},{b.position.y},{b.radius},{b.old_position.x},{b.old_position.y},{b.color[0]},{b.color[1]},{b.color[2]}\n")
            self.update(Config.FIXED_DT)
            self.current_step += 1
            if self.current_step % 100 == 0:
                print(f"Calculated {self.current_step}/{Config.TOTAL_STEPS}")
        with open("ball_spawns.csv", "w") as f:
            f.write(csv_buffer.getvalue())
        if self.input_image: self.map_colors()

    def map_colors(self):
        with open('ball_spawns.csv', 'r') as f: lines = f.readlines()
        sorted_balls = sorted(self.balls, key=lambda x: x.step_added)
        out = io.StringIO()
        for i, line in enumerate(lines):
            if i >= len(sorted_balls): break
            b = sorted_balls[i]
            x, y = int(b.position.x), int(b.position.y)
            r, g, bb = self.input_image.getpixel((x, y))
            parts = line.strip().split(',')
            parts[6:9] = [str(r), str(g), str(bb)]
            out.write(','.join(parts) + '\n')
        with open('ball_spawns.csv', 'w') as f:
            f.write(out.getvalue())

    def visualize(self):
        self.balls.clear()
        self.current_step = 0
        with open('ball_spawns.csv', 'r') as f: lines = f.readlines()
        running, idx = True, 0
        while running:
            self.clock.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
            if idx < len(lines):
                step, x, y, r, ox, oy, R, G, B = map(float, lines[idx].split(','))
                if int(step) == self.current_step:
                    b = Ball((x, y), r, step, (int(R), int(G), int(B)))
                    b.old_position = pygame.math.Vector2(ox, oy)
                    self.add_ball(b)
                    idx += 1
            self.update(Config.FIXED_DT)
            self.draw()
            self.current_step += 1
        pygame.quit(); sys.exit()

    def run(self):
        self.calculate_positions()
        if not self.headless:
            self.visualize()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run without display")
    args = parser.parse_args()
    sim = Simulation(headless=args.headless)
    sim.run()
