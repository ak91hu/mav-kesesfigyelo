# MÁV Késésfigyelő Discord Bot

Egy egyszerű, Docker konténerben futó bot, amely 15 percenként ellenőrzi a **Budapest–Győr–Hegyeshalom (1-es)** és az abból leágazó **Oroszlány (12-es)** vasútvonalon közlekedő MÁV és GYSEV vonatokat. Ha késést észlel, egy formázott, magyar nyelvű listát küld a késésben lévő vonatokról egy megadott Discord csatornára.

Ideális ingázóknak vagy vasút-rajongóknak, akik egy adott vonalról szeretnének gyors, automatizált áttekintést kapni.

## 📋 Főbb Jellemzők

* **Valós idejű adatok:** A nem-hivatalos MÁV EMMA API-t használja a járműpozíciók és késések lekérdezésére.
* **Precíziós Szűrés:** Egy kétlépcsős szűrő biztosítja, hogy **kizárólag** a figyelt vasútvonalon közlekedő vonatok jelenjenek meg.
    1.  **Azonosítás:** Kiszűri a vonalhoz tartozó vonatneveket (pl. S10, G10, S12) és a nemzetközi vonatokat (pl. Railjet, Dacia), illetve a vonalhoz tartozó célállomásokat.
    2.  **Helymeghatározás:** Ellenőrzi, hogy a vonat következő megállója fizikailag is szerepel-e az 1-es vagy 12-es vonal hivatalos állomáslistáján. Ez kiszűri a más vonalakról érkező (pl. szolnoki, pécsi) vonatokat, még akkor is, ha a Keletibe tartanak.
* **Automatizált:** Egy `cron` időzítő futtatja a szkriptet 15 percenként, emberi beavatkozás nélkül.
* **Discord Integráció:** Egy könnyen olvasható, formázott, magyar nyelvű üzenetet küld a megadott Discord webhookra.
* **Tördelés:** Ha a késő vonatok listája túl hosszú (meghaladja a Discord 2000 karakteres limitjét), a bot automatikusan több üzenetre bontja a listát.
* **Konténerizált:** Az egész megoldás egyetlen, pehelysúlyú (`python:3.10-slim`) Docker konténerben fut, minimális beállítással és erőforrás-igénnyel.



## ⚙️ Működési Folyamat

A megoldás egy egyszerű, de robusztus folyamatot követ:

1.  A Docker konténer elindulásakor elindítja a `cron` szolgáltatást.
2.  A `cron` a beállításoknak megfelelően (`*/15 * * * *`) 15 percenként lefuttatja a `mav_discord.py` Python szkriptet.
3.  A Python szkript lekérdezi az összes aktív jármű pozícióját a MÁV EMMA API-ról.
4.  A szkript alkalmazza a fent leírt kétlépcsős szűrést (vonattípus, kulcsszavak ÉS állomáslista).
5.  A szűrt listán ellenőrzi a késési adatokat (`arrivalDelay`, `departureDelay`).
6.  Összeállít egy magyar nyelvű szöveges üzenetet a 0 percnél többet késő vonatokból, késés szerint csökkenő sorrendben.
7.  A szkript beolvassa a `DISCORD_WEBHOOK_URL` környezeti változót, amit a konténer indításakor adtunk meg.
8.  Elküldi a formázott üzenetet (vagy üzenet-darabokat) a megadott Discord webhookra.
9.  A folyamat a következő 15 perces időzítésig alvó állapotba kerül.

## 📂 Fájlok Felépítése

A repository három fő fájlt tartalmaz, amelyek a megoldás működéséhez szükségesek.

### `mav_discord.py`

A bot "agya". Ez a Python szkript felelős az összes logikáért:
* Importálja a szükséges könyvtárakat (`requests`, `json`, `re`, `os`, `sys`).
* Tartalmazza az API lekérdezést, a szűrési logikát (állomáslista, kulcsszavak) és a késés-ellenőrzést.
* Formázza a kimeneti üzenetet, eltávolítva a felesleges HTML elemeket a nevekből.
* Kezeli a Discord webhookra történő küldést, beleértve az üzenetek darabolását is.
* Beolvassa a webhook URL-t az `os.environ`-ból, így a titkos kulcs nincs "bedrótozva" a kódba.

### `Dockerfile`

A Docker konténer "tervrajza". Ez a fájl mondja meg a Dockernek, hogyan építse fel az image-et:
* `FROM python:3.10-slim`: Egy minimális méretű, hivatalos Python alapképet használ.
* `RUN apt-get ... install cron`: Telepíti a `cron` időzítő szolgáltatást a konténerbe.
* `WORKDIR /app`: Létrehoz egy `/app` mappát a konténerben, és beállítja munkakönyvtárnak.
* `COPY requirements.txt .` és `RUN pip install ...`: Másolja a függőségi listát és telepíti a `requests` csomagot.
* `COPY mav_discord.py .`: Másolja a Python szkriptet a konténerbe.
* `RUN echo ... > /etc/cron.d/mav-cron`: Létrehozza a `cron` feladatot, ami 15 percenként futtatja a szkriptet, és a futás naplóját a `/var/log/cron.log` fájlba irányítja.
* `CMD cron && tail -f ...`: A konténer indítóparancsa. Elindítja a `cron` démont, majd a `tail -f` paranccsal "életben tartja" a konténert, és folyamatosan kiírja a logfájl tartalmát, amit a `docker logs` paranccsal láthatunk.

### `requirements.txt`

A Python projekt függőségi listája. Csak egy csomagot tartalmaz:
* `requests`: Az API lekérdezésekhez és a Discord webhookra való küldéshez szükséges.

## 🚀 Telepítés és Futtatás

### 1. Előfeltételek

* **Docker** és **Git** telepítve a gépeden (vagy a szervereden).

### 2. Kód Letöltése

Klónozd a repository-t a gépedre:
```bash
git clone [https://github.com/FELHASZNALONEVED/REPOZITORIUM_NEVE.git](https://github.com/FELHASZNALONEVED/REPOZITORIUM_NEVE.git)
cd REPOZITORIUM_NEVE
```
### 3. Discord Webhook Beszerzése
Szükséged lesz egy Discord Webhook URL-re, hogy a bot tudjon üzenetet küldeni.

1.  A Discord szervereden kattints a szerver nevére -> `Szerverbeállítások`.
2.  Menj az `Integrációk` menüpontra.
3.  Kattints a `Webhookok` -> `Új Webhook` gombra.
4.  Adj neki egy nevet (pl. "MÁV Bot"), válaszd ki a csatornát, ahová posztolni szeretnél.
5.  Kattints a `Webhook URL másolása` gombra.

> ⚠️ **FONTOS BIZTONSÁGI FIGYELMEZTETÉS:**
> A Webhook URL egy **titkos kulcs (secret)**. Bárki, aki megszerzi, üzeneteket küldhet a csatornádra.
>
> Kezeld úgy, mint egy jelszót!
> * **SOHA** ne írd bele a kódba, ne töltsd fel GitHubra, és ne oszd meg nyilvánosan.
> * A szkriptet szándékosan úgy írtuk, hogy ezt az URL-t környezeti változóból (kívülről) olvassa be.

### 4. Docker Image Építése
Nyiss egy terminált a projekt letöltött mappájában (ahol a `Dockerfile` is van), és futtasd a következő parancsot az image felépítéséhez:

```bash
docker build -t mav-bot .
```

### 5. A Konténer Futtatása
A terminálban futtasd a következő parancsot.

Cseréld le a <SAJAT_WEBHOOK_URL_IDE> részt a 3. lépésben kimásolt, titkos Discord Webhook URL-edre.

```bash
docker run -d --name mav-discord-bot \
    -e DISCORD_WEBHOOK_URL="<SAJAT_WEBHOOK_URL_IDE>" \
    mav-bot
```
Parancs magyarázata:

-d (Detached): A konténer a háttérben fog futni.

--name mav-discord-bot: Egyedi nevet ad a futó konténernek, így könnyebb később leállítani vagy megnézni a logokat.

-e DISCORD_WEBHOOK_URL="...": Beállítja a DISCORD_WEBHOOK_URL nevű környezeti változót a konténeren belül. A Python szkript ezt az értéket fogja használni a küldéshez.

A konténer elindult, és 15 percenként (00, 15, 30, 45 perckor) automatikusan le fog futni.
