#!/usr/bin/env python3
"""
Werkt de omzet- en ordercijfers in index.html (de volledige PadeLMQ-teller) bij.
Draait in GitHub Actions. Hergebruikt DEZELFDE verbinding als de dagontvangst-robot:
Client ID + Client Secret -> client_credentials grant -> tijdelijk Admin API token.
GEEN nieuwe shpat_-tokens.

Env (secrets):
  Verplicht (webshop):
    SHOP_WEBSHOP_DOMAIN / SHOP_WEBSHOP_CLIENT_ID / SHOP_WEBSHOP_CLIENT_SECRET
  Optioneel (fysieke winkel) - als deze ontbreken wordt de fysieke winkel
  overgeslagen en blijft COMPONENTS.fysiek op zijn handmatige waarde staan:
    SHOP_FYSIEK_DOMAIN / SHOP_FYSIEK_CLIENT_ID / SHOP_FYSIEK_CLIENT_SECRET
  SHOPIFY_API_VERSION (bv. 2024-10)

Past in index.html ENKEL deze CONFIG-velden aan (in het <script> bovenaan):
  COMPONENTS.webshop, COMPONENTS.fysiek (enkel als fysiek gekoppeld is),
  PADELMQ_ORDERS, UPDATED
De rest blijft ongemoeid: COMPONENTS.b2b en COMPONENTS.bancontact zijn de handmatige
(vaste) waarden, en TIENDA/teksten/opmaak worden niet aangeraakt.
"""
import os, re, datetime
from zoneinfo import ZoneInfo
import requests

API = os.environ.get("SHOPIFY_API_VERSION", "2024-10")

def env(key):
    v = os.environ.get(key)
    if not v:
        raise SystemExit(f"Ontbrekend secret: {key}")
    return v

def opt(key):
    v = os.environ.get(key)
    return v if v else None

def get_token(domain, client_id, client_secret):
    """client_credentials grant -> Admin API access token (zoals de dagontvangst-robot)."""
    r = requests.post(
        f"https://{domain}/admin/oauth/access_token",
        json={"client_id": client_id, "client_secret": client_secret,
              "grant_type": "client_credentials"},
        timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_year(domain, access_token):
    """Geeft (omzet_afgerond, aantal_orders) voor het huidige kalenderjaar."""
    year = datetime.datetime.now(ZoneInfo("Europe/Brussels")).year
    since = f"{year}-01-01"
    url = f"https://{domain}/admin/api/{API}/graphql.json"
    headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
    total, count, cursor = 0.0, 0, None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = ('{ orders(first: 250, query: "created_at:>=%s AND financial_status:paid"%s) '
                 '{ edges { cursor node { currentTotalPriceSet { shopMoney { amount } } } } '
                 'pageInfo { hasNextPage } } }') % (since, after)
        r = requests.post(url, headers=headers, json={"query": query}, timeout=90)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(str(data["errors"]))
        block = data["data"]["orders"]
        for e in block["edges"]:
            total += float(e["node"]["currentTotalPriceSet"]["shopMoney"]["amount"])
            count += 1
            cursor = e["cursor"]
        if not block["pageInfo"]["hasNextPage"]:
            break
    return round(total), count

def main():
    # --- Webshop (verplicht) ---
    web_dom = env("SHOP_WEBSHOP_DOMAIN")
    web_rev, web_ord = fetch_year(web_dom,
        get_token(web_dom, env("SHOP_WEBSHOP_CLIENT_ID"), env("SHOP_WEBSHOP_CLIENT_SECRET")))
    orders_total = web_ord

    html = open("index.html", encoding="utf-8").read()
    html = re.sub(r'(webshop:\s*)\d+', lambda m: m.group(1) + str(web_rev), html, count=1)

    # --- Fysieke winkel (optioneel: 2de Shopify-account) ---
    # Ondersteunt twee methodes:
    #  1) SHOP_FYSIEK_TOKEN  = een Admin API access token (shpat_...) van een custom app
    #     die rechtstreeks in die winkel is aangemaakt. -> direct gebruikt, geen oauth.
    #  2) SHOP_FYSIEK_CLIENT_ID + SHOP_FYSIEK_CLIENT_SECRET -> client_credentials grant.
    fy_dom = opt("SHOP_FYSIEK_DOMAIN")
    fy_token = opt("SHOP_FYSIEK_TOKEN")
    fy_id, fy_sec = opt("SHOP_FYSIEK_CLIENT_ID"), opt("SHOP_FYSIEK_CLIENT_SECRET")
    if fy_dom and (fy_token or (fy_id and fy_sec)):
        try:
            token = fy_token if fy_token else get_token(fy_dom, fy_id, fy_sec)
            fys_rev, fys_ord = fetch_year(fy_dom, token)
            html = re.sub(r'(fysiek:\s*)\d+', lambda m: m.group(1) + str(fys_rev), html, count=1)
            orders_total += fys_ord
            print(f"fysiek: EUR {fys_rev} / {fys_ord} orders")
        except Exception as e:
            print(f"fysiek OVERGESLAGEN (fout bij ophalen): {e}")
    else:
        print("fysiek overgeslagen: geen sleutels ingesteld -> handmatige waarde blijft staan")

    # --- Gemeenschappelijk ---
    html = re.sub(r'(PADELMQ_ORDERS:\s*)\d+', lambda m: m.group(1) + str(orders_total), html, count=1)
    stamp = datetime.datetime.now(ZoneInfo("Europe/Brussels")).strftime("%B %-d, %Y, %H:%M")
    html = re.sub(r'(UPDATED:\s*")[^"]*(")', lambda m: m.group(1) + stamp + m.group(2), html, count=1)
    open("index.html", "w", encoding="utf-8").write(html)

    print(f"webshop: EUR {web_rev} / {web_ord} orders | totaal orders {orders_total}")

if __name__ == "__main__":
    main()
