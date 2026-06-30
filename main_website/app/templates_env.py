"""
Shared Jinja2 templates instance.
cache_size=0 works around a Python 3.14 incompatibility with Jinja2's LRU cache.
"""

from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader, Environment

_jinja_env = Environment(
    loader=FileSystemLoader("app/templates"),
    auto_reload=True,
    cache_size=0,
)

templates = Jinja2Templates(env=_jinja_env)
