import numpy as np
import pandas as pd
from pathlib import Path

def generate(n=5000, seed=42, output="data/raw/deliveries.csv"):
    rng=np.random.default_rng(seed)
    dates=pd.date_range("2025-01-01","2025-12-31",freq="D")
    regions=np.array(["Sudeste","Sul","Centro-Oeste","Nordeste"])
    routes=np.array([f"ROTA-{i:02d}" for i in range(1,21)])
    vehicles=np.array([f"VEIC-{i:03d}" for i in range(1,61)])
    carriers=np.array(["Frota própria","Transportadora Alfa","Transportadora Beta","Transportadora Gama"])
    date=rng.choice(dates,n); region=rng.choice(regions,n,p=[.48,.2,.14,.18])
    route=rng.choice(routes,n); vehicle=rng.choice(vehicles,n)
    carrier=rng.choice(carriers,n,p=[.45,.25,.18,.12])
    km=np.round(rng.gamma(2.2,38,n)+8,1)
    efficiency=np.round(rng.normal(7.2,1,n).clip(4.5,10),2)
    liters=np.round(km/efficiency,2); price=np.round(rng.normal(5.85,.22,n).clip(5.2,6.5),2)
    fuel=np.round(liters*price,2); toll=np.round(rng.choice([0,0,0,12,18,25,35,48],n),2)
    driver=np.round(km*rng.normal(.82,.08,n).clip(.6,1.1),2)
    maintenance=np.round(km*rng.normal(.18,.04,n).clip(.08,.3),2)
    third=np.where(carrier=="Frota própria",0,np.round(rng.normal(42,12,n).clip(15,85),2))
    warehouse=np.round(rng.normal(7.5,1.5,n).clip(3,14),2); other=np.round(rng.normal(4,1.2,n).clip(1,9),2)
    total=np.round(fuel+toll+driver+maintenance+third+warehouse+other,2)
    revenue=np.round(rng.normal(185,35,n).clip(90,320),2)
    status=rng.choice(["Entregue no prazo","Entregue com atraso","Devolvida"],n,p=[.79,.14,.07])
    delay=np.where(status=="Entregue com atraso",rng.integers(1,5,n),0)
    out=pd.DataFrame({"delivery_id":[f"ENT-{i:06d}" for i in range(1,n+1)],
      "delivery_date":pd.to_datetime(date).strftime("%Y-%m-%d"),"region":region,"route_id":route,
      "vehicle_id":vehicle,"carrier":carrier,"distance_km":km,"fuel_efficiency_km_l":efficiency,
      "fuel_liters":liters,"fuel_price_brl_l":price,"fuel_cost_brl":fuel,"toll_cost_brl":toll,
      "driver_cost_brl":driver,"maintenance_cost_brl":maintenance,"third_party_cost_brl":third,
      "warehouse_cost_brl":warehouse,"other_cost_brl":other,"total_logistics_cost_brl":total,
      "freight_revenue_brl":revenue,"delivery_status":status,"delay_days":delay})
    Path(output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(output,index=False)
    return out

if __name__=="__main__":
    generate()
