__version__ = "8.0.0"
NAME = "TenSeiAi"

# --- cross-platform console bootstrap ---------------------------------------
# Windows consoles default to a legacy code page (cp1252/cp437), so printing
# unicode (conclusions signs, arrows, emoji in answers) raises UnicodeEncodeError
# and kills the CLI. Switch stdout/stderr to UTF-8 with replacement, so the same
# engine runs identically on Windows, Linux, macOS, Termux/Android.
import sys as _sys


def _utf8_streams():
    for _name in ("stdout", "stderr"):
        _s = getattr(_sys, _name, None)
        try:
            if _s is not None and hasattr(_s, "reconfigure"):
                _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_utf8_streams()
