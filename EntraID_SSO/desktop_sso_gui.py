import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import msal
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
AUTHORITY = os.getenv("AUTHORITY")  # ex: https://login.microsoftonline.com/<tenant_id>
SCOPES = os.getenv("SCOPES", "User.Read").split()

# --- Cache de jetons persistant & protégé ---
cache_dir = Path.home() / ".msal_cache"
cache_dir.mkdir(parents=True, exist_ok=True)

token_cache = None
persist_fallback_path = cache_dir / "msal_cache_fallback.bin"
use_fallback_serializable = False

try:
    # Utilise msal-extensions si disponible (recommandé)
    from msal.extensions import FilePersistenceWithDataProtection, PersistedTokenCache  # type: ignore
    persistence = FilePersistenceWithDataProtection(str(cache_dir / "msal_public_cache_gui.bin"))
    token_cache = PersistedTokenCache(persistence)
except Exception:
    # Fallback : cache sérialisable simple (non chiffré)
    from msal import SerializableTokenCache  # type: ignore
    token_cache = SerializableTokenCache()
    use_fallback_serializable = True
    if persist_fallback_path.exists():
        token_cache.deserialize(persist_fallback_path.read_text())

# --- Application publique MSAL (client lourd) ---
app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=token_cache)

def _persist_fallback_if_needed():
    # Persistance manuelle si on utilise le cache sérialisable
    if use_fallback_serializable and token_cache and token_cache.has_state_changed:
        persist_fallback_path.write_text(token_cache.serialize())

def acquire_token():
    """Tente d'abord le SSO silencieux, sinon ouvre le navigateur (interactive)."""
    accounts = app_msal.get_accounts()
    if accounts:
        token = app_msal.acquire_token_silent(SCOPES, account=accounts[0])
        if token and "access_token" in token:
            _persist_fallback_if_needed()
            return token
    token = app_msal.acquire_token_interactive(scopes=SCOPES)
    _persist_fallback_if_needed()
    return token

def on_login():
    try:
        token = acquire_token()
        if not token or "access_token" not in token:
            raise RuntimeError(token.get("error_description", "Échec de l'authentification"))
        res = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            timeout=30,
        )
        res.raise_for_status()
        me = res.json()
        email = me.get('mail') or me.get('userPrincipalName')
        lbl_status.config(text=f"Connecté : {me.get('displayName')}\\nEmail : {email}")
        btn_login.config(state="disabled")
        btn_logout.config(state="normal")
    except Exception as e:
        messagebox.showerror("Erreur", str(e))

def on_logout():
    try:
        # Efface le cache
        if hasattr(token_cache, "clear"):
            token_cache.clear()
        if use_fallback_serializable and persist_fallback_path.exists():
            persist_fallback_path.unlink()  # supprime le fichier de cache non chiffré
    finally:
        lbl_status.config(text="Déconnecté")
        btn_login.config(state="normal")
        btn_logout.config(state="disabled")

# --- UI Tkinter ---
root = tk.Tk()
root.title("Entra ID SSO – Client lourd")
root.geometry("500x220")

lbl_title = tk.Label(root, text="Démo SSO Entra ID (MSAL Desktop)", font=("Segoe UI", 12, "bold"))
lbl_title.pack(padx=16, pady=(16, 8), anchor="w")

lbl_status = tk.Label(root, text="Déconnecté", justify="left")
lbl_status.pack(padx=16, pady=8, anchor="w")

frm_buttons = tk.Frame(root)
frm_buttons.pack(padx=16, pady=8, anchor="w")

btn_login = tk.Button(frm_buttons, text="Se connecter", width=18, command=on_login)
btn_login.grid(row=0, column=0, padx=(0, 8))

btn_logout = tk.Button(frm_buttons, text="Se déconnecter", width=18, state="disabled", command=on_logout)
btn_logout.grid(row=0, column=1)

root.mainloop()
