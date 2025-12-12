from pathlib import Path
import argparse
import warnings
from typing import Optional, Dict

import numpy as np
import pandas as pd


try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_HW = True
except Exception:
    HAS_HW = False


import matplotlib
matplotlib.use("Agg")  # backend sin interfaz para guardar PNG
import matplotlib.pyplot as plt




DEFAULT_INPUT = r"C:/Users/User/Desktop/Practicas1/Dataset/consumo_energia_2022_en_adelante.csv"
DEFAULT_OUTDIR = r"C:/Users/User/Desktop/Practicas1/Salida"
DEFAULT_HORIZON = 12          # meses
DEFAULT_FOCUS_MONTHS = 6      # meses recientes para listar anomalías



def load_and_normalize(input_path: Path) -> tuple[pd.DataFrame, str, Optional[str]]:
    """
    Lee el CSV, estandariza nombres de columnas, infiere fecha (año/mes),
    detecta columna de consumo y de medidor, y crea 'mes_dt' (inicio de mes).
    """
    df = pd.read_csv(input_path)
    df.columns = [c.strip().lower() for c in df.columns]

    # Fecha
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["año"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
    elif "año" in df.columns and "mes" in df.columns:
        df["año"] = df["año"].astype(int)
        df["mes"] = df["mes"].astype(int)
    elif "year" in df.columns and "month" in df.columns:
        df["año"] = df["year"].astype(int)
        df["mes"] = df["month"].astype(int)
    else:
        # buscar alguna columna de fecha
        for c in df.columns:
            if "fecha" in c or "date" in c:
                df[c] = pd.to_datetime(df[c])
                df["año"] = df[c].dt.year
                df["mes"] = df[c].dt.month
                break

    # Consumo
    cons_cols = [c for c in df.columns if any(k in c for k in ["kwh", "consumo", "energia", "energy"])]
    consumo_col = cons_cols[0] if cons_cols else df.columns[-1]
    df[consumo_col] = pd.to_numeric(df[consumo_col], errors="coerce").fillna(0)

    # Medidor
    possible_med_cols = ["numero_medidor", "nro_medidor", "nro", "numero", "medidor", "meter_id", "id_medidor"]
    medidor_col: Optional[str] = None
    for c in possible_med_cols:
        if c in df.columns:
            medidor_col = c
            break
    if medidor_col is None:
        for c in df.columns:
            if "medidor" in c or "meter" in c:
                medidor_col = c
                break

    # Índice mensual
    df["mes_dt"] = pd.to_datetime(dict(year=df["año"], month=df["mes"], day=1))
    return df, consumo_col, medidor_col


def forecast_monthly(monthly: pd.Series, h: int) -> pd.Series:
    """
    Pronóstico mensual a h meses: Holt-Winters si hay ≥24 meses e instalado statsmodels,
    de lo contrario ingenuo estacional (mismo mes del año anterior) con relleno por media.
    """
    monthly = monthly.asfreq("MS")
    if HAS_HW and len(monthly.dropna()) >= 24:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = ExponentialSmoothing(
                monthly, trend="add", seasonal="add",
                seasonal_periods=12, initialization_method="estimated"
            )
            fit = model.fit(optimized=True)
            fc = fit.forecast(h)
    else:
        future_index = pd.date_range(monthly.index[-1] + pd.offsets.MonthBegin(), periods=h, freq="MS")
        if len(monthly) >= 24:
            fc = monthly.shift(12).reindex(future_index).fillna(monthly.mean())
        else:
            fc = pd.Series(np.repeat(monthly.mean(), h), index=future_index)
    return fc


def build_kpis(monthly: pd.Series, fc: pd.Series) -> pd.DataFrame:
    """ KPIs básicos para planificación. """
    kpis: Dict[str, float | str] = {}
    kpis["consumo_total_historico_kwh"] = float(monthly.sum()) if len(monthly) else 0.0
    kpis["promedio_mensual_kwh"] = float(monthly.mean()) if len(monthly) else 0.0
    kpis["max_pico_historico_kwh"] = float(monthly.max()) if len(monthly) else 0.0
    kpis["mes_pico_historico"] = str(monthly.idxmax().date()) if len(monthly) else ""
    kpis["pronostico_max_12m_kwh"] = float(fc.max()) if len(fc) else 0.0
    kpis["mes_pico_pronosticado"] = str(fc.idxmax().date()) if len(fc) else ""
    return pd.DataFrame([kpis])


def detect_anomalies(
    df: pd.DataFrame,
    consumo_col: str,
    medidor_col: Optional[str],
    focus_months: int = DEFAULT_FOCUS_MONTHS
) -> pd.DataFrame:
    """
    Reglas:
      1) Cambios abruptos: caída >50% o suba >200% vs mes previo.
      2) Z-score robusto vs mediana móvil 12 meses (|z| ≥ 4).
    Devuelve últimos 'focus_months' meses para accionar.
    """
    if medidor_col is None:
        return pd.DataFrame(columns=["medidor", "mes_dt", "criterio", "valor", "kwh", "kwh_prev"])

    tmp = df[[medidor_col, "mes_dt", consumo_col]].rename(columns={medidor_col: "medidor", consumo_col: "kwh"})
    tmp = tmp.sort_values(["medidor", "mes_dt"])

    # Cambios abruptos
    tmp["kwh_prev"] = tmp.groupby("medidor")["kwh"].shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        tmp["pct_change"] = (tmp["kwh"] - tmp["kwh_prev"]) / tmp["kwh_prev"]
    abrupt = tmp[(tmp["kwh_prev"] > 0) & ((tmp["pct_change"] <= -0.5) | (tmp["pct_change"] >= 2.0))].copy()
    abrupt["criterio"] = "cambio_abrupto"
    abrupt["valor"] = abrupt["pct_change"]

    # Z robusto (ventana 12)
    tmp["med_12"] = tmp.groupby("medidor")["kwh"].transform(lambda s: s.rolling(12, min_periods=6).median())
    tmp["mad_12"] = tmp.groupby("medidor")["kwh"].transform(
        lambda s: s.rolling(12, min_periods=6).apply(lambda x: np.median(np.abs(x - np.median(x))), raw=True)
    )
    denom = (1.4826 * tmp["mad_12"].replace(0, np.nan))
    tmp["robust_z"] = (tmp["kwh"] - tmp["med_12"]) / denom
    robust = tmp[np.abs(tmp["robust_z"]) >= 4].copy()
    robust["criterio"] = "robust_z"
    robust["valor"] = robust["robust_z"]

    anomalies = pd.concat(
        [abrupt[["medidor", "mes_dt", "criterio", "valor", "kwh", "kwh_prev"]],
         robust[["medidor", "mes_dt", "criterio", "valor", "kwh", "kwh_prev"]]],
        ignore_index=True
    ).drop_duplicates()

    if anomalies.empty:
        return anomalies

    last_month = tmp["mes_dt"].max()
    window_start = last_month - pd.DateOffset(months=focus_months - 1)
    return anomalies[anomalies["mes_dt"] >= window_start].sort_values(["mes_dt", "medidor"])


def run_pipeline(
    input_path: Path,
    outdir: Path,
    horizon: int = DEFAULT_HORIZON,
    focus_months: int = DEFAULT_FOCUS_MONTHS,
    do_plot: bool = True
) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)

    df, consumo_col, medidor_col = load_and_normalize(input_path)
    monthly = df.groupby("mes_dt", as_index=True)[consumo_col].sum().sort_index()
    fc = forecast_monthly(monthly, h=horizon)

    forecast_df = pd.DataFrame({
        "fecha": list(monthly.index) + list(fc.index),
        "tipo": ["histórico"] * len(monthly) + ["pronóstico"] * len(fc),
        "kwh": list(monthly.values) + list(fc.values)
    })
    kpis_df = build_kpis(monthly, fc)
    anomalies_df = detect_anomalies(df, consumo_col, medidor_col, focus_months=focus_months)

    # Guardar salidas
    kpis_path = outdir / "kpis_consumo.csv"
    pron_path = outdir / "pronostico_consumo_12m.csv"
    anom_path = outdir / "posibles_anomalias_recientes.csv"
    kpis_df.to_csv(kpis_path, index=False)
    forecast_df.to_csv(pron_path, index=False)
    anomalies_df.to_csv(anom_path, index=False)

    plot_path = None
    if do_plot:
        plt.figure()
        plt.plot(monthly.index, monthly.values, label="Histórico")
        plt.plot(fc.index, fc.values, label="Pronóstico 12m")
        plt.legend()
        plt.title("Consumo total mensual (kWh) - Histórico y Pronóstico 12 meses")
        plt.xlabel("Mes")
        plt.ylabel("kWh")
        plot_path = outdir / "consumo_pronostico_12m.png"
        plt.savefig(plot_path, bbox_inches="tight")

    return {
        "kpis": str(kpis_path),
        "pronostico": str(pron_path),
        "anomalias": str(anom_path),
        "grafico": str(plot_path) if plot_path else None
    }


def build_argparser() -> argparse.ArgumentParser:
   
    p = argparse.ArgumentParser(
        description="Pronóstico de demanda y detección de anomalías por medidor."
    )
    p.add_argument("--input", default=DEFAULT_INPUT, help="Ruta al CSV de entrada")
    p.add_argument("--outdir", default=DEFAULT_OUTDIR, help="Directorio de salida")
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON, help="Meses a pronosticar (default 12)")
    p.add_argument("--focus_months", type=int, default=DEFAULT_FOCUS_MONTHS, help="Meses recientes para anomalías (default 6)")
    p.add_argument("--plot", action="store_true", help="Si se incluye, genera PNG del histórico + pronóstico")
    return p

def main() -> None:
    ap = build_argparser()
    args = ap.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)
    do_plot = bool(args.plot) or True  # por defecto, genera el gráfico

    try:
        results = run_pipeline(
            input_path=input_path,
            outdir=outdir,
            horizon=args.horizon,
            focus_months=args.focus_months,
            do_plot=do_plot
        )

        print("\n✅ Datos procesados con éxito.\n")
        print("Archivos generados:")
        for k, v in results.items():
            if v:
                print(f"- {k}: {v}")
        print("\n📂 Los resultados fueron guardados correctamente en:", outdir)

    except FileNotFoundError:
        print(f"\n❌ Error: No se pudo leer el archivo CSV.\nVerificá la ruta:\n  {input_path}")
    except Exception as e:
        print("\n❌ Error inesperado al procesar los datos:")
        print(str(e))


if __name__ == "__main__":
    main()
