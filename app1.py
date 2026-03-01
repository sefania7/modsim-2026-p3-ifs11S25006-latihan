import streamlit as st
import simpy
import random
import pandas as pd
import time
from datetime import datetime, timedelta
import plotly.express as px

# =====================================================
# CONFIG PAGE
# =====================================================
st.set_page_config(
    page_title="Smart Piket Simulation",
    page_icon="🍱",
    layout="wide"
)

# =====================================================
# PREMIUM UI STYLE
# =====================================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    font-family: 'Segoe UI', sans-serif;
}

h1 {
    color: white;
    text-align: center;
    font-size: 45px;
    text-shadow: 2px 2px 15px rgba(0,0,0,0.4);
}

div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(10px);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0px 6px 20px rgba(0,0,0,0.15);
    transition: 0.3s;
}

div[data-testid="metric-container"]:hover {
    transform: scale(1.05);
}

.stButton>button {
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    color: white;
    border-radius: 30px;
    height: 50px;
    font-size: 18px;
    font-weight: bold;
    border: none;
    transition: 0.3s;
}

.stButton>button:hover {
    background: linear-gradient(90deg, #0072ff, #00c6ff);
    transform: scale(1.05);
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================
st.markdown("""
<h1>🍱 SMART PIKET SIMULATION</h1>
<p style='text-align:center;color:white;font-size:18px;'>
⏰ 07.00–07.15 | 👥 7 Mahasiswa | 🎯 Target 180 Ompreng
</p>
""", unsafe_allow_html=True)

st.divider()

# =====================================================
# PARAMETER
# =====================================================
START_TIME = datetime(2024, 1, 1, 7, 0, 0)
SIMULATION_DURATION = 15
TOTAL_OMPRENG = 180

PETUGAS_LAUK = 3
PETUGAS_ANGKUT = 2
PETUGAS_NASI = 2

random.seed(42)

# =====================================================
# SIMULATION MODEL
# =====================================================
class SistemPiket:
    def __init__(self, env):
        self.env = env
        self.lauk = simpy.Resource(env, PETUGAS_LAUK)
        self.angkut = simpy.Resource(env, PETUGAS_ANGKUT)
        self.nasi = simpy.Resource(env, PETUGAS_NASI)

        self.antrian_lauk = simpy.Store(env)
        self.antrian_meja = simpy.Store(env)
        self.selesai = []

    def isi_lauk(self):
        while self.env.now < SIMULATION_DURATION:
            with self.lauk.request() as req:
                yield req
                yield self.env.timeout(random.uniform(0.5, 1.0))
                if len(self.selesai) + len(self.antrian_lauk.items) < TOTAL_OMPRENG:
                    yield self.antrian_lauk.put(self.env.now)

    def angkut_batch(self):
        while self.env.now < SIMULATION_DURATION:
            if len(self.antrian_lauk.items) >= 4:
                batch = random.randint(4, 7)
                batch = min(batch, len(self.antrian_lauk.items))
                with self.angkut.request() as req:
                    yield req
                    yield self.env.timeout(random.uniform(0.33, 1.0))
                    for _ in range(batch):
                        waktu = yield self.antrian_lauk.get()
                        yield self.antrian_meja.put(waktu)
            else:
                yield self.env.timeout(0.1)

    def isi_nasi(self):
        while self.env.now < SIMULATION_DURATION:
            if len(self.antrian_meja.items) > 0:
                waktu_mulai = yield self.antrian_meja.get()
                with self.nasi.request() as req:
                    yield req
                    yield self.env.timeout(random.uniform(0.5, 1.0))
                    selesai = self.env.now
                    if selesai <= SIMULATION_DURATION:
                        self.selesai.append({
                            "Mulai (menit)": round(waktu_mulai, 2),
                            "Selesai (menit)": round(selesai, 2),
                            "Durasi (menit)": round(selesai - waktu_mulai, 2),
                            "Jam Selesai": START_TIME + timedelta(minutes=selesai)
                        })
            else:
                yield self.env.timeout(0.1)


def run_simulasi():
    env = simpy.Environment()
    sistem = SistemPiket(env)

    for _ in range(PETUGAS_LAUK):
        env.process(sistem.isi_lauk())
    for _ in range(PETUGAS_ANGKUT):
        env.process(sistem.angkut_batch())
    for _ in range(PETUGAS_NASI):
        env.process(sistem.isi_nasi())

    env.run(until=SIMULATION_DURATION)
    return pd.DataFrame(sistem.selesai)

# =====================================================
# RUN BUTTON
# =====================================================
if st.button("🚀 Jalankan Simulasi", use_container_width=True):

    progress = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress.progress(i + 1)

    df = run_simulasi()

    st.success("Simulasi selesai dalam 15 menit operasional ✅")

    c1, c2, c3 = st.columns(3)
    c1.metric("Target Ompreng", TOTAL_OMPRENG)
    c2.metric("Ompreng Selesai", len(df))
    c3.metric("Rata-rata Durasi",
              f"{df['Durasi (menit)'].mean():.2f} menit" if len(df)>0 else "0")

    st.divider()

    # =========================
    # ANALISIS
    # =========================
    st.subheader("🧠 Analisis Performa Sistem")

    if len(df) > 0:
        rata = df["Durasi (menit)"].mean()
        maksimum = df["Durasi (menit)"].max()

        if rata > 3:
            st.warning("⚠️ Sistem mulai overload!")
        else:
            st.success("✅ Sistem stabil dan efisien.")

        st.write(f"📊 Rata-rata durasi: {rata:.2f} menit")
        st.write(f"⏱ Durasi terlama: {maksimum:.2f} menit")

    # =========================
    # BOTTLENECK
    # =========================
    st.subheader("🚨 Deteksi Bottleneck")

    sisa = TOTAL_OMPRENG - len(df)

    if sisa > 50:
        st.error("🔥 Bottleneck kemungkinan di tahap LAUK atau ANGKUT!")
    elif sisa > 20:
        st.warning("⚠️ Ada potensi bottleneck kecil.")
    else:
        st.success("🚀 Tidak terdeteksi bottleneck signifikan.")

    st.divider()

    # =========================
    # HISTOGRAM
    # =========================
    fig1 = px.histogram(
        df,
        x="Durasi (menit)",
        title="Distribusi Waktu Proses",
        color_discrete_sequence=["#00c853"]
    )
    st.plotly_chart(fig1, use_container_width=True)

    # =========================
    # TIMELINE (LINE + MARKER)
    # =========================
    fig2 = px.line(
        df.sort_values("Selesai (menit)"),
        x="Selesai (menit)",
        y="Durasi (menit)",
        title="📈 Timeline Penyelesaian Ompreng",
        markers=True
    )

    fig2.update_traces(
        line=dict(width=4),
        marker=dict(size=8)
    )

    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Waktu Selesai (menit)",
        yaxis_title="Durasi Proses (menit)",
        title_x=0.5
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📄 Data Detail")
    st.dataframe(df, use_container_width=True)

else:
    st.info("Klik tombol untuk menjalankan simulasi 15 menit (07.00–07.15)")