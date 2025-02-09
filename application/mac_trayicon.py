import rumps
import webbrowser
import json
from .ssh_manager import SSHManager
from .logger import setup_logger

logger, yubikey_logger = setup_logger()

class TrayApplication(rumps.App):
    """macOS tray application"""
    def __init__(self, quit_callback=None):
        super().__init__("YubiKey SSH Manager", "🔐")
        self.ssh_manager = SSHManager()  # Create a new instance
        
        # Create Connect menu with initial submenu
        connect_menu = rumps.MenuItem("Connect")
        for item in self.create_server_submenu():
            connect_menu.add(item)
            
        # Create YubiKey menu with initial submenu
        yubikey_menu = rumps.MenuItem("YubiKey")
        for item in self.create_yubikey_submenu():
            yubikey_menu.add(item)
        
        # Set up the menu structure
        self.menu = [
            rumps.MenuItem("Open Web Interface", callback=self.open_web),
            None,  # Add a separator
            yubikey_menu,
            connect_menu,
            None,  # Add another separator
            # rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Start timers to update menus periodically
        self.server_timer = rumps.Timer(self.update_server_menu, 5)
        self.server_timer.start()
        self.yubikey_timer = rumps.Timer(self.update_yubikey_menu, 2)
        self.yubikey_timer.start()
        
        self.quit_callback = quit_callback

    def create_server_submenu(self):
        """Create a submenu with the list of configured servers"""
        submenu = []
        servers = self.ssh_manager.get_servers()
        
        if not servers:
            no_servers = rumps.MenuItem("No servers configured")
            no_servers.state = -1  # This makes the item disabled
            submenu.append(no_servers)
        else:
            for server in servers:
                server_name = f"{server['name']} ({server['username']}@{server['hostname']})"
                menu_item = rumps.MenuItem(
                    server_name, 
                    callback=lambda x, s=server: self.connect_to_server(s['id'])
                )
                submenu.append(menu_item)
        
        return submenu

    def create_yubikey_submenu(self):
        """Create a submenu with the list of available YubiKeys"""
        submenu = []
        try:
            yubikeys = self.ssh_manager.get_yubikeys()
            
            # Read selected YubiKey directly from file
            try:
                with open(self.ssh_manager.selected_yubikey_file, 'r') as f:
                    selected_data = json.loads(f.read() or '{}')
                    selected = selected_data.get('serial')
            except Exception as e:
                logger.error(f"Error reading selected YubiKey: {str(e)}")
                selected = None
            
            if not yubikeys:
                no_yubikeys = rumps.MenuItem("No YubiKeys detected")
                no_yubikeys.state = -1  # This makes the item disabled
                submenu.append(no_yubikeys)
            else:
                # Create a separate function for each menu item to avoid closure issues
                def make_callback(serial):
                    return lambda _: self.select_yubikey(serial)
                
                for yk in yubikeys:
                    title = f"YubiKey {yk['serial']} (v{yk['version']})"
                    if yk['serial'] == selected:
                        title = "✓ " + title
                    menu_item = rumps.MenuItem(
                        title,
                        callback=make_callback(yk['serial'])
                    )
                    submenu.append(menu_item)
        except Exception as e:
            logger.error(f"Error creating YubiKey submenu: {str(e)}")
            error_item = rumps.MenuItem("Error loading YubiKeys")
            error_item.state = -1
            submenu.append(error_item)
        
        return submenu

    def update_server_menu(self, _):
        """Update the server submenu periodically"""
        try:
            # Find the Connect menu
            connect_menu = None
            for item in self.menu:
                if isinstance(item, rumps.MenuItem) and item.title == "Connect":
                    connect_menu = item
                    break
            
            if connect_menu is None:
                return
            
            # Get new items
            new_items = self.create_server_submenu()
            
            # Update the menu items
            connect_menu.clear()
            for item in new_items:
                connect_menu.add(item)
                
        except Exception as e:
            logger.error(f"Error updating server menu: {str(e)}")

    def update_yubikey_menu(self, _):
        """Update the YubiKey submenu periodically"""
        try:
            # Find the YubiKey menu
            yubikey_menu = None
            for item in self.menu:
                if isinstance(item, rumps.MenuItem) and item.title == "YubiKey":
                    yubikey_menu = item
                    break
            
            if yubikey_menu is None:
                return
            
            # Get new items
            new_items = self.create_yubikey_submenu()
            
            # Completely recreate the menu
            yubikey_menu.clear()
            for item in new_items:
                yubikey_menu.add(item)
                
        except Exception as e:
            logger.error(f"Error updating YubiKey menu: {str(e)}")

    def connect_to_server(self, server_id):
        """Handle server connection from menu"""
        result = self.ssh_manager.connect_to_server(server_id)
        if not result['success']:
            rumps.notification(
                title='Connection Failed',
                subtitle='',
                message=result['message']
            )

    def select_yubikey(self, serial):
        """Handle YubiKey selection from menu"""
        try:
            if self.ssh_manager.select_yubikey(serial):
                # Force an immediate menu update
                self.update_yubikey_menu(None)
                rumps.notification(
                    title='YubiKey Selected',
                    subtitle='',
                    message=f'YubiKey {serial} is now active'
                )
            else:
                rumps.notification(
                    title='Selection Failed',
                    subtitle='',
                    message=f'Failed to select YubiKey {serial}'
                )
        except Exception as e:
            logger.error(f"Error selecting YubiKey: {str(e)}")
            rumps.notification(
                title='Selection Failed',
                subtitle='',
                message=str(e)
            )

    @rumps.clicked("Open Web Interface")
    def open_web(self, _):
        webbrowser.open('http://localhost:5001')

    # @rumps.clicked("Quit")
    # def quit_app(self, _):
    #     """Quit the application"""
    #     if self.quit_callback:
    #         self.quit_callback()
    #     else:
    #         rumps.quit_application()