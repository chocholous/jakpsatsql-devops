-- CzechitasProvisioner.applescript
-- Nativní macOS .app wrapper pro Czechitas Provisioner
--
-- Po zkompilování (osacompile) do .app bundle:
--   1. Zobrazí dialog pro výběr .tsv souboru
--   2. Zobrazí dialog pro zadání passphrase (skryté)
--   3. Spustí provision-macos ze stejné složky jako .app
--   4. Zachytí výstup a zobrazí výsledek
--
-- Předpoklady: provision-macos a provisioner_key.p8 musí být
-- ve stejné složce jako CzechitasProvisioner.app

-- Zjisti umístění .app bundle (POSIX cesta k Resources nebo obsahu)
-- Když je zkompilován osacompile, spouštěcí složka je složka .app
set appPath to POSIX path of (path to me)

-- Odstraň lomítko na konci pokud existuje
if appPath ends with "/" then
    set appPath to text 1 thru -2 of appPath
end if

-- Zjisti složku obsahující .app (parent folder)
-- appPath je cesta k .app bundle, chceme složku kde leží .app
set appFolder to do shell script "dirname " & quoted form of appPath

-- Ověř, zda provision-macos existuje v téže složce jako .app
set binaryPath to appFolder & "/provision-macos"
set keyPath to appFolder & "/provisioner_key.p8"

set binaryExists to do shell script "test -f " & quoted form of binaryPath & " && echo yes || echo no"
if binaryExists is not "yes" then
    display alert "Chyba: Binárka nenalezena" message "Soubor provision-macos nebyl nalezen ve složce:

" & appFolder & "

Ujisti se, že provision-macos a provisioner_key.p8 jsou ve stejné složce jako CzechitasProvisioner.app." as critical buttons {"Zavřít"} default button "Zavřít"
    return
end if

-- Ověř, zda provisioner_key.p8 existuje
set keyExists to do shell script "test -f " & quoted form of keyPath & " && echo yes || echo no"
if keyExists is not "yes" then
    display alert "Chyba: Klíč nenalezen" message "Soubor provisioner_key.p8 nebyl nalezen ve složce:

" & appFolder & "

Ujisti se, že provisioner_key.p8 je ve stejné složce jako CzechitasProvisioner.app." as critical buttons {"Zavřít"} default button "Zavřít"
    return
end if

-- Krok 1: Výběr TSV souboru přes nativní file picker
set selectedFile to ""
try
    set selectedFile to POSIX path of (choose file with prompt "Vyber soubor se seznamem studentek (.tsv):" of type {"public.tab-separated-values", "public.plain-text", "com.microsoft.excel.tab-separated-values-file"} default location POSIX file appFolder)
on error errMsg number errNum
    -- Uživatel klikl Zrušit nebo zavřel dialog
    if errNum is -128 then
        return
    end if
    display alert "Chyba při výběru souboru" message errMsg as warning buttons {"Zavřít"} default button "Zavřít"
    return
end try

-- Ověř, že vybraný soubor má příponu .tsv (nebo je TSV)
set fileName to do shell script "basename " & quoted form of selectedFile
set fileLower to do shell script "echo " & quoted form of fileName & " | tr '[:upper:]' '[:lower:]'"
if fileLower does not end with ".tsv" and fileLower does not end with ".txt" then
    set confirmNonTsv to button returned of (display dialog "Vybraný soubor nemá příponu .tsv:

" & fileName & "

Chceš pokračovat?" with title "Czechitas Provisioner" buttons {"Zrušit", "Pokračovat"} default button "Zrušit")
    if confirmNonTsv is "Zrušit" then
        return
    end if
end if

-- Krok 2: Zadání passphrase (skryté)
set passphrase to ""
try
    set passphraseResult to display dialog "Zadej passphrase k provisioner_key.p8:" default answer "" with hidden answer with title "Czechitas Provisioner" buttons {"Zrušit", "Spustit"} default button "Spustit"
    set passphrase to text returned of passphraseResult
    if button returned of passphraseResult is "Zrušit" then
        return
    end if
on error errMsg number errNum
    if errNum is -128 then
        return
    end if
    display alert "Chyba" message errMsg as warning buttons {"Zavřít"} default button "Zavřít"
    return
end try

if passphrase is "" then
    display alert "Passphrase je prázdná" message "Passphrase nesmí být prázdná. Provisioning byl zrušen." as warning buttons {"Zavřít"} default button "Zavřít"
    return
end if

-- Krok 3: Spuštění provision-macos se zachycením výstupu
-- Sestavíme shell příkaz: nastavíme env var a spustíme binárku s --yes příznakem
set cmdOutput to ""
set exitCode to 0

try
    -- Použij shell skript pro spuštění s env proměnnou a zachycení výstupu
    -- 2>&1 sloučí stderr do stdout pro zobrazení kompletního výstupu
    set shellCmd to "cd " & quoted form of appFolder & " && SF_KEY_PASSPHRASE=" & quoted form of passphrase & " " & quoted form of binaryPath & " " & quoted form of selectedFile & " --yes 2>&1; echo \"EXIT_CODE:$?\""
    set rawOutput to do shell script shellCmd

    -- Extrahuj exit kód z výstupu
    if rawOutput contains "EXIT_CODE:" then
        set exitMarker to "EXIT_CODE:"
        set exitStart to (offset of exitMarker in rawOutput) + (length of exitMarker)
        set exitCodeStr to text exitStart thru -1 of rawOutput
        -- Odstraň případné trailing whitespace/newline
        set exitCodeStr to do shell script "echo " & quoted form of exitCodeStr & " | tr -d '[:space:]'"
        try
            set exitCode to exitCodeStr as integer
        on error
            set exitCode to 0
        end try
        -- Odstraň EXIT_CODE řádek z výstupu
        set cmdOutput to text 1 thru ((offset of exitMarker in rawOutput) - 2) of rawOutput
    else
        set cmdOutput to rawOutput
    end if
on error shellErrMsg number shellErrNum
    -- do shell script vyhodí výjimku při exit code != 0
    -- Zachyť chybový výstup
    set cmdOutput to shellErrMsg
    set exitCode to 1
end try

-- Krok 4: Zobrazení výsledku
-- Omez délku výstupu pro dialog (max 2000 znaků)
set maxLen to 2000
if length of cmdOutput > maxLen then
    set cmdOutput to text 1 thru maxLen of cmdOutput & "
... (výstup zkrácen)"
end if

if exitCode is 0 then
    -- Úspěch
    display alert "Provisioning dokončen" message "Provisioning proběhl úspěšně.

Výstup:
" & cmdOutput buttons {"Zavřít"} default button "Zavřít"
else
    -- Chyba
    display alert "Chyba při provisioningu" message "Provisioning skončil chybou (kód " & exitCode & ").

Výstup:
" & cmdOutput as critical buttons {"Zavřít"} default button "Zavřít"
end if
