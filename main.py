import asyncio
import platform
import pygame
import sys
import pyperclip
from pygame.locals import *
from dotenv import load_dotenv, set_key
import os
import json
from controller.bot import ControllerBot

import importlib.util
import inspect
import copy

pygame.init()
pygame.font.init()


THEME = "dark"

def get_theme_colors():
    """Return theme colors based on the current theme."""
    if THEME == "dark":
        return {
            "BG": (26, 26, 26),
            "TEXT": (255, 255, 255),
            "ACCENT_START": (0, 0, 0),
            "ACCENT_END": (50, 50, 50),
            "GRAY": (55, 55, 55),
            "YELLOW": (255, 255, 0),
            "RED": (255, 0, 0),
            "GREEN": (0, 255, 0),
        }
    else:
        return {
            "BG": (245, 245, 245),
            "TEXT": (20, 20, 20),
            "ACCENT_START": (200, 200, 200),
            "ACCENT_END": (160, 160, 160),
            "GRAY": (220, 220, 220),
            "YELLOW": (255, 215, 0),
            "RED": (200, 50, 50),
            "GREEN": (50, 200, 50),
        }

COLORS = get_theme_colors()

def toggle_theme():
    """Toggle between light and dark themes."""
    global THEME, COLORS
    THEME = "light" if THEME == "dark" else "dark"
    COLORS = get_theme_colors()

WIDTH, HEIGHT = 1000, 800
MIN_WIDTH, MIN_HEIGHT = 700, 600
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Discord Bot GUI (Auto Layout)")

def get_fonts():
    """Return the main fonts used in the application."""
    f = pygame.font.SysFont('Segoe UI', max(22, HEIGHT // 28), bold=True)
    sf = pygame.font.SysFont('Segoe UI', max(16, HEIGHT // 38))
    ic = pygame.font.SysFont('Segoe UI Symbol', max(28, HEIGHT // 24))
    return f, sf, ic

font, small_font, icon_font = get_fonts()

# Global variables
logs = []
filtered_logs = []
max_logs = 6
show_console = True
bot = None
bot_task = None
bot_running = False
settings_scroll = 0
settings_view_rect = None
console_scroll = 0
console_view_rect = None
console_content_h = 0
reset_confirm_active = False
reset_confirm_rects = {}

settings_is_dragging = False
settings_drag_offset_y = 0
settings_scroll_track_rect = None
settings_scroll_thumb_rect = None
settings_scroll_max = 0
settings_content_h = 0

def get_all_controller_classes(modals_dir=None):
    """Dynamically load all controller classes from the specified directory."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        modals_dir = os.path.join(base_path, "controller", "modals")
    else:
        modals_dir = modals_dir or os.path.join("controller", "modals")

    controller_classes = {}

    if not os.path.exists(modals_dir):
        return controller_classes

    for filename in os.listdir(modals_dir):
        if filename.startswith("controller_") and filename.endswith(".py"):
            module_path = os.path.join(modals_dir, filename)
            module_name = filename[:-3]

            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if name.startswith("Controller"):
                        controller_classes[name] = obj
            except Exception as e:
                print(f"❌ Error loading controller {filename}: {e}")

    return controller_classes

controller_classes = {

}
controller_classes.update(get_all_controller_classes())

## Defaults & settings
default_settings = {}
for name, cls in controller_classes.items():
    try:
        temp_bot = type('TempBot', (), {'log_message': lambda x: None})()
        if cls:
            try:
                controller_instance = cls(temp_bot, register_commands=False, load_settings_flag=False)
                default_settings[name] = controller_instance.settings.copy()
            except Exception as e:
                print(f"❌ Failed to init {name}: {e}")
        else:
            print(f"⚠️ Controller class for {name} is None")
    except Exception as e:
        print(f"❌ Failed to init {name}: {e}")


default_settings["ControllerBot"] = {"default_prefix": "!"}

settings = copy.deepcopy(default_settings)
if os.path.exists("settings.json"):
    try:
        with open("settings.json", "r") as f:
            loaded_settings = json.load(f)
            for controller, defaults in default_settings.items():
                controller_settings = loaded_settings.get(controller, {})
                for key, default_value in defaults.items():
                    current_value = controller_settings.get(key)
                    settings[controller][key] = current_value if current_value not in ["", None] else default_value
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
if "ControllerBot" not in settings:
    settings["ControllerBot"] = {"default_prefix": "!"}
elif "default_prefix" not in settings["ControllerBot"]:
    settings["ControllerBot"]["default_prefix"] = "!"

if not os.path.exists("settings.json"):
    with open("settings.json", "w") as f:
        json.dump(settings, f, indent=4)
        print("✅ settings.json created with default values.")

state = {
    "token_text": "",
    "search_text": "",
    "active_token": False,
    "active_search": False,
    "active_tab": None,
    "hover_times": {},
    "active_input": None
}
# UI elements
start_button = None
pause_button = None
toggle_button = None
token_box = None
search_box = None
tab_buttons = []
setting_elements = []
reset_button = None

def sanitize_text(text):
    """Sanitize text by removing null characters and trimming whitespace."""
    return str(text).replace('\\x00', '').strip()

def log_message(message):
    """Log a message to the console and store it in the logs."""
    global filtered_logs
    sanitized = message.replace(state["token_text"], "[HIDDEN]") if state["token_text"] else message
    logs.append(sanitized[:100])
    if len(logs) > max_logs:
        logs.pop(0)
    update_filtered_logs()

def update_filtered_logs():
    """Update the filtered logs based on the current search text."""
    global filtered_logs
    if state["search_text"]:
        filtered_logs = [log for log in logs if state["search_text"].lower() in log.lower()]
    else:
        filtered_logs = logs

def load_token():
    """Load the Discord token from the .env file."""
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "")
    if token:
        log_message("✅ Token loaded from .env")
    else:
        log_message("⚠️ No token found in .env")
    return token

def save_token(token):
    """Save the Discord token to the .env file."""
    try:
        set_key(".env", "DISCORD_TOKEN", token)
        log_message("💾 Token saved to .env")
    except Exception as e:
        log_message(f"❌ Failed to save token: {str(e)}")

def save_settings():
    """Save the current settings to the settings.json file."""
    try:
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)
        log_message("Settings saved to settings.json")
    except Exception as e:
        log_message(f"Error saving settings: {str(e)}")

def reset_settings(controller_name=None):
    global settings

    if controller_name is None:
        return 

    if controller_name in default_settings:
        settings[controller_name] = copy.deepcopy(default_settings[controller_name])
        save_settings()
        log_message(f"🔄 {controller_name} reset to defaults")

        if bot_running and bot:
            if controller_name == "ControllerBot":
                bot.settings = copy.deepcopy(default_settings["ControllerBot"])
            else:
                controller = next((c for c in bot._controllers if type(c).__name__ == controller_name), None)
                if controller:
                    controller.settings = copy.deepcopy(default_settings[controller_name])
                    controller.save_settings()


    if bot_running and bot:

        bot.load_settings()
        for controller in bot._controllers:
            controller.load_settings()



def draw_gradient_background():
    """Draw a gradient background."""
    for y in range(HEIGHT):
        shade = 26 + y * 10 // max(1, HEIGHT)
        pygame.draw.line(screen, (shade, shade, shade), (0, y), (WIDTH, y))

def draw_panel_mica(rect):
    """Draw a Mica-like panel with a gradient effect."""
    mica_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    base_color = (32, 32, 37, 180)
    mica_surface.fill(base_color)
    for y in range(rect.height):
        shade = int(10 * (y / rect.height))
        pygame.draw.line(mica_surface, (shade, shade, shade, 40), (0, y), (rect.width, y))
    pygame.draw.rect(mica_surface, (255, 255, 255, 25), (0, 0, rect.width, rect.height // 6))
    screen.blit(mica_surface, rect.topleft)
    pygame.draw.rect(screen, COLORS["TEXT"], rect, 2, border_radius=18)

def draw_text_input(rect, text, active, mask=False):
    """Draw a text input field with a border and background."""
    if not rect:
        return
    pygame.draw.rect(screen, (40, 40, 40), rect.inflate(5, 5), border_radius=18)
    pygame.draw.rect(screen, COLORS["GRAY"] if not active else COLORS["ACCENT_START"], rect, border_radius=18)
    pygame.draw.rect(screen, COLORS["TEXT"] if not active else COLORS["ACCENT_END"], rect, 2, border_radius=18)
    display_text = sanitize_text(text)
    if mask and not active:
        display_text = "*" * len(display_text)
    available_width = rect.width - 20
    while font.size(display_text)[0] > available_width and len(display_text) > 0:
        display_text = display_text[:-1]
    display_text = display_text[:100]
    clipped_surface = font.render(display_text, True, COLORS["TEXT"])
    text_rect = clipped_surface.get_rect(midleft=(rect.x + 10, rect.centery))
    screen.blit(clipped_surface, text_rect)

def draw_checkbox(rect, checked, label):
    """Draw a checkbox with a label."""
    pygame.draw.rect(screen, (30, 30, 30), rect, border_radius=6)
    pygame.draw.rect(screen, COLORS["ACCENT_START"], rect, 2, border_radius=6)
    if checked:
        check = icon_font.render('✔', True, COLORS["GREEN"])
        check_rect = check.get_rect(center=rect.center)
        screen.blit(check, check_rect)
    label_surface = small_font.render(label, True, COLORS["TEXT"])
    screen.blit(label_surface, (rect.x + rect.width + 10, rect.y + 5))


def draw_logs(log_area, scroll=0):
    """Draw the logs in the specified area with scrolling support."""
    global console_view_rect, console_content_h

    draw_panel_mica(log_area)
    pygame.draw.rect(screen, COLORS["TEXT"], log_area, 2, border_radius=18)
    console_view_rect = log_area.copy()
    clip = screen.get_clip()
    screen.set_clip(log_area.inflate(-10, -10))

    max_width = log_area.width - 30
    base_x = log_area.x + 10
    y = log_area.y + 10 - scroll
    line_h = small_font.get_height() + 6

    total_h = 10
    for log in filtered_logs:
        words = log.split(' ')
        line = ''
        while words:
            if small_font.size(line + words[0] + ' ')[0] < max_width:
                line += words.pop(0) + ' '
                if not words:
                    surface = small_font.render(line, True, COLORS["TEXT"])
                    screen.blit(surface, (base_x, y))
                    y += line_h
                    total_h += line_h
            else:
                surface = small_font.render(line, True, COLORS["TEXT"])
                screen.blit(surface, (base_x, y))
                y += line_h
                total_h += line_h
                line = ''

    screen.set_clip(clip)

    console_content_h = max(total_h + 10, log_area.height)

    view_h = log_area.height - 10
    content_h = console_content_h
    if content_h > view_h:
        track = pygame.Rect(log_area.right - 14, log_area.y + 6, 8, log_area.height - 12)
        pygame.draw.rect(screen, (180, 180, 180), track, border_radius=8)
        ratio = view_h / content_h
        thumb_h = max(24, int(track.height * ratio))
        max_scroll = content_h - view_h
        thumb_y = track.y + int((scroll / max(1, max_scroll)) * (track.height - thumb_h))
        thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)

        s = pygame.Surface((thumb.width, thumb.height), pygame.SRCALPHA)
        s.fill((255, 255, 255, 120))
        screen.blit(s, thumb.topleft)
        pygame.draw.rect(screen, (255, 255, 255), thumb, 1, border_radius=8)

    return console_content_h

def compute_tabs(controllers, container_rect, vgap=8, hgap=10, padding_x=10, row_height=40):
    """Compute the positions and sizes of tabs based on the available space."""
    items = []
    x = container_rect.x + padding_x
    y = container_rect.y + vgap
    max_x = container_rect.right - padding_x
    current_row_height = row_height

    for name in controllers:
        label = name.replace("Controller", "")
        text_w = small_font.size(label)[0]
        w = max(100, text_w + 24)
        if x + w > max_x:
            x = container_rect.x + padding_x
            y += current_row_height + vgap
        rect = pygame.Rect(x, y, w, row_height)
        items.append((rect, name))
        x = rect.right + hgap

    tabs_bottom = (items[-1][0].bottom if items else container_rect.y) + vgap
    return items, tabs_bottom

def draw_settings_panel(panel, active_tab, scroll=0):
    """Draw the settings panel for the active controller tab with scrolling support."""
    global setting_elements, reset_button, settings_view_rect
    setting_elements.clear()

    draw_panel_mica(panel)
    pygame.draw.rect(screen, COLORS["TEXT"], panel, 2, border_radius=18)

    settings_view_rect = panel.copy()

    if not active_tab:
        text = small_font.render("Select the controller tab to see the settings", True, COLORS["TEXT"])
        screen.blit(text, (panel.x + 20, panel.y + 20))
        reset_button = None
        return 0

    content_w = panel.width - 20
    y = 10

    elements = []
    title = f"{active_tab} Settings"
    title_surf = small_font.render(title, True, COLORS["TEXT"])
    title_h = title_surf.get_height()
    y += title_h + 10

    current_settings = settings.get(active_tab, {})

    for key, value in current_settings.items():
        if isinstance(value, bool):
            rect = pygame.Rect(10, y, 30, 30)
            elements.append(("checkbox", rect, key, active_tab, key.replace("_", " ").capitalize()))
            y += 40
        else:
            rect = pygame.Rect(10, y, content_w - 20, 40)
            elements.append(("input", rect, key, active_tab, None))
            y += 50

    reset_rect = pygame.Rect(panel.x + panel.width - 150, panel.y + 10, 120, 40)
    pygame.draw.rect(screen, COLORS["RED"], reset_rect, border_radius=18)
    pygame.draw.rect(screen, COLORS["TEXT"], reset_rect, 1, border_radius=18)
    reset_text = small_font.render("Reset", True, COLORS["TEXT"])
    screen.blit(reset_text, (reset_rect.x + 10, reset_rect.y + 10))

    reset_button = reset_rect

    content_height = y + 10

    clip = screen.get_clip()
    screen.set_clip(settings_view_rect.inflate(-10, -10))
    screen.blit(title_surf, (panel.x + 20, panel.y + 10 - scroll))

    for kind, r, key, controller, extra in elements:
        sr = r.move(panel.x + 10, panel.y + 10 - scroll)
        if kind == "checkbox":
            draw_checkbox(sr, settings[controller].get(key, False), extra or key)
            label_w = small_font.size(extra or key)[0]
            hit_rect = pygame.Rect(sr.x, sr.y, sr.width + 10 + label_w, sr.height)
            setting_elements.append((hit_rect, key, controller))
        elif kind == "input":
            draw_text_input(sr, str(settings[controller].get(key, "")), state["active_input"] == key)
            setting_elements.append((sr, key, controller))
        elif kind == "input_num":
            draw_text_input(sr, str(settings[controller].get(key, "")), state["active_input"] == key)
            unit = small_font.render(extra or "", True, COLORS["TEXT"])
            screen.blit(unit, (sr.right + 10, sr.y + 10))
            setting_elements.append((sr, key, controller))

    screen.set_clip(clip)

    view_h = panel.height - 20
    global settings_scroll_track_rect, settings_scroll_thumb_rect, settings_scroll_max, settings_content_h
    settings_content_h = content_height

    max_scroll = max(0, content_height - view_h)
    settings_scroll_max = max_scroll
    scroll_clamped = max(0, min(scroll, max_scroll))

    if scroll_clamped != scroll:
        scroll = scroll_clamped
        settings_scroll = scroll_clamped

    settings_scroll_track_rect = None
    settings_scroll_thumb_rect = None

    if content_height > view_h:

        bg_strip = pygame.Rect(panel.right - 18, panel.y + 6, 14, panel.height - 12)
        pygame.draw.rect(screen, (20, 20, 20), bg_strip, border_radius=8)

        track = pygame.Rect(panel.right - 14, panel.y + 8, 8, panel.height - 16)
        pygame.draw.rect(screen, (200, 200, 200), track, border_radius=8)

        ratio = view_h / float(content_height)
        thumb_h = max(28, int(track.height * ratio))
        travel = track.height - thumb_h
        thumb_y = track.y + (0 if max_scroll == 0 else int(scroll * travel / max_scroll))
        thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)

        pygame.draw.rect(screen, (245, 245, 245), thumb, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), thumb, 2, border_radius=8)

        settings_scroll_track_rect = track
        settings_scroll_thumb_rect = thumb

    return content_height

def draw_reset_modal(text="Reset this controller's settings?"):
    """Draw a modal dialog for confirming reset of controller settings."""
    global reset_confirm_rects
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140)) 
    screen.blit(overlay, (0, 0))

    dlg_w, dlg_h = 380, 170
    dlg_rect = pygame.Rect((WIDTH - dlg_w)//2, (HEIGHT - dlg_h)//2, dlg_w, dlg_h)

    pygame.draw.rect(screen, COLORS["BG"], dlg_rect, border_radius=18)
    pygame.draw.rect(screen, COLORS["TEXT"], dlg_rect, 2, border_radius=18)

    title = small_font.render(text, True, COLORS["TEXT"])
    screen.blit(title, (dlg_rect.centerx - title.get_width()//2, dlg_rect.y + 18))

    btn_w, btn_h = 120, 44
    yes_rect = pygame.Rect(dlg_rect.x + 28, dlg_rect.bottom - btn_h - 20, btn_w, btn_h)
    no_rect  = pygame.Rect(dlg_rect.right - btn_w - 28, dlg_rect.bottom - btn_h - 20, btn_w, btn_h)

    pygame.draw.rect(screen, COLORS["GREEN"], yes_rect, border_radius=12)
    pygame.draw.rect(screen, COLORS["RED"],   no_rect,  border_radius=12)

    yes_text = small_font.render("Yes", True, COLORS["BG"])
    no_text  = small_font.render("No", True, COLORS["BG"])
    screen.blit(yes_text, (yes_rect.centerx - yes_text.get_width()//2, yes_rect.centery - yes_text.get_height()//2))
    screen.blit(no_text,  (no_rect.centerx  -  no_text.get_width()//2,  no_rect.centery -  no_text.get_height()//2))

    reset_confirm_rects["yes"] = yes_rect
    reset_confirm_rects["no"]  = no_rect

def toggle_console():
    """Toggle the visibility of the console."""
    global show_console
    show_console = not show_console

def setup():
    """Initial setup for the application."""
    state["token_text"] = load_token()
    update_filtered_logs()
    log_message("App started. Enter a valid Discord token and click ▶ to run the bot.")

async def update_loop():
    """Main update loop for the application."""
    global bot, bot_task, bot_running, WIDTH, HEIGHT
    global start_button, pause_button, toggle_button, token_box, search_box, tab_buttons, reset_button, settings_scroll, settings_view_rect
    global screen, font, small_font, icon_font
    global console_scroll, console_view_rect, console_content_h
    global settings_is_dragging, settings_drag_offset_y, settings_scroll_track_rect, settings_scroll_thumb_rect, settings_scroll_max, settings_content_h
    global reset_confirm_active
    mouse_x, mouse_y = pygame.mouse.get_pos()
    hover_start_time = state["hover_times"]
    now = pygame.time.get_ticks()

    def show_tooltip(button_rect, text):
        key = id(button_rect)
        if button_rect.collidepoint(mouse_x, mouse_y):
            if key not in hover_start_time:
                hover_start_time[key] = now
            if now - hover_start_time[key] > 500:
                tooltip_surface = small_font.render(text, True, (255, 255, 255))
                tooltip_bg = pygame.Surface((tooltip_surface.get_width() + 10, tooltip_surface.get_height() + 6), pygame.SRCALPHA)
                tooltip_bg.fill((0, 0, 0, 180))
                tooltip_bg.blit(tooltip_surface, (5, 3))
                screen.blit(tooltip_bg, (button_rect.right + 10, button_rect.centery - tooltip_surface.get_height() // 2))
        else:
            hover_start_time.pop(key, None)

    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if reset_confirm_active:
            if event.type == MOUSEBUTTONDOWN:
                if "yes" in reset_confirm_rects and reset_confirm_rects["yes"].collidepoint(event.pos):
                    reset_settings(state["active_tab"])
                    reset_confirm_active = False
                elif "no" in reset_confirm_rects and reset_confirm_rects["no"].collidepoint(event.pos):
                    reset_confirm_active = False
                continue

            if event.type == KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    reset_confirm_active = False
                    continue
                if event.key in (pygame.K_RETURN, pygame.K_y):
                    reset_settings(state["active_tab"])
                    reset_confirm_active = False
                    continue
            continue
        elif event.type == VIDEORESIZE:
            WIDTH, HEIGHT = max(event.w, MIN_WIDTH), max(event.h, MIN_HEIGHT)
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            font, small_font, icon_font = get_fonts()
        elif event.type == MOUSEWHEEL:
            if settings_view_rect and settings_view_rect.collidepoint(mouse_x, mouse_y):
                settings_scroll -= event.y * 30
                if settings_scroll_max:
                    settings_scroll = max(0, min(settings_scroll, settings_scroll_max))
                else:
                    settings_scroll = max(0, settings_scroll)
            elif console_view_rect and console_view_rect.collidepoint(mouse_x, mouse_y):
                console_scroll -= event.y * 30
                view_h = (console_view_rect.height - 10) if console_view_rect else 0
                max_scroll = max(0, console_content_h - view_h)
                console_scroll = max(0, min(console_scroll, max_scroll))
        elif event.type == MOUSEBUTTONDOWN:
            if toggle_button and toggle_button.collidepoint(event.pos):
                toggle_console()
            elif token_box and token_box.collidepoint(event.pos):
                state["active_token"] = True
                state["active_search"] = False
                state["active_input"] = None
            elif search_box and search_box.collidepoint(event.pos):
                state["active_token"] = False
                state["active_search"] = True
                state["active_input"] = None
            elif start_button and start_button.collidepoint(event.pos) and state["token_text"] and not bot_running:
                log_message("Starting bot...")
                try:
                    bot = ControllerBot(state["token_text"], log_message)
                    bot_task = asyncio.create_task(bot.start(state["token_text"]))
                    bot_running = True
                    save_token(state["token_text"])
                    log_message(f"Bot started. Loaded controllers: {bot.controllers}")
                    state["active_tab"] = bot.controllers[0] if bot.controllers else None
                except Exception as e:
                    log_message(f"Error starting bot: {str(e)}")
            elif pause_button and pause_button.collidepoint(event.pos) and bot_running:
                log_message("Stopping bot...")
                try:
                    if bot:
                        await bot.close()
                        bot_task.cancel()
                        bot_running = False
                        log_message("Bot stopped.")
                        state["active_tab"] = None
                except Exception as e:
                    log_message(f"Error stopping bot: {str(e)}")
            else:
                for tab_rect, tab_name in tab_buttons:
                    if tab_rect.collidepoint(event.pos):
                        state["active_tab"] = tab_name if state["active_tab"] != tab_name else None
                        state["active_input"] = None

                for element_rect, setting_key, target in setting_elements:
                    if element_rect.collidepoint(event.pos):
                        if setting_key in ["enabled", "ban_enabled", "kick_enabled", "mute_enabled"]:
                            settings[target][setting_key] = not settings[target][setting_key]
                            save_settings()
            
                            if bot_running and bot:
                                controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                                if controller:
                                    controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                    controller.save_settings()
                                elif target == "ControllerBot":
                                    bot.settings[state["active_input"]] = settings[target][state["active_input"]]


                            log_message(f"Updated {setting_key} to {settings[target][setting_key]}")
                        else:
                            state["active_input"] = setting_key
                            state["active_token"] = False
                            state["active_search"] = False

                if reset_button and reset_button.collidepoint(event.pos):
                    reset_confirm_active = True
                    state["active_input"] = None
                if settings_scroll_thumb_rect and settings_scroll_thumb_rect.collidepoint(event.pos):
                    settings_is_dragging = True
                    settings_drag_offset_y = event.pos[1] - settings_scroll_thumb_rect.y
                elif settings_scroll_track_rect and settings_scroll_track_rect.collidepoint(event.pos):
                    view_h = (settings_view_rect.height - 20) if settings_view_rect else 0
                    if settings_scroll_thumb_rect and event.pos[1] < settings_scroll_thumb_rect.y:
                        settings_scroll = max(0, settings_scroll - view_h)
                    elif settings_scroll_thumb_rect and event.pos[1] > settings_scroll_thumb_rect.bottom:
                        settings_scroll = min(settings_scroll_max, settings_scroll + view_h)

        elif event.type == MOUSEMOTION:
            if settings_is_dragging and settings_scroll_track_rect and settings_scroll_thumb_rect:
                track = settings_scroll_track_rect
                thumb = settings_scroll_thumb_rect
                new_thumb_y = event.pos[1] - settings_drag_offset_y
                new_thumb_y = max(track.y, min(new_thumb_y, track.y + track.height - thumb.height))
                if track.height - thumb.height > 0:
                    p = (new_thumb_y - track.y) / (track.height - thumb.height)
                else:
                    p = 0.0
                settings_scroll = int(p * settings_scroll_max)

        elif event.type == MOUSEBUTTONUP:
            settings_is_dragging = False

        elif event.type == KEYDOWN:
            if (event.key == K_v and (event.mod & KMOD_CTRL or event.mod & KMOD_META)):
                pasted_text = pyperclip.paste()
                if state["active_token"]:
                    state["token_text"] += sanitize_text(pasted_text)
                elif state["active_search"]:
                    state["search_text"] += sanitize_text(pasted_text)
                    update_filtered_logs()
                elif state["active_input"]:
                    target = next((t for r, k, t in setting_elements if k == state["active_input"]), None)
                    if target:

                        if state["active_input"] == "default_mute_duration":
                            try:
                                settings[target][state["active_input"]] = int(pasted_text)
                                save_settings()
                                if bot_running and bot:
                                    controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                                    if controller:
                                        controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                        controller.save_settings()
                                    elif target == "ControllerBot":
                                        bot.settings[state["active_input"]] = settings[target][state["active_input"]]
                                        log_message(f"🔄 Prefix applied: {bot.settings[state['active_input']]}")


                            except ValueError:
                                log_message("Invalid number for mute duration")
                        else:
                            settings[target][state["active_input"]] = sanitize_text(pasted_text)
                            save_settings()
                            if bot_running and bot:
                                controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                                if controller:
                                    controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                    controller.save_settings()
            elif state["active_token"]:
                if event.key == K_BACKSPACE:
                    state["token_text"] = state["token_text"][:-1]
                elif event.unicode.isprintable():
                    state["token_text"] += event.unicode
                    state["token_text"] = sanitize_text(state["token_text"])
            elif state["active_search"]:
                if event.key == K_BACKSPACE:
                    state["search_text"] = state["search_text"][:-1]
                    update_filtered_logs()
                elif event.unicode.isprintable():
                    state["search_text"] += event.unicode
                    state["search_text"] = sanitize_text(state["search_text"])
                    update_filtered_logs()
            elif state["active_input"]:
                target = next((t for r, k, t in setting_elements if k == state["active_input"]), None)
                if target:
                    current_value = str(settings[target].get(state["active_input"], ""))
                    if event.key == K_BACKSPACE:
                        settings[target][state["active_input"]] = current_value[:-1] if current_value else ""
                        save_settings()
                        if bot_running and bot:
                            controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                            if controller:
                                controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                controller.save_settings()
                    elif event.unicode.isprintable():
                        if state["active_input"] == "default_mute_duration":
                            if event.unicode.isdigit():
                                current_value = str(settings[target].get(state["active_input"], ""))
                                try:
                                    settings[target][state["active_input"]] = int(current_value + event.unicode)
                                    save_settings()
                                    if bot_running and bot:
                                        controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                                        if controller:
                                            controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                            controller.save_settings()
                                except ValueError:
                                    log_message("Invalid input for mute duration")
                            else:
                                log_message("Mute duration accepts only digits")
                        else:
                            settings[target][state["active_input"]] = current_value + event.unicode
                            save_settings()
                            if bot_running and bot:
                                controller = next((c for c in bot._controllers if type(c).__name__ == target), None)
                                if controller:
                                    controller.settings[state["active_input"]] = settings[target][state["active_input"]]
                                    controller.save_settings()

            if console_view_rect and console_view_rect.collidepoint(mouse_x, mouse_y):
                if event.key == pygame.K_PAGEUP:
                    console_scroll = max(0, console_scroll - (console_view_rect.height - 40))
                elif event.key == pygame.K_PAGEDOWN:
                    view_h = console_view_rect.height - 10
                    max_scroll = max(0, console_content_h - view_h)
                    console_scroll = min(max_scroll, console_scroll + (console_view_rect.height - 40))
                elif event.key == pygame.K_HOME:
                    console_scroll = 0
                elif event.key == pygame.K_END:
                    view_h = console_view_rect.height - 10
                    console_scroll = max(0, console_content_h - view_h)

    draw_gradient_background()
    margin = max(10, int(min(WIDTH, HEIGHT) * 0.02))
    inner_w = WIDTH - 2 * margin

    panel_h = max(140, int(HEIGHT * 0.18))
    panel = pygame.Rect(margin, margin, inner_w, panel_h)
    draw_panel_mica(panel)

    row_gap = 10
    input_h = 46
    left_w = max(300, int(inner_w * 0.7))
    token_box = pygame.Rect(panel.x + 20, panel.y + 20, left_w, input_h)
    search_box = pygame.Rect(panel.x + 20, token_box.bottom + row_gap, left_w, input_h)

    btn_w = max(48, int(WIDTH * 0.06))
    btn_h = max(42, int(HEIGHT * 0.06))
    col_x = panel.right - (btn_w + 20)
    start_button = pygame.Rect(col_x, panel.y + 18, btn_w, btn_h)
    pause_button = pygame.Rect(col_x, start_button.bottom + row_gap, btn_w, btn_h)

    toggle_button = pygame.Rect(col_x - (btn_w + 12), panel.y + (panel_h - (btn_h * 2 + row_gap)) // 2, btn_w, btn_h * 2 + row_gap)

    draw_text_input(token_box, state["token_text"], state["active_token"], mask=True)
    draw_text_input(search_box, state["search_text"], state["active_search"])

    pygame.draw.rect(screen, COLORS["GREEN"] if not bot_running else COLORS["GRAY"], start_button, border_radius=18)
    play_icon = icon_font.render("▶", True, COLORS["BG"])
    screen.blit(play_icon, play_icon.get_rect(center=start_button.center))

    pygame.draw.rect(screen, COLORS["RED"] if bot_running else COLORS["GRAY"], pause_button, border_radius=18)
    pause_icon = icon_font.render("⏸", True, COLORS["BG"])
    screen.blit(pause_icon, pause_icon.get_rect(center=pause_button.center))

    pygame.draw.rect(screen, COLORS["ACCENT_END"], toggle_button, border_radius=18)
    icon = "🗖" if show_console else "🗕"
    toggle_icon = icon_font.render(icon, True, COLORS["BG"])
    screen.blit(toggle_icon, toggle_icon.get_rect(center=toggle_button.center))

    tabs_container = pygame.Rect(margin, panel.bottom + margin // 2, inner_w, 9999)
    tab_buttons.clear()
    controllers = (
    (bot.controllers if bot_running and bot and hasattr(bot, 'controllers') else list(controller_classes.keys()))
    + ["ControllerBot"]
    )

    tab_buttons, tabs_bottom = compute_tabs(controllers, tabs_container)
    for rect, controller in tab_buttons:
        color = COLORS["ACCENT_START"] if state["active_tab"] == controller else COLORS["GRAY"]
        pygame.draw.rect(screen, color, rect, border_radius=18)
        pygame.draw.rect(screen, COLORS["TEXT"], rect, 1, border_radius=18)
        tab_text = small_font.render(controller.replace("Controller", ""), True, COLORS["TEXT"])
        screen.blit(tab_text, (rect.x + 10, rect.y + (rect.height - tab_text.get_height()) // 2))

    spacing = margin // 2
    available_h_below_tabs = HEIGHT - tabs_bottom - spacing - margin
    console_h = 0
    if show_console:
        console_h = max(140, int(available_h_below_tabs * 0.28))
    settings_h = available_h_below_tabs - console_h - (spacing if show_console else 0)
    settings_h = max(140, settings_h)

    settings_panel = pygame.Rect(margin, tabs_bottom + spacing, inner_w, settings_h)
    if settings_scroll_max:
        settings_scroll = max(0, min(settings_scroll, settings_scroll_max))
    content_h = draw_settings_panel(settings_panel, state["active_tab"], scroll=settings_scroll)
    max_scroll_settings = max(0, content_h - settings_panel.height + 20)
    if settings_scroll > max_scroll_settings:
        settings_scroll = max_scroll_settings

    if show_console:
        log_area = pygame.Rect(margin, settings_panel.bottom + spacing, inner_w, console_h)
        console_content_h = draw_logs(log_area, scroll=console_scroll)

        view_h = log_area.height - 10
        max_scroll_console = max(0, console_content_h - view_h)
        if console_scroll > max_scroll_console:
            console_scroll = max_scroll_console

    if reset_confirm_active:
        draw_reset_modal()
    pygame.display.flip()

async def main():
    """Main entry point for the application."""
    global WIDTH, HEIGHT, screen, font, small_font, icon_font
    setup()
    while True:
        WIDTH, HEIGHT = pygame.display.get_surface().get_size()
        WIDTH = max(WIDTH, MIN_WIDTH)
        HEIGHT = max(HEIGHT, MIN_HEIGHT)
        await update_loop()
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
    """Main entry point for the application."""
fade_alpha = 255
