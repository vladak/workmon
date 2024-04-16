"""
safe mode handling
"""

import microcontroller

# pylint: disable=import-error
import supervisor

if supervisor.runtime.safe_mode_reason == supervisor.SafeModeReason.HARD_FAULT:
    # pylint: disable=no-member
    microcontroller.reset()  # Reset and start over.

# Otherwise, do nothing. The safe mode reason will be printed in the
# console, and nothing will run.
