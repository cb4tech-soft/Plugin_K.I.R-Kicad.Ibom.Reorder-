import pcbnew
import wx
import webbrowser
import traceback
import subprocess
import sys
import threading
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

class hello_world(pcbnew.ActionPlugin):
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
        # Exécuter sur le thread principal wx (requis pour les boîtes de dialogue)
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

            _debug_log(f"html_path OK: {html_path}")

            # Récupérer le chemin du projet KiCad
            board = pcbnew.GetBoard()
            if not board:
                _debug_log("Erreur: Pas de board (pcbnew.GetBoard() vide)")
                wx.MessageBox("Aucun projet KiCad ouvert. Ouvrez un fichier .kicad_pcb d'abord.", "Erreur")
                return

            board_path = str(board.GetFileName()) if board.GetFileName() else ""
            _debug_log(f"board_path: {board_path}")
            if not board_path:
                wx.MessageBox("Impossible de déterminer le chemin du projet.", "Erreur")
                return

            project_dir = Path(board_path).parent
            ibom_path = project_dir / "bom" / "ibom.html"

            if not ibom_path.exists():
                wx.MessageBox(
                    f"Fichier ibom.html introuvable dans :\n{ibom_path}\n\n"
                    "Générez d'abord l'IBOM avec le plugin Interactive HTML BOM.\n\n"
                    "Ouverture de K.I.R. sans fichier préchargé.",
                    "Attention"
                )
                url = html_path.as_uri()
                try:
                    webbrowser.open(url)
                except Exception:
                    if sys.platform == "linux":
                        subprocess.Popen(["xdg-open", url], start_new_session=True)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", url], start_new_session=True)
                    else:
                        subprocess.Popen(["start", "", url], shell=True, start_new_session=True)
                return

            # Lire ibom.html
            with open(ibom_path, "r", encoding="utf-8") as f:
                ibom_content = f.read()

            # Créer un serveur HTTP local pour servir KIR_V2.html et ibom via paramètre d'URL
            kir_html = html_path.read_text(encoding="utf-8")

            class KIRHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed = urlparse(self.path)
                    path = parsed.path
                    if path in ("/", "/KIR_V2.html", ""):
                        # Servir KIR_V2.html avec le paramètre dataUrl dans l'URL
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
                    pass  # Désactiver les logs du serveur

            server = HTTPServer(("127.0.0.1", 0), KIRHandler)
            server.socket.settimeout(2)  # Timeout 2s entre les requêtes
            port = server.server_address[1]
            url = f"http://127.0.0.1:{port}/?dataUrl=/ibom"

            def run_server():
                request_count = 0
                max_requests = 6
                while request_count < max_requests:
                    try:
                        server.handle_request()
                        request_count += 1
                    except Exception:
                        break  # Timeout (2s sans requête) ou erreur → fermer
                server.server_close()

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()

            import time
            time.sleep(0.2)  # Laisser le serveur démarrer

            try:
                webbrowser.open(url)
            except Exception:
                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", url], start_new_session=True)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", url], start_new_session=True)
                else:
                    subprocess.Popen(["start", "", url], shell=True, start_new_session=True)

            _debug_log("Succès - navigateur ouvert")

        except Exception as e:
            _debug_log(f"EXCEPTION: {e}\n{traceback.format_exc()}")
            wx.MessageBox(
                f"Erreur K.I.R. :\n\n{str(e)}\n\n{traceback.format_exc()}",
                "Erreur",
                wx.OK | wx.ICON_ERROR
            )
