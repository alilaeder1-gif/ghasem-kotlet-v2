import subprocess
import sys
import os
import time

if __name__ == '__main__':
    try:
        init = subprocess.run([sys.executable, 'init_db.py'], capture_output=True, text=True, timeout=30)
        print(init.stdout)
        if init.stderr:
            print(f'init_db stderr: {init.stderr}')
    except Exception as e:
        print(f'Warning: init_db.py failed: {e}')
        print('Continuing anyway...')

    time.sleep(1)

    bot = subprocess.Popen([sys.executable, 'bot.py'])
    admin = subprocess.Popen([sys.executable, 'admin_panel.py'])

    print('Bot and Admin Panel started!')

    try:
        bot.wait()
        admin.wait()
    except KeyboardInterrupt:
        bot.terminate()
        admin.terminate()
