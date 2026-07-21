import subprocess
import sys
import os

if __name__ == '__main__':
    init = subprocess.run([sys.executable, 'init_db.py'])
    if init.returncode != 0:
        print('❌ Database initialization failed!')
        sys.exit(1)

    bot = subprocess.Popen([sys.executable, 'bot.py'])
    admin = subprocess.Popen([sys.executable, 'admin_panel.py'])

    try:
        bot.wait()
        admin.wait()
    except KeyboardInterrupt:
        bot.terminate()
        admin.terminate()
