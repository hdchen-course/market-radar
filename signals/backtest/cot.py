import urllib.request, json, pandas as pd
rows=[]
off=0
while True:
    u=("https://publicreporting.cftc.gov/resource/6dca-aqww.json?"
       "$limit=1000&$offset=%d&$order=report_date_as_yyyy_mm_dd"
       "&$select=report_date_as_yyyy_mm_dd,open_interest_all,noncomm_positions_long_all,noncomm_positions_short_all"
       "&$where=cftc_contract_market_code='084691'")%off
    r=json.load(urllib.request.urlopen(u,timeout=90))
    if not r: break
    rows+=r; off+=1000
    if len(r)<1000: break
df=pd.DataFrame(rows)
df["date"]=pd.to_datetime(df.report_date_as_yyyy_mm_dd).dt.tz_localize(None)
for c in ["open_interest_all","noncomm_positions_long_all","noncomm_positions_short_all"]:
    df[c]=pd.to_numeric(df[c])
df["net"]=df.noncomm_positions_long_all-df.noncomm_positions_short_all
df=df[["date","open_interest_all","net"]].sort_values("date").reset_index(drop=True)
df.to_csv("/tmp/cot_silver.csv",index=False)
print(len(df), df.date.min().date(), df.date.max().date())
print(df.tail(8).to_string())
