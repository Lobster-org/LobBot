from app.modules.loader import module_loader
from app.modules.registry import register_modules

register_modules()

__all__ = ["module_loader"]