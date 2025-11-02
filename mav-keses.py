import requests
import json
import re
import os
import sys

API_URL = "https://emma.mav.hu/otp2-backend/otp/routers/default/index/graphql"
GRAPHQL_QUERY = """
{
  vehiclePositions(
    swLat: 45.7,
    swLon: 16.1,
    neLat: 48.6,
    neLon: 22.9
  ) {
    vehicleId
    lat
    lon
    speed
    trip {
      gtfsId
      tripHeadsign
      directionId
      route {
        shortName
        longName
        type
      }
    }
    nextStop {
      arrivalDelay
      departureDelay
      stop {
        gtfsId
        name
        lat
        lon
      }
    }
  }
}
"""
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://emma.mav.hu",
    "Referer": "https://emma.mav.hu/",
}

LINE_1_STATIONS = {
    "Budapest-Keleti", "Budapest-Kelenföld", "Budaörs", "Törökbálint",
    "Biatorbágy", "Herceghalom", "Bicske alsó", "Bicske", "Szár",
    "Szárliget", "Alsógalla", "Tatabánya", "Vértesszőlős", "Tóvároskert",
    "Tata", "Almásfüzitő", "Almásfüzitő felső", "Komárom", "Ács",
    "Nagyszentjános", "Győrszentiván", "Győr", "Abda", "Öttevény",
    "Lébény-Mosonszentmiklós", "Moson", "Mosonmagyaróvár", "Levél",
    "Hegyeshalom", "Bánhida", "Oroszlány"
}

ZONAL_ROUTES = ["S10", "G10", "S12"]

ROUTE_KEYWORDS = [
    "győr", "tatabánya", "hegyeshalom", "oroszlány", "wien", "komárom",
    "csárdás", "kálmán imre", "railjet", "rjx", "dráva", "mura", "savaria",
    "advent", "lehár", "liszt ferenc", "semmelweis", "dacia"
]

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>|&.*?;')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def send_to_discord(webhook_url, message_content):
    max_len = 2000

    if len(message_content) <= max_len:
        data = {"content": message_content}
        try:
            response = requests.post(webhook_url, json=data)
            response.raise_for_status()
            print(f"Discord üzenet sikeresen elküldve.")
        except requests.exceptions.RequestException as e:
            print(f"Hiba a Discord webhook küldésekor: {e}", file=sys.stderr)
    else:
        print(f"Üzenet túl hosszú ({len(message_content)} karakter). Darabolás...")
        chunks = []
        current_chunk = ""
        for line in message_content.splitlines(True):
            if len(current_chunk) + len(line) > max_len - 30:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line
        chunks.append(current_chunk)

        for i, chunk in enumerate(chunks):
            chunk_content = f"**Folytatás ({i+1}/{len(chunks)})...**\n" if i > 0 else ""
            chunk_content += chunk

            data = {"content": chunk_content}
            try:
                print(f"Küldés: {i+1}. darab...")
                response = requests.post(webhook_url, json=data)
                response.raise_for_status()
                print(f"Discord üzenet ({i+1}/{len(chunks)}) sikeresen elküldve.")
            except requests.exceptions.RequestException as e:
                print(f"Hiba a Discord webhook küldésekor ({i+1}. darab): {e}", file=sys.stderr)

def get_delayed_line_1_trains_hun():
    output_lines = []
    try:
        response = requests.post(API_URL, headers=HEADERS, json={"query": GRAPHQL_QUERY})
        response.raise_for_status()
        data = response.json()

        if "data" not in data or "vehiclePositions" not in data["data"]:
            print("Hiba: Nem található 'vehiclePositions' az API válaszában.", file=sys.stderr)
            return None

        all_vehicles = data["data"]["vehiclePositions"]
        filtered_delayed_trains = []

        for vehicle in all_vehicles:
            is_on_line_1 = False
            trip = vehicle.get("trip")
            if not trip: continue
            route = trip.get("route")
            if not route: continue
            route_type = route.get("type")
            if not route_type: continue

            if not (100 < route_type < 200):
                continue

            longName_raw = route.get("longName")
            longName_lower = (longName_raw or "").lower()
            headsign_lower = (trip.get("tripHeadsign") or "").lower()

            if longName_raw in ZONAL_ROUTES:
                is_on_line_1 = True
            else:
                for keyword in ROUTE_KEYWORDS:
                    if keyword in longName_lower or keyword in headsign_lower:
                        is_on_line_1 = True
                        break

            if not is_on_line_1:
                continue

            next_stop_name = "N/A"
            nextStop = vehicle.get("nextStop")
            if nextStop and nextStop.get("stop"):
                next_stop_name = nextStop["stop"].get("name", "N/A")

            if next_stop_name not in LINE_1_STATIONS:
                continue

            delay_sec = 0
            if nextStop:
                arrival_delay = nextStop.get("arrivalDelay", 0) or 0
                departure_delay = nextStop.get("departureDelay", 0) or 0
                delay_sec = max(arrival_delay, departure_delay)

            if delay_sec > 0:
                filtered_delayed_trains.append((vehicle, delay_sec, next_stop_name))

        filtered_delayed_trains.sort(key=lambda x: x[1], reverse=True)

        output_lines.append(f"--- Járművek a hálózaton: {len(all_vehicles)} ---")
        output_lines.append(f"--- Találat: {len(filtered_delayed_trains)} KÉSŐ VONAT a 1-es vonalon (precíz szűréssel) ---\n")

        if not filtered_delayed_trains:
            output_lines.append("Nem található késő vonat ezen a vonalon.")
            return "\n".join(output_lines)

        for i, (train, delay_sec, next_stop_name) in enumerate(filtered_delayed_trains):

            train_longName = train.get("trip", {}).get("route", {}).get("longName", "Ismeretlen")
            train_shortName_raw = train.get("trip", {}).get("route", {}).get("shortName", "Ismeretlen")
            train_shortName = clean_html(train_shortName_raw)
            train_headsign = train.get("trip", {}).get("tripHeadsign", "Ismeretlen")
            speed_kmh = train.get("speed")
            speed_str = f"{int(speed_kmh)} km/h" if speed_kmh is not None else "N/A"
            delay_min = int(delay_sec / 60)

            vonat_nev = train_longName
            if "S" in vonat_nev or "G" in vonat_nev or "Z" in vonat_nev:
                 vonat_nev = f"{train_longName} ({train_shortName})"

            output_lines.append(f"--- {i + 1}. Késő vonat ---")
            output_lines.append(f"🔴 KÉSÉS:      {delay_min} perc ({delay_sec}s)")
            output_lines.append(f"🚄 Vonat:       {vonat_nev}")
            output_lines.append(f"➡️ Úti cél:     {train_headsign}")
            output_lines.append(f"🚉 Köv. megálló: {next_stop_name} (1-es vonal)")
            output_lines.append(f"💨 Sebesség:    {speed_str}")
            output_lines.append("-" * 30 + "\n")

        return "\n".join(output_lines)

    except requests.exceptions.RequestException as e:
        print(f"Hiba az adatlekérés során: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Hiba: Nem sikerült feldgozni a szerver válaszát (JSON).", file=sys.stderr)
        return None

if __name__ == "__main__":
    WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

    if not WEBHOOK_URL:
        print("Hiba: A DISCORD_WEBHOOK_URL környezeti változó nincs beállítva!", file=sys.stderr)
        sys.exit(1)

    print("Szkript indul... Vonatok keresése...")
    final_output = get_delayed_line_1_trains_hun()

    if final_output:
        print("Adatok sikeresen lekérve. Küldés Discordra...")
        send_to_discord(WEBHOOK_URL, final_output)
    else:
        print("Hiba történt az adatok lekérése közben, nincs mit küldeni.", file=sys.stderr)
        sys.exit(1)
