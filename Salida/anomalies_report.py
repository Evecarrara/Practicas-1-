
# ============================================================
# anomalias_un_archivo.py
# Lee posibles_anomalias_recientes.csv 
# ============================================================


from pathlib import Path
import pandas as pd
import argparse


DEFAULT_INPUT = r"C:/Users/User/Desktop/Practicas1/Salida/posibles_anomalias_recientes.csv"

def read_csv_any(p: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception:
            pass
    raise RuntimeError(f"No pude leer el CSV: {p}")

def main():
    ap = argparse.ArgumentParser(description="Conteo simple de anomalías por criterio y año.")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="Ruta a posibles_anomalias_recientes.csv")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")

    df = read_csv_any(path)
    df.columns = [c.strip().lower() for c in df.columns]

    # Fecha -> Año
    if "mes_dt" in df.columns:
        fecha_col = "mes_dt"
    else:
        # fallback por si la columna se llama distinto
        cand = [c for c in df.columns if "fecha" in c or "mes" in c]
        if not cand:
            raise ValueError("No encuentro columna de fecha (mes_dt/fecha).")
        fecha_col = cand[0]

    df[fecha_col] = pd.to_datetime(df[fecha_col], errors="coerce")
    if df[fecha_col].isna().all():
        raise ValueError("No pude parsear las fechas.")
    df["anio"] = df[fecha_col].dt.year

    # Criterio normalizado
    if "criterio" not in df.columns:
        raise ValueError("Falta la columna 'criterio'.")
    df["criterio"] = df["criterio"].astype(str).str.strip().str.lower()

    # --- Totales por criterio ---
    totales = (
        df.assign(conteo=1)
          .groupby("criterio", as_index=False)["conteo"].sum()
          .sort_values("conteo", ascending=False)
    )

    # --- Por año y criterio ---
    por_anio = (
        df.assign(conteo=1)
          .groupby(["anio", "criterio"], as_index=False)["conteo"].sum()
          .sort_values(["anio", "criterio"])
    )

    # --- Pivot (filas: año / columnas: criterio) ---
    pivot = por_anio.pivot(index="anio", columns="criterio", values="conteo").fillna(0).astype(int)

    # ---- Mostrar en pantalla ----
    print("\n=== Totales por criterio ===")
    print(totales.to_string(index=False))

    print("\n=== Por año y criterio (detalle) ===")
    print(por_anio.to_string(index=False))

    print("\n=== Por año (pivot) ===")
    print(pivot.to_string())

 # --- Gráficos ---
    import matplotlib.pyplot as plt

    # 1. Distribución total por criterio
    plt.figure()
    plt.bar(totales["criterio"], totales["conteo"], color=["#ff7f0e", "#1f77b4"])
    plt.title("Distribución total de anomalías por criterio")
    plt.xlabel("Criterio")
    plt.ylabel("Cantidad de anomalías")
    plt.tight_layout()
    plt.savefig("grafico_total_anomalias.png", bbox_inches="tight")
    plt.close()

    # 2. Evolución mensual (si existe mes_dt)
    if "mes_dt" in df.columns:
        df["anio_mes"] = df["mes_dt"].dt.to_period("M").astype(str)
        mensual = (
            df.assign(conteo=1)
              .groupby(["anio_mes", "criterio"], as_index=False)["conteo"]
              .sum()
              .pivot(index="anio_mes", columns="criterio", values="conteo")
              .fillna(0)
        )
        mensual.index = pd.to_datetime(mensual.index, errors="coerce")
        mensual = mensual.sort_index()

        mensual.plot(kind="line", figsize=(9, 4))
        plt.title("Evolución mensual de anomalías por criterio")
        plt.xlabel("Mes")
        plt.ylabel("Cantidad de anomalías")
        plt.tight_layout()
        plt.savefig("grafico_mensual_anomalias.png", bbox_inches="tight")
        plt.close()

    print("\n✅ Gráficos guardados en esta carpeta:")
    print(" - grafico_total_anomalias.png")
    print(" - grafico_mensual_anomalias.png")

if __name__ == "__main__":
    main()
