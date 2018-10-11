"""Main module of Vigilancia. This where execution begins."""
import vg_config
vg_config.init()

from core.services import DisplayScreen
import sys

if __name__ == '__main__':
    dsp = DisplayScreen.DisplayScreen(sys.argv)
    dsp.create_login()
    sys.exit(dsp.start_app())
