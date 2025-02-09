from setuptools import setup

APP = ['app.py']
DATA_FILES = [
    ('templates', ['templates/index.html']),
    ('static', ['static/styles.css']),
]

OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,
        'CFBundleName': 'Yubikey SSH Manager',
        'CFBundleDisplayName': 'Yubikey SSH Manager',
        'CFBundleIdentifier': 'com.yubikey.sshmanager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
    'includes': [
        'flask',
        'rumps',
        'paramiko',
        'cryptography',
        'requests',
        'dotenv',
        'flask_socketio',
        'eventlet',
        'flask_cors',
        'yubikey_manager',
        'ykman',
    ],
    'packages': ['rumps', 'flask', 'werkzeug', 'jinja2', 'click', 'itsdangerous'],
    'site_packages': True,
    'resources': ['templates', 'static'],
    'strip': False,
    'optimize': 0
}

setup(
    app=APP,
    name='Yubikey SSH Manager',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
