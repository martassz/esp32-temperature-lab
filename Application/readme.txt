========================================================================
Obslužná aplikace pro měřicí stanici
Laboratorní úloha - Porovnání způsobů měření teploty prostředí
Autor: Martin Zatloukal
Zdrojové kódy a dokumentace:
https://github.com/martassz/esp32-temperature-lab
========================================================================

Tato složka obsahuje plně zkompilovanou desktopovou aplikaci pro řízení 
měřicí komory a vizualizaci dat. K jejímu provozu NENÍ potřeba instalovat 
Python ani žádné dodatečné knihovny.

RYCHLÝ START (NÁVOD K POUŽITÍ):
------------------------------------------------------------------------
1. Připojení k řídicí jednotce (ESP32):
   - Přes USB: Připojte řídicí jednotku k PC pomocí datového USB kabelu.
   - Přes Bluetooth: Lze se připojit i bezdrátově. V takovém případě 
     však musí být ESP32 připojeno k externímu napájení (např. powerbanka).
     
2. Spusťte hlavní soubor s aplikací (např. "Python application.exe").
   
   TIP: Tento spouštěcí .exe soubor si můžete libovolně přejmenovat 
   (např. na "Mereni_Teploty.exe") nebo si z něj vytvořit zástupce na 
   plochu. Důležité je pouze to, aby hlavní soubor zůstal vždy ve stejné 
   složce společně se složkou "_internal", do které nijak nezasahujte.

3. V levém panelu aplikace vyberte příslušný COM port (USB nebo Bluetooth) 
   a klikněte na "Připojit k ESP".
   
4. Vyberte požadovanou část laboratorní úlohy.

5. Výběr senzorů: Pomocí tlačítka "Výběr senzorů" si můžete zvolit, 
   které konkrétní měřicí prvky chcete v grafu sledovat a logovat. 
   (Aplikace automaticky předvybírá vhodné senzory podle zvolené úlohy, 
   ale výběr si můžete libovolně přizpůsobit).

6. Parametry měření: Před startem můžete přes tlačítko "⚙ Parametry 
   měření" upravit celkovou dobu měření a periodu vzorkování (jak často 
   se data ukládají).
   
7. Kliknutím na "START" zahájíte měření.

DŮLEŽITÉ BEZPEČNOSTNÍ UPOZORNĚNÍ:
------------------------------------------------------------------------
Měřicí komora je chráněna softwarovým bezpečnostním limitem nastaveným 
na 42.0 °C. Pokud teplota tuto hranici překročí, aplikace z bezpečnostních 
důvodů okamžitě zastaví měření a odpojí výkonové topné prvky.

Řešení: Pokud k tomu dojde, otevřete víko komory, nechte vzduch uvnitř 
samovolně zchladnout pod povolenou hranici a teprve poté pokračujte v měření.

ŘEŠENÍ NEJČASTĚJŠÍCH PROBLÉMŮ:
------------------------------------------------------------------------
* Aplikace nenachází žádný COM port:
  - Zkontrolujte kabel (některé levné USB kabely slouží pouze k nabíjení).
  - Při použití Bluetooth zkontrolujte, zda je zařízení s PC spárováno.

* Nelze se připojit k nalezenému COM portu (Chyba přístupu):
  - Port pravděpodobně blokuje jiný program. Ujistěte se, že nemáte 
    otevřený Sériový monitor v jiné aplikaci (např. Arduino IDE).

* Aplikace nereaguje nebo se po připojení neobjevují data:
  - Zkontrolujte fyzické propojení mezi řídicí jednotkou a samotnou 
    měřicí komorou (kabely RJ45).
  - Odpojte zařízení v aplikaci, fyzicky odpojte a znovu zapojte napájení 
    ESP32 a zkuste se připojit znovu.

