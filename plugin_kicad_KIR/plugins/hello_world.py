import pcbnew
import wx
import webbrowser
from pathlib import Path

class hello_world(pcbnew.ActionPlugin):
    def defaults(self):
        
        plugin_dir = Path(__file__).resolve().parent
        
        
        self.icon_file_name = str(plugin_dir / "icon.png")
        
        self.show_toolbar_button = True
        self.name = "Open K.I.R"
        self.category = "Aide"
        self.description = "Open the Kicad Ibom Reorder"

    def Run(self):
        
        plugin_dir = Path(__file__).resolve().parent
        html_path = plugin_dir / "KIR" / "KIR_V2.html"
        
        if not html_path.exists():
            wx.MessageBox(f"Error : File not found in \n{html_path}", "Error")
            return

        webbrowser.open(html_path.as_uri())
