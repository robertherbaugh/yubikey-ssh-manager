import rumps
import webbrowser
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
        
        # Set up the menu structure
        self.menu = [
            rumps.MenuItem("Open Web Interface", callback=self.open_web),
            None,  # Add a separator
            connect_menu,
            None,  # Add another separator
            # rumps.MenuItem("Quit", callback=self.quit_app)
        ]
        
        # Start a timer to update the server list periodically
        self.timer = rumps.Timer(self.update_server_menu, 5)
        self.timer.start()
        
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

    def connect_to_server(self, server_id):
        """Handle server connection from menu"""
        result = self.ssh_manager.connect_to_server(server_id)
        if not result['success']:
            rumps.notification(
                title='Connection Failed',
                subtitle='',
                message=result['message']
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