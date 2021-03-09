import os
os.environ['GIT_PYTHON_REFRESH']="quiet"

from .fastcmd import main_cmd

if __name__ == '__main__':
    main_cmd()
