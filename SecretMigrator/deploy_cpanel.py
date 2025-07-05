"""
cPanel deployment configuration and setup script
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_cpanel_deployment():
    """
    Setup script for cPanel Python app deployment
    Creates necessary files for Python Selector and passenger_wsgi.py
    """
    # Create .htaccess file
    htaccess_content = """
AddHandler fcgid-script .fcgi
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteRule ^(.*)$ /app.fcgi/$1 [QSA,L]
"""
    
    with open('.htaccess', 'w') as f:
        f.write(htaccess_content)

    # Create passenger_wsgi.py
    passenger_content = """
import os
import sys
from pathlib import Path

# Add project directory to path
INTERP = Path.home() / "virtualenv" / "bin" / "python3"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Add project directory to path
cwd = Path(__file__).parent
sys.path.append(str(cwd))

# Import and run the application
from main import app as application
"""
    
    with open('passenger_wsgi.py', 'w') as f:
        f.write(passenger_content)

    # Create app.fcgi
    fcgi_content = """#!/home/{username}/virtualenv/bin/python3
import sys
from flup.server.fcgi import WSGIServer
from main import app

if __name__ == '__main__':
    WSGIServer(app).run()
"""
    
    with open('app.fcgi', 'w') as f:
        f.write(fcgi_content)
    
    # Make app.fcgi executable
    os.chmod('app.fcgi', 0o755)

    # Create requirements.txt if it doesn't exist
    if not os.path.exists('requirements.txt'):
        requirements = """
flask>=2.0.1
ccxt>=4.4.92,<5.0.0
pandas>=1.3.3,<2.0.0
aiosqlite>=0.17.0
python-telegram-bot>=13.7,<14.0
flup6>=1.1.1
"""
        with open('requirements.txt', 'w') as f:
            f.write(requirements)

    print("Created deployment files for cPanel hosting")
    print("\nNext steps:")
    print("1. Upload all files to your cPanel public_html directory")
    print("2. Create a Python virtual environment in cPanel")
    print("3. Install requirements: pip install -r requirements.txt")
    print("4. Set up environment variables in cPanel")
    print("5. Configure Python app in cPanel Python Selector")
    print("6. Restart the application")

if __name__ == '__main__':
    setup_cpanel_deployment() 