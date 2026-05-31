import json
import math
import random
from pathlib import Path

import pygame


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
QUESTIONS_FILE_JSON = ASSETS_DIR / "questions.json"
FONT_FILE = BASE_DIR / "uvKits.ttf"
SAVE_FILE = BASE_DIR / "savegame.json"
SOUNDS_DIR = ASSETS_DIR / "sounds"

WIDTH = 1212
HEIGHT = 576
FPS = 60

WHITE = (245, 247, 252)
BLACK = (15, 18, 28)
BLUE = (23, 55, 112)
BLUE_DARK = (10, 26, 67)
BLUE_LIGHT = (54, 103, 190)
GOLD = (246, 186, 58)
GREEN = (71, 174, 101)
RED = (211, 77, 77)
PANEL = (20, 32, 68)
BUTTON_PANEL = (116, 113, 68)
BUTTON_PANEL_DARK = (76, 74, 45)
BUTTON_BORDER = (162, 155, 101)
QUESTION_COUNT = 15

PRIZES_15 = [
    100,
    200,
    300,
    500,
    1_000,
    2_000,
    4_000,
    8_000,
    16_000,
    32_000,
    64_000,
    125_000,
    250_000,
    500_000,
    1_000_000,
]

DIFFICULTIES = {
    "easy": {"title": "Легкий уровень", "prizes": PRIZES_15},
    "medium": {"title": "Средний уровень", "prizes": PRIZES_15},
    "hard": {"title": "Сложный уровень", "prizes": PRIZES_15},
}

# Ищет первый подходящий файл ассета по нескольким возможным именам.
def find_asset(*names):
    for name in names:
        for suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            path = ASSETS_DIR / f"{name}{suffix}"
            if path.exists():
                return path
    return None


# Обрезает прозрачные или фоновые поля вокруг изображения.
def trim_visible(image, colorkey=None):
    min_x = image.get_width()
    min_y = image.get_height()
    max_x = -1
    max_y = -1
    for y in range(image.get_height()):
        for x in range(image.get_width()):
            pixel = image.get_at((x, y))
            if pixel.a == 0:
                continue
            if colorkey is not None and pixel.r == colorkey[0] and pixel.g == colorkey[1] and pixel.b == colorkey[2]:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if max_x < min_x or max_y < min_y:
        return image
    bounds = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return image.subsurface(bounds).copy()


# Удаляет только фон, связанный с краями кадра, сохраняя детали внутри спрайта.
def remove_edge_background(image, color=(0, 0, 0)):
    result = image.copy()
    width, height = result.get_size()
    visited = set()
    stack = []

    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in visited or x < 0 or y < 0 or x >= width or y >= height:
            continue
        visited.add((x, y))
        pixel = result.get_at((x, y))
        if pixel.a == 0 or (pixel.r, pixel.g, pixel.b) != color:
            continue
        result.set_at((x, y), (0, 0, 0, 0))
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    return result


# Загружает изображение, при необходимости обрезает фон и меняет размер.
def load_image(name_candidates, size=None, colorkey=None, trim=False):
    path = find_asset(*name_candidates)
    if not path:
        return None
    image = pygame.image.load(path).convert_alpha()
    if colorkey is not None:
        image.set_colorkey(colorkey)
    if trim:
        image = trim_visible(image, colorkey)
    if size:
        image = pygame.transform.smoothscale(image, size)
    return image


# Нарезает горизонтальный спрайт-лист на отдельные кадры анимации.
def split_sheet(sheet, frame_count, remove_black_edges=False):
    if not sheet:
        return []
    frame_width = sheet.get_width() // frame_count
    frames = []
    for index in range(frame_count):
        frame = pygame.Surface((frame_width, sheet.get_height()), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), (index * frame_width, 0, frame_width, sheet.get_height()))
        if remove_black_edges:
            frame = remove_edge_background(frame, (0, 0, 0))
        frames.append(frame)
    return frames


# Приводит вопрос из JSON к единому внутреннему формату.
def normalize_question(item):
    answers = item.get("answers") or [
        item.get("answer_a"),
        item.get("answer_b"),
        item.get("answer_c"),
        item.get("answer_d"),
    ]
    answers = [str(answer) for answer in answers if answer is not None]
    correct = item.get("correct", item.get("correct_index", item.get("right")))

    if isinstance(correct, str) and correct.strip().isdigit():
        correct = int(correct)
    elif isinstance(correct, str) and correct in answers:
        correct = answers.index(correct)

    if len(answers) != 4 or not isinstance(correct, int):
        return None

    if correct > 3:
        correct -= 1

    if correct < 0 or correct > 3:
        return None

    return {
        "difficulty": str(item.get("difficulty", "easy")).lower(),
        "question": str(item.get("question", "")).strip(),
        "answers": answers,
        "correct": correct,
    }


# Загружает банк вопросов из основного JSON-файла.
def load_questions():
    loaded = []
    with QUESTIONS_FILE_JSON.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    if isinstance(raw, dict):
        for difficulty, questions in raw.items():
            for question in questions:
                question["difficulty"] = question.get("difficulty", difficulty)
                normalized = normalize_question(question)
                if normalized:
                    loaded.append(normalized)
    elif isinstance(raw, list):
        for question in raw:
            normalized = normalize_question(question)
            if normalized:
                loaded.append(normalized)
    return loaded


# Возвращает игровой шрифт, а если его нет — системный запасной.
def pick_font(size, bold=False):
    if FONT_FILE.exists():
        return pygame.font.Font(FONT_FILE, size)
    preferred = ["arial", "verdana", "dejavusans", "segoeui", "tahoma"]
    return pygame.font.SysFont(preferred, size, bold=bold)


# Разбивает длинную строку на несколько строк по ширине блока.
def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Button:
    # Создает текстовую кнопку для ответов, меню и модальных окон.
    def __init__(self, rect, text, font, image=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.image = image
        self.state_color = None

    # Рисует кнопку с наведением, текстом и подсветкой состояния.
    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = self.state_color or (BLUE_LIGHT if hovered else BLUE)

        if self.image:
            scaled = pygame.transform.scale(self.image, self.rect.size)
            surface.blit(scaled, self.rect)
            if self.state_color:
                overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                overlay.fill((*self.state_color, 110))
                surface.blit(overlay, self.rect)
                pygame.draw.rect(surface, self.state_color, self.rect, width=4, border_radius=8)
        else:
            pygame.draw.rect(surface, color, self.rect, border_radius=8)
            pygame.draw.rect(surface, GOLD, self.rect, width=3, border_radius=8)

        lines = wrap_text(self.text, self.font, self.rect.width - 36)
        total_height = len(lines) * self.font.get_linesize()
        y = self.rect.centery - total_height // 2
        for line in lines:
            text_surface = self.font.render(line, True, WHITE)
            text_rect = text_surface.get_rect(centerx=self.rect.centerx, y=y)
            surface.blit(text_surface, text_rect)
            y += self.font.get_linesize()


class IconButton:
    # Создает компактную верхнюю кнопку с иконкой или короткой подписью.
    def __init__(self, rect, image=None, text="", font=None, enabled=True):
        self.rect = pygame.Rect(rect)
        self.image = image
        self.text = text
        self.font = font
        self.enabled = enabled

    # Рисует иконку, состояние наведения и блокировку кнопки.
    def draw(self, surface, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        if self.image:
            image = pygame.transform.scale(self.image, self.rect.size)
            surface.blit(image, self.rect)
        else:
            pygame.draw.rect(surface, BUTTON_PANEL_DARK, self.rect, border_radius=6)
            pygame.draw.rect(surface, BUTTON_PANEL, self.rect.inflate(-8, -8), border_radius=4)
            pygame.draw.rect(surface, BUTTON_BORDER, self.rect, width=2, border_radius=6)
        if self.text and self.font:
            color = WHITE if self.enabled else (170, 168, 142)
            label = self.font.render(self.text, True, color)
            surface.blit(label, label.get_rect(center=self.rect.center))
        if not self.enabled:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 95))
            surface.blit(overlay, self.rect)
        if hovered:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 35))
            surface.blit(overlay, self.rect)


class MillionaireCatGame:
    # Готовит pygame, ассеты, шрифты, звуки и начальное состояние игры.
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=44_100, size=-16, channels=1)
        except pygame.error:
            pass

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Кот хочет стать миллионером")
        app_icon = load_image(("app_icon",), colorkey=(0, 0, 0), trim=True)
        if app_icon:
            pygame.display.set_icon(app_icon)
        self.clock = pygame.time.Clock()

        self.title_font = pick_font(48, True)
        self.big_font = pick_font(36, True)
        self.text_font = pick_font(28)
        self.button_font = pick_font(32)
        self.answer_font = pick_font(27)
        self.small_font = pick_font(22)
        self.prize_font = pick_font(17)

        self.menu_bg = load_image(("menu_bg", "main_menu", "background_menu"), (WIDTH, HEIGHT))
        self.question_bg = load_image(("question_bg", "game_bg", "background_questions"), (WIDTH, HEIGHT))
        self.button_image = load_image(("button", "answer_button", "btn"), colorkey=(0, 0, 0), trim=True)
        self.menu_icon = load_image(("menu_button", "menu_icon"), colorkey=(0, 0, 0), trim=True)
        self.power_icon = load_image(("power_button", "power_icon"), colorkey=(0, 0, 0), trim=True)
        self.sound_on_icon = load_image(("sound_on",), colorkey=(0, 0, 0), trim=True)
        self.sound_off_icon = load_image(("sound_off",), colorkey=(0, 0, 0), trim=True)
        self.fifty_icon = load_image(("fifty",), trim=True)
        self.skip_icon = load_image(("skip",), trim=True)

        idle_sheet = load_image(("cat_idle_sheet", "cat_idle", "cat"))
        jump_sheet = load_image(("cat_jump", "cat_happy", "cat_correct"))
        self.cat_frames = {
            "idle": split_sheet(idle_sheet, 4, remove_black_edges=True),
            "jump": split_sheet(jump_sheet, 4, remove_black_edges=True),
        }

        self.questions = load_questions()
        self.sounds = self.create_sounds()
        self.state = "menu"
        self.difficulty = "easy"
        self.question_pool = []
        self.current_question = None
        self.question_number = 0
        self.score = 0
        self.feedback = ""
        self.feedback_color = WHITE
        self.cat_mood = "idle"
        self.cat_animation = "idle"
        self.cat_animation_started = pygame.time.get_ticks()
        self.answer_reveal_time = 0
        self.selected_answer = None
        self.sound_enabled = True
        self.pending_menu_confirm = False
        self.fifty_fifty_used = False
        self.skip_used = False
        self.hidden_answers = set()
        self.load_saved_game()

    # Загружает игровые звуки из папки assets/sounds.
    def create_sounds(self):
        if not pygame.mixer.get_init():
            return {}
        sound_files = {
            "click": "click.mp3",
            "correct": "correct.mp3",
            "wrong": "wrong.mp3",
            "win": "win.mp3",
        }
        sounds = {}
        for name, filename in sound_files.items():
            path = SOUNDS_DIR / filename
            if path.exists():
                sounds[name] = pygame.mixer.Sound(str(path))
        if "click" in sounds:
            sounds["click"].set_volume(0.45)
        if "correct" in sounds:
            sounds["correct"].set_volume(0.55)
        if "wrong" in sounds:
            sounds["wrong"].set_volume(0.65)
        if "win" in sounds:
            sounds["win"].set_volume(0.55)
        return sounds

    # Проигрывает звук по имени, если звук включен.
    def play_sound(self, name):
        if not self.sound_enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

    # Останавливает все звуки, которые сейчас проигрываются.
    def stop_all_sounds(self):
        if pygame.mixer.get_init():
            pygame.mixer.stop()

    # Переключает текущую анимацию кота и сбрасывает таймер кадров.
    def set_cat_animation(self, name):
        self.cat_animation = name
        self.cat_animation_started = pygame.time.get_ticks()

    # Сохраняет текущую незавершенную партию в файл.
    def save_game(self):
        if self.state != "game" or not self.current_question or self.selected_answer is not None:
            return
        data = {
            "difficulty": self.difficulty,
            "question_pool": self.question_pool,
            "current_question": self.current_question,
            "question_number": self.question_number,
            "score": self.score,
            "fifty_fifty_used": self.fifty_fifty_used,
            "skip_used": self.skip_used,
            "hidden_answers": sorted(self.hidden_answers),
        }
        with SAVE_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    # Удаляет файл сохранения, когда партия завершена или сброшена.
    def clear_save(self):
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()

    # Восстанавливает незавершенную партию при запуске игры.
    def load_saved_game(self):
        if not SAVE_FILE.exists():
            return
        try:
            with SAVE_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return

        if data.get("difficulty") not in DIFFICULTIES or not data.get("current_question"):
            return

        self.difficulty = data["difficulty"]
        self.question_pool = data.get("question_pool", [])
        self.current_question = data["current_question"]
        self.question_number = int(data.get("question_number", 1))
        self.score = int(data.get("score", 0))
        self.fifty_fifty_used = bool(data.get("fifty_fifty_used", False))
        self.skip_used = bool(data.get("skip_used", False))
        self.hidden_answers = set(data.get("hidden_answers", []))
        self.feedback = ""
        self.selected_answer = None
        self.answer_reveal_time = 0
        self.cat_mood = "idle"
        self.set_cat_animation("idle")
        self.state = "game"

    # Начинает новую партию выбранной сложности.
    def start_game(self, difficulty):
        self.difficulty = difficulty
        self.question_pool = [q for q in self.questions if q["difficulty"] == difficulty]
        if not self.question_pool:
            self.question_pool = self.questions[:]
        random.shuffle(self.question_pool)
        self.question_pool = self.question_pool[:QUESTION_COUNT]
        self.question_number = 0
        self.score = 0
        self.feedback = ""
        self.cat_mood = "idle"
        self.set_cat_animation("idle")
        self.selected_answer = None
        self.fifty_fifty_used = False
        self.skip_used = False
        self.hidden_answers = set()
        self.next_question()
        self.state = "game"
        self.save_game()

    # Переключает игру на следующий вопрос или завершает партию.
    def next_question(self):
        if self.question_number >= len(DIFFICULTIES[self.difficulty]["prizes"]):
            self.finish_game(True)
            return
        if not self.question_pool:
            self.finish_game(True)
            return
        self.current_question = self.question_pool.pop()
        self.question_number += 1
        self.feedback = ""
        self.selected_answer = None
        self.answer_reveal_time = 0
        self.hidden_answers = set()
        self.save_game()

    # Показывает итоговый экран победы или поражения.
    def finish_game(self, won=False):
        self.clear_save()
        self.state = "result"
        self.cat_mood = "happy" if won else "sad"
        self.set_cat_animation("jump" if won else "idle")
        if won:
            self.play_sound("win")
            self.feedback = "Победа! Кот гордится тобой."
            self.feedback_color = WHITE
        else:
            self.feedback = "Игра окончена. Кот верит в реванш."
            self.feedback_color = RED

    # Проверяет, дошел ли игрок до последнего вопроса.
    def is_last_question(self):
        return self.question_number >= QUESTION_COUNT

    # Использует подсказку 50/50 и скрывает два неверных ответа.
    def use_fifty_fifty(self):
        if self.fifty_fifty_used or self.is_last_question() or not self.current_question:
            return
        wrong_answers = [index for index in range(4) if index != self.current_question["correct"]]
        self.hidden_answers = set(random.sample(wrong_answers, 2))
        self.fifty_fifty_used = True
        self.save_game()

    # Использует одноразовый пропуск текущего вопроса.
    def skip_question(self):
        if self.skip_used or self.is_last_question() or not self.current_question:
            return
        self.skip_used = True
        self.hidden_answers = set()
        self.next_question()

    # Рисует фон экрана или запасную заливку, если картинки нет.
    def draw_background(self, image):
        if image:
            self.screen.blit(image, (0, 0))
        else:
            self.screen.fill(BLUE_DARK)
            for y in range(0, HEIGHT, 80):
                tone = 28 + y // 18
                pygame.draw.rect(self.screen, (tone // 2, tone, tone + 45), (0, y, WIDTH, 80))

    # Рисует верхнюю панель с меню, подсказками, звуком и выходом.
    def draw_top_icons(self, show_menu=False):
        mouse = pygame.mouse.get_pos()
        buttons = {}
        if show_menu:
            buttons["menu"] = IconButton((18, 18, 64, 64), self.menu_icon)
            hints_enabled = not self.is_last_question() and self.selected_answer is None
            buttons["fifty"] = IconButton(
                (18, HEIGHT - 82, 64, 64),
                self.fifty_icon,
                enabled=hints_enabled and not self.fifty_fifty_used,
            )
            buttons["skip"] = IconButton(
                (92, HEIGHT - 82, 64, 64),
                self.skip_icon,
                enabled=hints_enabled and not self.skip_used,
            )
        buttons["sound"] = IconButton((WIDTH - 156, 18, 64, 64), self.sound_on_icon if self.sound_enabled else self.sound_off_icon)
        buttons["quit"] = IconButton((WIDTH - 82, 18, 64, 64), self.power_icon)
        for button in buttons.values():
            button.draw(self.screen, mouse)
        return buttons

    # Рисует кота с текущей анимацией.
    def draw_cat(self, x=72, y=252, scale=2.45):
        frames = self.cat_frames.get(self.cat_animation) or self.cat_frames.get("idle")
        if frames:
            elapsed = pygame.time.get_ticks() - self.cat_animation_started
            if self.cat_animation == "jump" and elapsed > 760:
                self.set_cat_animation("idle")
                frames = self.cat_frames.get("idle")
                elapsed = 0
            frame = frames[(elapsed // 190) % len(frames)]
            width = int(frame.get_width() * scale)
            height = int(frame.get_height() * scale)
            self.screen.blit(pygame.transform.scale(frame, (width, height)), (x, y))
        else:
            color = GOLD if self.cat_mood == "happy" else RED if self.cat_mood == "sad" else WHITE
            pygame.draw.circle(self.screen, color, (x + 95, y + 90), 78)
            pygame.draw.polygon(self.screen, color, [(x + 34, y + 44), (x + 60, y), (x + 82, y + 52)])
            pygame.draw.polygon(self.screen, color, [(x + 108, y + 52), (x + 135, y), (x + 158, y + 44)])
            pygame.draw.circle(self.screen, BLACK, (x + 68, y + 88), 8)
            pygame.draw.circle(self.screen, BLACK, (x + 122, y + 88), 8)
            mouth_y = y + 122 if self.cat_mood != "sad" else y + 136
            pygame.draw.arc(self.screen, BLACK, (x + 73, mouth_y - 18, 44, 32), 0, math.pi, 3)

    # Рисует главное меню и возвращает кнопки выбора сложности.
    def draw_menu(self):
        self.draw_background(self.menu_bg)
        self.draw_top_icons(show_menu=False)
        title = self.title_font.render("Кот хочет стать миллионером", True, BLACK)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2 + 150, 126)))

        mouse = pygame.mouse.get_pos()
        buttons = []
        for index, (key, data) in enumerate(DIFFICULTIES.items()):
            rect = (WIDTH // 2 - 25, 220 + index * 112, 520, 92)
            buttons.append((key, Button(rect, data["title"], self.button_font, self.button_image)))
        for _, button in buttons:
            button.draw(self.screen, mouse)

        return buttons

    # Рисует шкалу выигрыша и подсвечивает текущую ступень.
    def draw_prize_ladder(self):
        prizes = DIFFICULTIES[self.difficulty]["prizes"]
        panel = pygame.Rect(WIDTH - 212, 92, 172, 404)
        pygame.draw.rect(self.screen, BUTTON_PANEL_DARK, panel, border_radius=8)
        pygame.draw.rect(self.screen, BUTTON_PANEL, panel.inflate(-10, -10), border_radius=6)
        pygame.draw.rect(self.screen, BUTTON_BORDER, panel, 3, border_radius=8)
        title = self.small_font.render("Выигрыш", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 28)))
        for index, prize in enumerate(reversed(prizes)):
            step = len(prizes) - index
            y = panel.y + 56 + index * 22
            if step == self.question_number:
                highlight = pygame.Rect(panel.x + 10, y - 2, panel.width - 20, 21)
                pygame.draw.rect(self.screen, BUTTON_PANEL_DARK, highlight, border_radius=4)
            color = GOLD if step == self.question_number else WHITE
            line = self.prize_font.render(f"{step}. {prize:,}".replace(",", " "), True, color)
            self.screen.blit(line, (panel.x + 16, y))

    # Рисует основной игровой экран с вопросом и ответами.
    def draw_game(self):
        self.draw_background(self.question_bg)
        self.draw_top_icons(show_menu=True)
        self.draw_prize_ladder()
        self.draw_cat(80, 32, 1.65)

        difficulty_title = DIFFICULTIES[self.difficulty]["title"]
        header_text = f"{difficulty_title} | Вопрос {self.question_number} из {QUESTION_COUNT}"
        header = self.small_font.render(header_text, True, WHITE)
        header_rect = header.get_rect(center=(584, 44))
        header_panel = header_rect.inflate(28, 16)
        pygame.draw.rect(self.screen, BUTTON_PANEL_DARK, header_panel, border_radius=7)
        pygame.draw.rect(self.screen, BUTTON_PANEL, header_panel.inflate(-6, -6), border_radius=5)
        pygame.draw.rect(self.screen, BUTTON_BORDER, header_panel, 2, border_radius=7)
        self.screen.blit(header, header_rect)

        monitor = pygame.Rect(376, 92, 415, 190)
        y = monitor.y + 28
        for line in wrap_text(self.current_question["question"], self.text_font, monitor.width - 56):
            text = self.text_font.render(line, True, BLACK)
            self.screen.blit(text, text.get_rect(centerx=monitor.centerx, y=y))
            y += self.text_font.get_linesize()

        mouse = pygame.mouse.get_pos()
        buttons = []
        for index, answer in enumerate(self.current_question["answers"]):
            col = index % 2
            row = index // 2
            rect = pygame.Rect(210 + col * 400, 382 + row * 96, 370, 82)
            if index in self.hidden_answers:
                hidden_button = IconButton(rect, text="", font=self.answer_font, enabled=False)
                hidden_button.draw(self.screen, mouse)
                continue
            label = f"{'ABCD'[index]}. {answer}"
            button = Button(rect, label, self.answer_font, self.button_image)
            if self.selected_answer is not None:
                if index == self.current_question["correct"]:
                    button.state_color = GREEN
                elif index == self.selected_answer:
                    button.state_color = RED
            button.draw(self.screen, mouse)
            buttons.append((index, button))

        if self.feedback:
            feedback = self.text_font.render(self.feedback, True, self.feedback_color)
            self.screen.blit(feedback, feedback.get_rect(center=(WIDTH // 2, 364)))

        if self.pending_menu_confirm:
            self.draw_menu_confirm()

        return buttons

    # Рисует подтверждение выхода в главное меню без сохранения прогресса.
    def draw_menu_confirm(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 95))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 330, HEIGHT // 2 - 128, 660, 256)
        pygame.draw.rect(self.screen, BUTTON_PANEL_DARK, panel, border_radius=8)
        pygame.draw.rect(self.screen, BUTTON_PANEL, panel.inflate(-12, -12), border_radius=6)
        pygame.draw.rect(self.screen, BUTTON_BORDER, panel, 4, border_radius=8)

        title = self.big_font.render("Выйти в главное меню?", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + 66)))

        warning = self.text_font.render("Прогресс не сохранится", True, GOLD)
        self.screen.blit(warning, warning.get_rect(center=(panel.centerx, panel.y + 118)))

        mouse = pygame.mouse.get_pos()
        yes_button = Button((panel.x + 82, panel.y + 166, 220, 64), "Да", self.button_font, self.button_image)
        no_button = Button((panel.right - 302, panel.y + 166, 220, 64), "Нет", self.button_font, self.button_image)
        yes_button.draw(self.screen, mouse)
        no_button.draw(self.screen, mouse)
        return yes_button, no_button

    # Рисует итоговый экран после победы или поражения.
    def draw_result(self):
        self.draw_background(self.question_bg)
        self.draw_top_icons(show_menu=False)
        self.draw_cat(80, 32, 1.65)
        result_panel = pygame.Rect(WIDTH // 2 - 300, 136, 600, 226)
        pygame.draw.rect(self.screen, BUTTON_PANEL_DARK, result_panel, border_radius=8)
        pygame.draw.rect(self.screen, BUTTON_PANEL, result_panel.inflate(-12, -12), border_radius=6)
        pygame.draw.rect(self.screen, BUTTON_BORDER, result_panel, 4, border_radius=8)

        title = self.title_font.render("Результат", True, WHITE)
        score = self.big_font.render(f"Твой выигрыш: {self.score:,}".replace(",", " "), True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 184)))
        self.screen.blit(score, score.get_rect(center=(WIDTH // 2, 252)))
        message_lines = wrap_text(self.feedback, self.text_font, result_panel.width - 70)
        message_y = 300
        for line in message_lines:
            message = self.text_font.render(line, True, self.feedback_color)
            self.screen.blit(message, message.get_rect(center=(WIDTH // 2, message_y)))
            message_y += self.text_font.get_linesize()

        mouse = pygame.mouse.get_pos()
        menu_button = Button((WIDTH // 2 - 230, 404, 460, 86), "В главное меню", self.button_font, self.button_image)
        menu_button.draw(self.screen, mouse)
        return menu_button

    # Обрабатывает выбранный игроком вариант ответа.
    def choose_answer(self, answer_index):
        if self.selected_answer is not None:
            return
        self.selected_answer = answer_index
        correct = self.current_question["correct"]
        if answer_index == correct:
            prizes = DIFFICULTIES[self.difficulty]["prizes"]
            self.score = prizes[min(self.question_number - 1, len(prizes) - 1)]
            self.feedback = "Верно!"
            self.feedback_color = GREEN
            self.cat_mood = "happy"
            self.set_cat_animation("jump")
            self.play_sound("correct")
            self.answer_reveal_time = pygame.time.get_ticks() + 900
        else:
            self.feedback = f"Неверно. Правильный ответ: {'ABCD'[correct]}."
            self.feedback_color = RED
            self.cat_mood = "sad"
            self.set_cat_animation("idle")
            self.play_sound("wrong")
            self.answer_reveal_time = pygame.time.get_ticks() + 1400

    # Ждет короткую паузу после ответа и затем двигает игру дальше.
    def handle_reveal_timer(self):
        if not self.answer_reveal_time:
            return
        if pygame.time.get_ticks() < self.answer_reveal_time:
            return
        was_correct = self.selected_answer == self.current_question["correct"]
        self.answer_reveal_time = 0
        if was_correct:
            self.cat_mood = "idle"
            self.set_cat_animation("idle")
            self.next_question()
        else:
            self.finish_game(False)

    # Обрабатывает клики по верхним кнопкам управления и подсказок.
    def handle_top_icon_click(self, pos):
        if self.state == "game" and pygame.Rect(18, 18, 64, 64).collidepoint(pos):
            self.pending_menu_confirm = True
            return "consumed"
        if self.state == "game" and self.selected_answer is None and pygame.Rect(18, HEIGHT - 82, 64, 64).collidepoint(pos):
            self.use_fifty_fifty()
            return "consumed"
        if self.state == "game" and self.selected_answer is None and pygame.Rect(92, HEIGHT - 82, 64, 64).collidepoint(pos):
            self.skip_question()
            return "consumed"
        if pygame.Rect(WIDTH - 156, 18, 64, 64).collidepoint(pos):
            self.sound_enabled = not self.sound_enabled
            if self.sound_enabled:
                self.play_sound("click")
            return "consumed"
        if pygame.Rect(WIDTH - 82, 18, 64, 64).collidepoint(pos):
            return "quit"
        return None

    # Обрабатывает выбор в окне подтверждения выхода в меню.
    def handle_menu_confirm_click(self, pos):
        panel = pygame.Rect(WIDTH // 2 - 330, HEIGHT // 2 - 128, 660, 256)
        yes_rect = pygame.Rect(panel.x + 82, panel.y + 166, 220, 64)
        no_rect = pygame.Rect(panel.right - 302, panel.y + 166, 220, 64)
        if yes_rect.collidepoint(pos):
            self.stop_all_sounds()
            self.pending_menu_confirm = False
            self.state = "menu"
            self.cat_mood = "idle"
            self.set_cat_animation("idle")
            self.feedback = ""
            self.clear_save()
            return True
        if no_rect.collidepoint(pos):
            self.pending_menu_confirm = False
            return True
        return self.pending_menu_confirm

    # Запускает главный цикл игры.
    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            click_pos = None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_game()
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
                    self.play_sound("click")

            if click_pos:
                if self.pending_menu_confirm:
                    if self.handle_menu_confirm_click(click_pos):
                        click_pos = None

            if click_pos:
                icon_action = self.handle_top_icon_click(click_pos)
                if icon_action == "quit":
                    self.save_game()
                    running = False
                    click_pos = None
                elif icon_action == "consumed":
                    click_pos = None

            if self.state == "menu":
                menu_buttons = self.draw_menu()
                if click_pos:
                    for difficulty, button in menu_buttons:
                        if button.rect.collidepoint(click_pos):
                            self.start_game(difficulty)
            elif self.state == "game":
                answer_buttons = self.draw_game()
                if click_pos and self.selected_answer is None and not self.pending_menu_confirm:
                    for answer_index, button in answer_buttons:
                        if answer_index not in self.hidden_answers and button.rect.collidepoint(click_pos):
                            self.choose_answer(answer_index)
                self.handle_reveal_timer()
            else:
                menu_button = self.draw_result()
                if click_pos and menu_button.rect.collidepoint(click_pos):
                    self.stop_all_sounds()
                    self.state = "menu"
                    self.cat_mood = "idle"
                    self.feedback = ""
                    self.clear_save()

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    MillionaireCatGame().run()

