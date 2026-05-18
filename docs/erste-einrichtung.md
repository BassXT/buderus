# Ersteinrichtung ohne Hilfsskript

Diese Anleitung beschreibt den aktuell zuverlässigsten Weg für die erste Anmeldung mit SingleKey ID. Sie ist etwas sperrig, aber sie vermeidet lokale Zusatzprogramme und funktioniert mit dem vorhandenen MyBuderus-Redirect.

## Wichtig vorab

- Nutze für die Ersteinrichtung einen Desktop-Browser wie Chrome, Edge oder Firefox.
- Nutze nicht das iPhone oder Android-Gerät, wenn dort die MyBuderus-App installiert ist. Die App kann den finalen Redirect abfangen.
- Nach dem Login kann eine Netzwerk- oder Weiterleitungsfehlermeldung erscheinen. Das ist in diesem Ablauf normal.

## Schritt für Schritt

1. Öffne in Home Assistant die Integration `Buderus MX300`.
2. Kopiere die angezeigte SingleKey-Login-URL noch nicht sofort in den Browser.
3. Öffne zuerst im Browser die Entwicklerwerkzeuge mit `F12`.
4. Wechsle in den Tab `Netzwerk` oder `Network`.
5. Aktiviere `Protokoll beibehalten`, `Preserve log` oder eine ähnlich benannte Option.
6. Öffne jetzt die SingleKey-Login-URL aus Home Assistant.
7. Melde dich mit deinem SingleKey-Konto an.
8. Wenn danach eine Fehlerseite erscheint, bleibe auf dieser Seite und gehe zurück zum Tab `Netzwerk`.
9. Suche den letzten Eintrag mit `/auth/connect/authorize/callback`.
10. Öffne diesen Eintrag.
11. Suche in den Antwort-Headern den Header `Location`.
12. Kopiere den kompletten Wert. Er beginnt mit:

```text
com.buderus.tt.dashtt://app/login
```

13. Füge diese komplette URL in das Home-Assistant-Setupfeld ein.
14. Bestätige den Dialog.

## Falls du nur den Code siehst

Du kannst alternativ nur den Wert hinter `code=` aus der Redirect-URL einfügen. Die komplette `com.buderus.tt.dashtt://app/login...` URL ist aber weniger fehleranfällig.

## Warum ist das nötig?

Die MyBuderus-App nutzt einen App-Redirect statt einer normalen lokalen Webadresse. SingleKey akzeptiert für diesen Client nach aktuellem Stand keine normale HTTP-Callback-URL und keinen nutzbaren Device-Code-Flow. Deshalb muss der finale Redirect beim ersten Login einmal aus den Browser-Entwicklerwerkzeugen kopiert werden.
