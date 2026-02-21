# Legacy: AutoPrompter (Desktop-App Automation)

## Herkunft
Urspruenglich als BACH-Modul gebaut, dann als Standalone extrahiert:
`C:\Users\User\OneDrive\Software Entwicklung\DEV_AutoPrompter\`

## Was es macht
- PyQt6 GUI mit Dark Theme
- Startet Claude Desktop App per Hotkey (Ctrl+Space)
- Daemon-Modus: Sendet in konfigurierbaren Intervallen Prompts
- Profile: developer, reviewer, analyst, assistant
- System Tray Integration

## Technologie
- Python 3.10+, PyQt6, pyautogui, pyperclip
- Eine Datei: autoprompter.py (~1400 Zeilen)

## Status in llmauto
Legacy-Modus: `llmauto daemon start [profil]`
Wird als `modes/daemon.py` portiert.
Claude Code Sessions sind effektiver, aber Desktop-App-User profitieren weiter.
