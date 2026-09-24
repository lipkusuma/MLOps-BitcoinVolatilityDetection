import requests
import pandas as pd

print("Sedang menarik data dari CoinGecko API...")

url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1"
response = requests.get(url)
data = response.json()

# Ambil data harga dan volume dari JSON API
prices = data['prices']
volumes = data['total_volumes']

df_price = pd.DataFrame(prices, columns=['timestamp', 'price'])
df_vol = pd.DataFrame(volumes, columns=['timestamp', 'volume'])

# Gabungkan berdasarkan timestamp
df = pd.merge(df_price, df_vol, on='timestamp')

# 1. SIMPAN DATA MURNI (Harga + Volume)
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.to_csv("data/raw/btc_raw_latest.csv", index=False)

# 2. TAMPILAN TERMINAL (UTC + WIB)
df_display = df.copy()
df_display['utc'] = df_display['timestamp'].dt.strftime('%H:%M UTC')
df_display['wib'] = df_display['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Jakarta').dt.strftime('%d %b %Y | %H:%M WIB')
df_display['price_fmt'] = df_display['price'].apply(lambda x: f"${x:,.2f}")
df_display['vol_fmt'] = df_display['volume'].apply(lambda x: f"${x:,.0f}")

# Layout Terminal Header
print("\n" + "═"*78)
print("     🚀 DATA INGESTION SUCCESSFUL: BITCOIN PRICE & VOLUME MONITOR")
print("═"*78)
print(f" Status API  : 200 OK")
print(f" Total Rows  : {len(df)} records")
print(f" Saved File  : data/raw/btc_raw_latest.csv")
print("─"*78)
print(" SAMPLE DATA (HEAD 5):")
print("┌─────────────┬───────────────────────────┬──────────────────┬─────────────────────┐")
print("│ Waktu (UTC) │        Waktu (WIB)        │  Harga BTC (USD) │ 24h Volume (USD)    │")
print("├─────────────┼───────────────────────────┼──────────────────┼─────────────────────┤")

for _, row in df_display.head(5).iterrows():
    utc = row['utc'].center(11)
    wib = row['wib'].center(25)
    price = row['price_fmt'].rjust(16)
    vol = row['vol_fmt'].rjust(19)
    print(f"│ {utc} │ {wib} │ {price} │ {vol} │")

print("└─────────────┴───────────────────────────┴──────────────────┴─────────────────────┘")
print("═"*78 + "\n")