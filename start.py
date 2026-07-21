import subprocess
import sys
import os

if __name__ == '__main__':
    bot = subprocess.Popen([sys.executable, 'bot.py'])
    admin = subprocess.Popen([sys.executable, 'admin_panel.py'])
    
    try:
        bot.wait()
        admin.wait()
    except KeyboardInterrupt:
        bot.terminate()
        admin.terminate()
