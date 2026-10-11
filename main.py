
import sys
import math
import random
import pygame

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

pygame.init()
W, H = 1000, 760
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("QUBIT QUEST: Quantum Vault")
clock = pygame.time.Clock()

WHITE = (240, 245, 255)
MUTED = (157, 180, 211)
RED = (255, 105, 125)
GREEN = (100, 245, 165)
YELLOW = (255, 220, 110)

THEMES = [
    {"bg": (8, 14, 32), "panel": (20, 30, 55),
     "edge": (65, 220, 255), "accent": (190, 120, 255)},
    {"bg": (20, 12, 34), "panel": (39, 25, 60),
     "edge": (255, 130, 210), "accent": (120, 190, 255)},
    {"bg": (7, 27, 29), "panel": (17, 48, 48),
     "edge": (90, 255, 195), "accent": (255, 205, 100)},
    {"bg": (29, 18, 9), "panel": (54, 36, 22),
     "edge": (255, 190, 85), "accent": (255, 115, 115)},
    {"bg": (10, 20, 43), "panel": (23, 40, 75),
     "edge": (125, 160, 255), "accent": (90, 255, 235)},
]

FONT = pygame.font.SysFont("consolas", 18)
SMALL = pygame.font.SysFont("consolas", 14)
MED = pygame.font.SysFont("consolas", 25, bold=True)
BIG = pygame.font.SysFont("consolas", 39, bold=True)

STARS = [(random.randrange(W), random.randrange(H)) for _ in range(90)]


def draw_text(value, x, y, color=WHITE, font=FONT, center=False):
    image = font.render(str(value), True, color)
    rect = image.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(image, rect)


def draw_panel(rect, fill, edge, radius=12):
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    pygame.draw.rect(screen, edge, rect, 2, border_radius=radius)


def draw_button(rect, label, fill, edge, enabled=True):
    if not enabled:
        fill = (43, 48, 65)
        edge = (85, 92, 112)
    draw_panel(rect, fill, edge, 10)
    draw_text(label, rect.centerx, rect.centery, WHITE, SMALL, True)


def grover_search(target, n, shots=256):
    """Run Grover search on a real Qiskit Aer simulator."""
    if not QISKIT_AVAILABLE:
        raise RuntimeError("Install qiskit and qiskit-aer first.")

    size = 2 ** n
    qc = QuantumCircuit(n, n)
    qc.h(range(n))

    # One marked state: the vault number is encoded in the oracle.
    iterations = max(1, round(math.pi / 4 * math.sqrt(size)))

    for _ in range(iterations):
        # Oracle: phase-flip the marked target state.
        bits = format(target, f"0{n}b")
        zero_qubits = []

        for q, bit in enumerate(reversed(bits)):
            if bit == "0":
                qc.x(q)
                zero_qubits.append(q)

        if n == 1:
            qc.z(0)
        else:
            qc.h(n - 1)
            qc.mcx(list(range(n - 1)), n - 1)
            qc.h(n - 1)

        for q in zero_qubits:
            qc.x(q)

        # Diffusion operator.
        qc.h(range(n))
        qc.x(range(n))

        if n == 1:
            qc.z(0)
        else:
            qc.h(n - 1)
            qc.mcx(list(range(n - 1)), n - 1)
            qc.h(n - 1)

        qc.x(range(n))
        qc.h(range(n))

    qc.measure(range(n), range(n))
    simulator = AerSimulator()
    result = simulator.run(
        transpile(qc, simulator), shots=shots
    ).result()

    return result.get_counts()


class VaultGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.level = 1
        self.score = 0
        self.streak = 0
        self.lives = 3
        self.scans = 2
        self.screen_name = "menu"
        self.new_puzzle()

    def new_puzzle(self):
        # The interface expands from 4x4 to 5x5 and then 6x6.
        self.size = min(4 + (self.level - 1) // 2, 6)
        self.total = self.size * self.size
        self.target = random.randrange(self.total)
        self.target_row = self.target // self.size
        self.target_col = self.target % self.size
        self.guesses = 0
        self.revealed = False
        self.scan_result = None
        self.scan_counts = None
        self.feedback = "Study the clues. Find the correct vault!"
        self.feedback_color = WHITE
        self.make_clues()

    def features(self, cell):
        r, c = divmod(cell, self.size)
        return {
            "odd row": r % 2 == 0,
            "even row": r % 2 == 1,
            "odd column": c % 2 == 0,
            "even column": c % 2 == 1,
            "top row": r == 0,
            "bottom row": r == self.size - 1,
            "left column": c == 0,
            "right column": c == self.size - 1,
            "main diagonal": r == c,
            "anti-diagonal": r + c == self.size - 1,
            "above middle": r < self.size / 2,
            "below middle": r >= self.size / 2,
        }

    def make_clues(self):
        # Choose clues that are true of the target but leave
        # multiple possible vaults for the player to investigate.
        target_features = self.features(self.target)
        available = list(target_features.keys())
        random.shuffle(available)

        chosen = []
        candidates = list(range(self.total))

        for clue in available:
            if not target_features[clue]:
                continue

            trial = [
                cell for cell in candidates
                if self.features(cell)[clue]
            ]

            if 2 <= len(trial) < len(candidates):
                chosen.append(clue)
                candidates = trial

            if len(chosen) >= min(3, 1 + self.level // 2):
                break

        # Guarantee that at least two possibilities remain.
        if len(candidates) < 2:
            chosen = []
            candidates = list(range(self.total))
            for clue in available:
                if not target_features[clue]:
                    continue
                trial = [
                    cell for cell in candidates
                    if self.features(cell)[clue]
                ]
                if len(trial) >= 2 and len(trial) < len(candidates):
                    chosen.append(clue)
                    candidates = trial
                    break

        self.clues = chosen
        self.possible = [
            cell for cell in range(self.total)
            if all(self.features(cell)[clue] for clue in self.clues)
        ]

        # The target is guaranteed to satisfy every displayed clue.
        assert self.target in self.possible
        assert len(self.possible) >= 2

    def choose(self, cell):
        if self.revealed or self.screen_name != "game":
            return

        # The clues define the valid search space.
        if cell not in self.possible:
            self.lives -= 1
            self.streak = 0
            self.feedback = "That vault breaks a clue! One life lost."
            self.feedback_color = RED
        elif cell == self.target:
            self.revealed = True
            points = max(100, 250 - (self.guesses * 25)) + self.level * 20
            self.score += points
            self.streak += 1
            self.feedback = f"VAULT OPENED! +{points} points!"
            self.feedback_color = GREEN
        else:
            self.lives -= 1
            self.streak = 0
            self.feedback = "Valid candidate, but not the target. One life lost."
            self.feedback_color = RED

        self.guesses += 1
        if self.lives <= 0:
            self.screen_name = "gameover"

    def run_scan(self):
        if self.revealed:
            return
        if self.scans <= 0:
            self.feedback = "No quantum scans left!"
            self.feedback_color = RED
            return

        try:
            # Search within the clue-compatible candidates.
            # The oracle marks the actual hidden target.
            # Candidate indices are encoded into a compact search space.
            candidates = self.possible
            compact_target = candidates.index(self.target)
            n = max(1, math.ceil(math.log2(len(candidates))))

            # Use Grover on a power-of-two register. The target index
            # is the marked state; unused indices are never shown as vaults.
            counts = grover_search(compact_target, n, shots=256)
            self.scans -= 1
            self.scan_counts = counts

            # Map the most frequent measured bit string to a candidate.
            measured = max(counts, key=counts.get)
            result_index = int(measured, 2)

            if result_index < len(candidates):
                self.scan_result = candidates[result_index]
                self.feedback = (
                    f"Scan suggests vault {self.scan_result + 1}. "
                    "Use the clues before deciding!"
                )
            else:
                self.scan_result = None
                self.feedback = "Scan returned an unused state. Try another clue."
            self.feedback_color = self.theme()["edge"]

        except Exception as exc:
            self.feedback = f"Quantum scan failed: {type(exc).__name__}"
            self.feedback_color = RED

    def theme(self):
        return THEMES[(self.level - 1) % len(THEMES)]

    def next_level(self):
        if not self.revealed:
            return
        self.level += 1
        self.scans = min(2 + self.level // 3, 5)
        self.new_puzzle()

    def draw_background(self):
        t = self.theme()
        screen.fill(t["bg"])
        for x in range(0, W, 50):
            pygame.draw.line(screen, (24, 35, 57), (x, 0), (x, H))
        for y in range(0, H, 50):
            pygame.draw.line(screen, (24, 35, 57), (0, y), (W, y))
        for p in STARS:
            pygame.draw.circle(screen, (65, 91, 132), p, 1)

    def draw_menu(self):
        self.draw_background()
        t = self.theme()
        draw_text("QUBIT QUEST", W // 2, 110, t["edge"], BIG, True)
        draw_text("THE QUANTUM VAULT", W // 2, 165, t["accent"], MED, True)

        draw_panel(pygame.Rect(120, 225, 760, 235), t["panel"], t["edge"])
        draw_text("MISSION BRIEFING", 155, 255, YELLOW, MED)
        draw_text("1. Read the clues to narrow down the vaults.", 155, 310)
        draw_text("2. Select a vault that satisfies every clue.", 155, 350)
        draw_text("3. Use limited Grover scans when you need help.", 155, 390)
        draw_button(
            pygame.Rect(340, 505, 320, 62),
            "START MISSION", t["panel"], t["edge"]
        )
        draw_text("ENTER to start   |   ESC to quit", W // 2, 620, MUTED, SMALL, True)

    def draw_game(self):
        self.draw_background()
        t = self.theme()
        draw_text("QUANTUM VAULT", 20, 15, t["edge"], MED)
        draw_text(f"LEVEL {self.level}", 310, 22, YELLOW, SMALL)
        draw_text(f"SCORE {self.score}", 430, 22, WHITE, SMALL)
        draw_text(f"STREAK {self.streak}", 560, 22, t["accent"], SMALL)
        draw_text(f"LIVES {self.lives}", 690, 22, RED, SMALL)
        draw_text(f"SCANS {self.scans}", 820, 22, t["edge"], SMALL)

        # Grid width adjusts automatically at every size change.
        grid_x, grid_y = 30, 105
        grid_area_w, grid_area_h = 570, 520
        cell_w = min(90, (grid_area_w - 30) // self.size)
        cell_h = min(72, (grid_area_h - 55) // self.size)
        gap = 8
        actual_w = self.size * cell_w + (self.size - 1) * gap
        start_x = grid_x + (grid_area_w - actual_w) // 2

        draw_panel(
            pygame.Rect(15, 65, 600, 570), t["panel"], t["edge"]
        )
        draw_text("VAULT GRID", 35, 75, YELLOW, MED)

        self.cell_rects = []
        for c in range(self.size):
            x = start_x + c * (cell_w + gap)
            draw_text(f"C{c + 1}", x + cell_w // 2, 102, MUTED, SMALL, True)

        for r in range(self.size):
            y = grid_y + 35 + r * (cell_h + gap)
            draw_text(f"R{r + 1}", 25, y + cell_h // 2, MUTED, SMALL, True)

            for c in range(self.size):
                cell = r * self.size + c
                x = start_x + c * (cell_w + gap)
                rect = pygame.Rect(x, y, cell_w, cell_h)
                self.cell_rects.append(rect)

                fill = (28, 42, 70)
                edge = (64, 86, 126)

                if cell not in self.possible:
                    fill = (17, 23, 39)
                    edge = (43, 51, 68)

                if self.scan_result == cell:
                    fill, edge = (76, 55, 106), t["accent"]

                if self.revealed and cell == self.target:
                    fill, edge = (18, 103, 68), GREEN

                draw_panel(rect, fill, edge, 8)
                label = "LOCKED" if cell not in self.possible else f"VAULT {cell + 1}"
                draw_text(label, rect.centerx, rect.centery, WHITE, SMALL, True)

        # Intelligence panel
        draw_panel(
            pygame.Rect(635, 65, 350, 570), t["panel"], t["accent"]
        )
        draw_text("INTELLIGENCE", 655, 85, t["edge"], MED)
        draw_text(f"Grid: {self.size} x {self.size}", 655, 130, WHITE, SMALL)
        draw_text(f"Possible vaults: {len(self.possible)}", 655, 155, WHITE, SMALL)

        draw_text("CLUES", 655, 200, YELLOW, FONT)
        y = 235
        for i, clue in enumerate(self.clues):
            draw_text(f"{i + 1}. Target is in the", 655, y, MUTED, SMALL)
            draw_text(clue + ".", 675, y + 20, WHITE, SMALL)
            y += 57

        draw_text("RULES", 655, 425, t["accent"], FONT)
        draw_text("Rows: top to bottom", 655, 455, MUTED, SMALL)
        draw_text("Columns: left to right", 655, 477, MUTED, SMALL)
        draw_text("Locked vaults break a clue.", 655, 499, MUTED, SMALL)

        draw_button(
            pygame.Rect(655, 535, 300, 40),
            "RUN GROVER SCAN", (35, 52, 100), t["edge"]
        )
        draw_button(
            pygame.Rect(655, 583, 300, 35),
            "REPEAT CLUES", (65, 43, 89), t["accent"]
        )

        draw_text(
            self.feedback, W // 2, 660,
            self.feedback_color, SMALL, True
        )
        draw_text(
            "ESC quit | Click vaults to investigate",
            W // 2, 690, MUTED, SMALL, True
        )

        if self.revealed:
            draw_panel(
                pygame.Rect(250, 275, 500, 155),
                (15, 53, 43), GREEN
            )
            draw_text("VAULT UNLOCKED!", W // 2, 305, GREEN, MED, True)
            draw_text(f"Score: {self.score}", W // 2, 345, WHITE, FONT, True)
            draw_button(
                pygame.Rect(350, 375, 300, 40),
                "NEXT LEVEL", (20, 90, 65), GREEN
            )

    def draw_gameover(self):
        self.draw_background()
        t = self.theme()
        draw_text("MISSION FAILED", W // 2, 230, RED, BIG, True)
        draw_text(f"Final score: {self.score}", W // 2, 305, YELLOW, MED, True)
        draw_text(f"Reached level: {self.level}", W // 2, 350, WHITE, FONT, True)
        draw_button(
            pygame.Rect(340, 420, 320, 60),
            "PLAY AGAIN", t["panel"], t["edge"]
        )

    def draw(self):
        if self.screen_name == "menu":
            self.draw_menu()
        elif self.screen_name == "game":
            self.draw_game()
        else:
            self.draw_gameover()


def main():
    game = VaultGame()
    running = True

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif game.screen_name == "menu":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.screen_name = "game"
                elif game.screen_name == "gameover":
                    if event.key in (pygame.K_RETURN, pygame.K_r):
                        game.reset()
                elif game.screen_name == "game":
                    if event.key == pygame.K_RETURN and game.revealed:
                        game.next_level()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if game.screen_name == "menu":
                    if pygame.Rect(340, 505, 320, 62).collidepoint(pos):
                        game.screen_name = "game"

                elif game.screen_name == "gameover":
                    if pygame.Rect(340, 420, 320, 60).collidepoint(pos):
                        game.reset()

                elif game.screen_name == "game":
                    if game.revealed:
                        if pygame.Rect(350, 375, 300, 40).collidepoint(pos):
                            game.next_level()
                    else:
                        for i, rect in enumerate(game.cell_rects):
                            if rect.collidepoint(pos):
                                game.choose(i)
                                break

                        if pygame.Rect(655, 535, 300, 40).collidepoint(pos):
                            game.run_scan()
                        elif pygame.Rect(655, 583, 300, 35).collidepoint(pos):
                            game.feedback = (
                                "Clues: " + "; ".join(self for self in game.clues)
                            )
                            game.feedback_color = YELLOW

        game.draw()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
