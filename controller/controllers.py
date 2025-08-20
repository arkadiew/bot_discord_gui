import platform
import importlib.util
import os
import sys

def load_controllers(bot):
    """Dynamically load controller modules from the 'controller/modals' directory."""
    bot.controllers = [] # Store controller names
    if platform.system() == "Emscripten" or os is None:
        bot.log_message("Dynamic module loading not supported in Pyodide")
        return

    modals_dir = "controller/modals" # Directory where controller modules are located
    bot.log_message(f"Checking for {modals_dir} directory")
    try:
        os.makedirs(modals_dir, exist_ok=True)
        bot.log_message(f"Ensured {modals_dir} directory exists")
    except Exception as e:
        bot.log_message(f"Error creating {modals_dir} directory: {str(e)}")
        return

    if not os.path.exists(modals_dir):
        bot.log_message(f"Warning: {modals_dir} directory does not exist or is inaccessible")
        return

    for filename in sorted(os.listdir(modals_dir)):

        if filename.startswith("controller_") and filename.endswith(".py"):
            module_name = filename[:-3]
            bot.log_message(f"Attempting to load {filename}")
            try:
                spec = importlib.util.spec_from_file_location(module_name, os.path.join(modals_dir, filename))
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.startswith("Controller"):
                        controller = attr(bot)
                        bot.controllers.append(attr_name)  # Store controller name
                        bot._controllers.append(controller)
                        bot.log_message(f"Successfully loaded controller: {attr_name} from {filename}")
            except Exception as e:
                bot.log_message(f"Error loading {filename}: {str(e)}")