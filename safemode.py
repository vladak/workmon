"""
safe mode handling
"""
import microcontroller
import supervisor

if supervisor.runtime.safe_mode_reason == supervisor.SafeModeReason.HARD_FAULT:
    microcontroller.reset()  # Reset and start over.

# Otherwise, do nothing. The safe mode reason will be printed in the
# console, and nothing will run.
