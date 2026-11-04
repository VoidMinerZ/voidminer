from __future__ import annotations

LANGS = {"English": "en", "Español": "es", "Français": "fr", "Deutsch": "de"}
_cur = "en"
S = {
    "en": dict(dashboard="Dashboard", profiles="Profiles", optimize="Optimize", mods="Mods", skins="Skins",
               accounts="Accounts", settings="Settings", play="PLAY", playing="PLAYING", stop="Stop game",
               selected_profile="Selected profile", recent_versions="Recent versions",
               recent_profiles="Recently played", new_profile="New profile", not_signed="Not signed in"),
    "es": dict(dashboard="Inicio", profiles="Perfiles", optimize="Optimizar", mods="Mods", skins="Skins",
               accounts="Cuentas", settings="Ajustes", play="JUGAR", playing="JUGANDO", stop="Detener juego",
               selected_profile="Perfil seleccionado", recent_versions="Versiones recientes",
               recent_profiles="Jugados recientemente", new_profile="Nuevo perfil", not_signed="Sin sesión"),
    "fr": dict(dashboard="Accueil", profiles="Profils", optimize="Optimiser", mods="Mods", skins="Skins",
               accounts="Comptes", settings="Paramètres", play="JOUER", playing="EN JEU", stop="Arrêter le jeu",
               selected_profile="Profil sélectionné", recent_versions="Versions récentes",
               recent_profiles="Joués récemment", new_profile="Nouveau profil", not_signed="Non connecté"),
    "de": dict(dashboard="Übersicht", profiles="Profile", optimize="Optimieren", mods="Mods", skins="Skins",
               accounts="Konten", settings="Einstellungen", play="SPIELEN", playing="LÄUFT", stop="Spiel beenden",
               selected_profile="Gewähltes Profil", recent_versions="Letzte Versionen",
               recent_profiles="Zuletzt gespielt", new_profile="Neues Profil", not_signed="Nicht angemeldet"),
}


def set_language(name: str) -> None:
    global _cur
    _cur = LANGS.get(name, "en")


def t(key: str) -> str:
    return S.get(_cur, {}).get(key) or S["en"].get(key, key)
