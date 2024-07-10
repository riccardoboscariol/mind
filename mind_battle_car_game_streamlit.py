import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt
import io
import requests

# Funzione per ottenere bit casuali da random.org
def get_random_bits_from_random_org(num_bits):
    url = "https://www.random.org/integers/"
    params = {
        "num": num_bits,
        "min": 0,
        "max": 1,
        "col": 1,
        "base": 10,
        "format": "plain",
        "rnd": "new"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        random_bits = list(map(int, response.text.strip().split()))
        return random_bits
    except requests.RequestException as e:
        if not st.session_state.get('random_org_warning_shown', False):
            st.session_state['random_org_warning_shown'] = True
            st.warning("Errore durante l'accesso a random.org: {}. Utilizzando la generazione locale.".format(e))
        return get_random_bits(num_bits)

# Funzione per ottenere bit casuali localmente
def get_random_bits(num_bits):
    return np.random.randint(0, 2, num_bits).tolist()

# Funzione per calcolare l'entropia
def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

# Funzione per spostare l'auto
def move_car(car_pos, distance):
    car_pos += distance
    if car_pos > 1000:  # Se l'auto esce dallo schermo, riportala all'inizio
        car_pos = 1000
    return car_pos

# Funzione principale
def main():
    st.title("Mind Battle Car Game")

    # CSS per personalizzare i colori degli slider
    st.markdown("""
        <style>
        .stSlider > div > div > div > div > div {
            background: red;
        }
        .stSlider > div > div > div > div > div:nth-child(2) {
            background: green;
        }
        </style>
        """, unsafe_allow_html=True)

    start_button = st.button("Avvia Generazione", key="start")
    stop_button = st.button("Blocca Generazione", key="stop")
    download_button = st.button("Scarica Dati", key="download_data")
    download_graph_button = st.button("Scarica Grafico", key="download_graph")
    stats_button = st.button("Mostra Analisi Statistiche", key="stats")
    reset_button = st.button("Resetta Gioco", key="reset")
    
    if "car_pos" not in st.session_state:
        st.session_state.car_pos = 50
    if "car2_pos" not in st.session_state:
        st.session_state.car2_pos = 50
    if "car1_moves" not in st.session_state:
        st.session_state.car1_moves = 0
    if "car2_moves" not in st.session_state:
        st.session_state.car2_moves = 0
    if "random_numbers_1" not in st.session_state:
        st.session_state.random_numbers_1 = []
    if "random_numbers_2" not in st.session_state:
        st.session_state.random_numbers_2 = []
    if "data_for_excel_1" not in st.session_state:
        st.session_state.data_for_excel_1 = []
    if "data_for_excel_2" not in st.session_state:
        st.session_state.data_for_excel_2 = []
    if "data_for_condition_1" not in st.session_state:
        st.session_state.data_for_condition_1 = []
    if "data_for_condition_2" not in st.session_state:
        st.session_state.data_for_condition_2 = []
    if "car_start_time" not in st.session_state:
        st.session_state.car_start_time = None
    if "best_time" not in st.session_state:
        st.session_state.best_time = None
    if "running" not in st.session_state:
        st.session_state.running = False
    if "widget_key_counter" not in st.session_state:
        st.session_state.widget_key_counter = 0

    car_placeholder = st.empty()
    car2_placeholder = st.empty()
    car_progress = st.empty()
    car2_progress = st.empty()

    car_image = Image.open("car.png").resize((140, 140))
    car2_image = Image.open("car2.png").resize((140, 140))
    car_placeholder.image(car_image, width=140)
    car2_placeholder.image(car2_image, width=140)

    if start_button:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()

    if stop_button:
        st.session_state.running = False

    while st.session_state.running:
        random_bits_1 = get_random_bits_from_random_org(5000)
        random_bits_2 = get_random_bits_from_random_org(5000)
        
        st.session_state.random_numbers_1.extend(random_bits_1)
        st.session_state.random_numbers_2.extend(random_bits_2)
        
        st.session_state.data_for_excel_1.append(random_bits_1)
        st.session_state.data_for_excel_2.append(random_bits_2)
        
        entropy_score_1 = calculate_entropy(random_bits_1)
        entropy_score_2 = calculate_entropy(random_bits_2)
        
        st.session_state.data_for_condition_1.append(entropy_score_1)
        st.session_state.data_for_condition_2.append(entropy_score_2)
        
        percentile_5_1 = np.percentile(st.session_state.data_for_condition_1, 5)
        percentile_5_2 = np.percentile(st.session_state.data_for_condition_2, 5)
        
        if entropy_score_1 < percentile_5_1:
            rarity_percentile = 1 - (entropy_score_1 / percentile_5_1)
            st.session_state.car_pos = move_car(st.session_state.car_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car1_moves += 1
        
        if entropy_score_2 < percentile_5_2:
            rarity_percentile = 1 - (entropy_score_2 / percentile_5_2)
            st.session_state.car2_pos = move_car(st.session_state.car2_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car2_moves += 1
        
        st.session_state.widget_key_counter += 1  # Incrementa il contatore per ogni iterazione
        car_progress.slider("Posizione Auto Rossa", min_value=0, max_value=1000, value=int(st.session_state.car_pos), key=f"slider1_{st.session_state.widget_key_counter}")
        car2_progress.slider("Posizione Auto Verde", min_value=0, max_value=1000, value=int(st.session_state.car2_pos), key=f"slider2_{st.session_state.widget_key_counter}")

        time.sleep(0.1)

    if download_button:
        df = pd.DataFrame({
            "Condizione 1": [''.join(map(str, row)) for row in st.session_state.data_for_excel_1],
            "Condizione 2": [''.join(map(str, row)) for row in st.session_state.data_for_excel_2]
        })
        try:
            df.to_excel("random_numbers.xlsx", index=False)
            with open("random_numbers.xlsx", "rb") as file:
                st.download_button(
                    label="Scarica Dati",
                    data=file,
                    file_name="random_numbers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except ImportError:
            st.error("openpyxl non è installato. Installa openpyxl per scaricare i dati in formato Excel.")

    if download_graph_button:
        fig, ax = plt.subplots(figsize=(8, 4))
        if st.session_state.data_for_condition_1:
            ax.hist(st.session_state.data_for_condition_1, bins=30, alpha=0.5, color='red', edgecolor='k')
        if st.session_state.data_for_condition_2:
            ax.hist(st.session_state.data_for_condition_2, bins=30, alpha=0.5, color='green', edgecolor='k')
        ax.set_title('Distribuzione della Rarità degli Slot')
        ax.set_xlabel('Rarità')
        ax.set_ylabel('Frequenza')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        st.download_button(label="Scarica Grafico", data=buf, file_name="rarity_distribution.png", mime="image/png")
    
    if stats_button:
        if st.session_state.data_for_condition_1 and st.session_state.data_for_condition_2:
            u_stat, p_value = mannwhitneyu(st.session_state.data_for_condition_1, st.session_state.data_for_condition_2, alternative='two-sided')
            mann_whitney_text = f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value:.4f}"
        else:
            mann_whitney_text = "Mann-Whitney U test: Dati insufficienti"

        total_moves = st.session_state.car1_moves + st.session_state.car2_moves
        if total_moves > 0:
            binom_p_value_moves = binomtest(st.session_state.car1_moves, total_moves, alternative='two-sided').pvalue
            binom_text_moves = f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}"
        else:
            binom_text_moves = "Test Binomiale (numero di spostamenti): Dati insufficienti"

        if st.session_state.random_numbers_1:
            binom_p_value_1 = binomtest(np.sum(st.session_state.random_numbers_1), len(st.session_state.random_numbers_1), alternative='two-sided').pvalue
            binom_text_1 = f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}"
        else:
            binom_text_1 = "Test Binomiale (cifre auto verde): Dati insufficienti"

        if st.session_state.random_numbers_2:
            binom_p_value_2 = binomtest(np.sum(st.session_state.random_numbers_2), len(st.session_state.random_numbers_2), alternative='two-sided').pvalue
            binom_text_2 = f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}"
        else:
            binom_text_2 = "Test Binomiale (cifre auto rossa): Dati insufficienti"

        stats_text = mann_whitney_text + "\n" + binom_text_moves + "\n" + binom_text_1 + "\n" + binom_text_2
        st.write(stats_text)
    
    if reset_button:
        st.session_state.car_pos = 50
        st.session_state.car2_pos = 50
        st.session_state.car1_moves = 0
        st.session_state.car2_moves = 0
        st.session_state.data_for_excel_1 = []
        st.session_state.data_for_excel_2 = []
        st.session_state.data_for_condition_1 = []
        st.session_state.data_for_condition_2 = []
        st.session_state.random_numbers_1 = []
        st.session_state.random_numbers_2 = []
        st.session_state.widget_key_counter = 0  # Reset del contatore di chiavi
        st.write("Gioco resettato!")
        st.session_state['random_org_warning_shown'] = False  # Reset dell'avviso di errore per random.org

if __name__ == "__main__":
    main()
