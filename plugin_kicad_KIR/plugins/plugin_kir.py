import pcbnew
import wx
import webbrowser
import traceback
import subprocess
import sys
import threading
import random
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

def _debug_log(msg):
    """Écrit dans un fichier pour diagnostiquer si Run() est appelé."""
    try:
        with open("/tmp/kir_plugin_debug.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

class plugin_kir(pcbnew.ActionPlugin):
    def defaults(self):
        plugin_dir = Path(__file__).resolve().parent
        icon_path = plugin_dir / "icon.png"
        self.icon_file_name = str(icon_path) if icon_path.exists() else ""
        self.show_toolbar_button = True
        self.name = "Open K.I.R"
        self.category = "Aide"
        self.description = "Open the Kicad Ibom Reorder"

    def Run(self):
        _debug_log("=== Run() déclenché ===")
        # Exécuter sur le thread principal wx
        wx.CallAfter(self._run_impl)

    def _run_impl(self):
        try:
            _debug_log("Run() appelé - démarrage")
            plugin_dir = Path(__file__).resolve().parent
            html_path = plugin_dir / "KIR" / "KIR_V2.html"
            
            if not html_path.exists():
                _debug_log(f"Erreur: KIR_V2.html introuvable: {html_path}")
                wx.MessageBox(f"Error : File not found in \n{html_path}", "Error")
                return

            # Récupérer le projet KiCad
            board = pcbnew.GetBoard()
            board_path = str(board.GetFileName()) if (board and board.GetFileName()) else ""
            
            if not board_path:
                wx.MessageBox("Aucun projet KiCad ouvert ou fichier non enregistré.", "Erreur")
                return

            project_dir = Path(board_path).parent
            ibom_path = project_dir / "bom" / "ibom.html"

            # Préparation du contenu iBOM (si présent)
            ibom_content = ""
            if ibom_path.exists():
                with open(ibom_path, "r", encoding="utf-8") as f:
                    ibom_content = f.read()
            else:
                wx.MessageBox(
                    f"Attention : ibom.html introuvable dans :\n{ibom_path}\n\n"
                    "L'outil s'ouvrira sans données préchargées.",
                    "Information"
                )

            kir_html = html_path.read_text(encoding="utf-8")

            class KIRHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed = urlparse(self.path)
                    path = parsed.path
                    if path in ("/", "/KIR_V2.html", ""):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(kir_html.encode("utf-8"))
                    elif path == "/ibom":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(ibom_content.encode("utf-8"))
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    pass

            # --- LOGIQUE DE PORT ALÉATOIRE ---
            server = None
            attempts = 0
            while attempts < 20:
                try:
                    target_port = random.randint(45000, 65000)
                    server = HTTPServer(("127.0.0.1", target_port), KIRHandler)
                    break 
                except OSError:
                    attempts += 1
            
            if not server:
                # Si vraiment aucun port n'est libre dans la plage, on laisse l'OS décider
                server = HTTPServer(("127.0.0.1", 0), KIRHandler)

            server.socket.settimeout(2)
            port = server.server_address[1]
            url = f"http://127.0.0.1:{port}/?dataUrl=/ibom"

            def run_server():
                request_count = 0
                max_requests = 10 # Augmenté un peu pour être sûr que tout charge
                while request_count < max_requests:
                    try:
                        server.handle_request()
                        request_count += 1
                    except Exception:
                        break
                server.server_close()

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()

            # Petit délai pour laisser le thread démarrer
            import time
            time.sleep(0.3)

            # Ouverture du navigateur
            try:
                webbrowser.open(url)
            except Exception:
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", url], start_new_session=True)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", url], start_new_session=True)
                else:
                    subprocess.Popen(["start", "", url], shell=True, start_new_session=True)

            _debug_log(f"Succès - Serveur sur port {port}")

        except Exception as e:
            _debug_log(f"EXCEPTION: {e}\n{traceback.format_exc()}")
            wx.MessageBox(f"Erreur K.I.R. :\n\n{str(e)}", "Erreur", wx.OK | wx.ICON_ERROR)

