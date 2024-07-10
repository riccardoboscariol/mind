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
    
    start_button = st.button("Avvia Generazione")
    stop_button = st.button("Blocca Generazione")
    download_button = st.button("Scarica Dati")
    download_graph_button = st.button("Scarica Grafico")
    stats_button = st.button("Mostra Analisi Statistiche")
    reset_button = st.button("Resetta Gioco")
    
    car_pos = 50
    car2_pos = 50
    car1_moves = 0
    car2_moves = 0
    random_numbers_1 = []
    random_numbers_2 = []
    data_for_excel_1 = []
    data_for_excel_2 = []
    data_for_condition_1 = []
    data_for_condition_2 = []
    car_start_time = None
    best_time = None
    running = False

    car_placeholder = st.empty()
    car2_placeholder = st.empty()
    car_progress = st.empty()
    car2_progress = st.empty()

    if start_button:
        running = True
        car_start_time = time.time()
        
        while running:
            random_bits_1 = get_random_bits_from_random_org(5000)
            random_bits_2 = get_random_bits_from_random_org(5000)
            
            random_numbers_1.extend(random_bits_1)
            random_numbers_2.extend(random_bits_2)
            
            data_for_excel_1.append(random_bits_1)
            data_for_excel_2.append(random_bits_2)
            
            entropy_score_1 = calculate_entropy(random_bits_1)
            entropy_score_2 = calculate_entropy(random_bits_2)
            
            data_for_condition_1.append(entropy_score_1)
            data_for_condition_2.append(entropy_score_2)
            
            percentile_5_1 = np.percentile(data_for_condition_1, 5)
            percentile_5_2 = np.percentile(data_for_condition_2, 5)
            
            if entropy_score_1 < percentile_5_1:
                rarity_percentile = 1 - (entropy_score_1 / percentile_5_1)
                car_pos = move_car(car_pos, 6 * (1 + (10 * rarity_percentile)))
                car1_moves += 1
            
            if entropy_score_2 < percentile_5_2:
                rarity_percentile = 1 - (entropy_score_2 / percentile_5_2)
                car2_pos = move_car(car2_pos, 6 * (1 + (10 * rarity_percentile)))
                car2_moves += 1
            
            car_image = Image.open("car.png").resize((70, 70))
            car2_image = Image.open("car2.png").resize((70, 70))
            
            car_placeholder.image(car_image, caption="Auto Verde", width=70)
            car_progress.progress(int(car_pos / 10))
            car2_placeholder.image(car2_image, caption="Auto Rossa", width=70)
            car2_progress.progress(int(car2_pos / 10))
            
            time.sleep(0.1)

            if stop_button:
                running = False
                break
        
        end_time = time.time()
        time_taken = end_time - car_start_time
        st.write(f"Tempo impiegato: {time_taken:.2f} secondi")
        if best_time is None or time_taken < best_time:
            best_time = time_taken
            st.success(f"Nuovo Record! Tempo: {time_taken:.2f} secondi")
        else:
            st.info(f"Tempo impiegato: {time_taken:.2f} secondi")

    if download_button:
        df = pd.DataFrame({
            "Condizione 1": [''.join(map(str, row)) for row in data_for_excel_1],
            "Condizione 2": [''.join(map(str, row)) for row in data_for_excel_2]
        })
        df.to_excel("random_numbers.xlsx", index=False)
        st.success("Dati salvati in random_numbers.xlsx")
    
    if download_graph_button:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(data_for_condition_1, bins=30, alpha=0.5, color='red', edgecolor='k')
        ax.hist(data_for_condition_2, bins=30, alpha=0.5, color='green', edgecolor='k')
        ax.set_title('Distribuzione della Rarità degli Slot')
        ax.set_xlabel('Rarità')
        ax.set_ylabel('Frequenza')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        st.download_button(label="Scarica Grafico", data=buf, file_name="rarity_distribution.png", mime="image/png")
    
    if stats_button:
        if data_for_condition_1 and data_for_condition_2:
            u_stat, p_value = mannwhitneyu(data_for_condition_1, data_for_condition_2, alternative='two-sided')
            mann_whitney_text = f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value:.4f}"
        else:
            mann_whitney_text = "Mann-Whitney U test: Dati insufficienti"

        total_moves = car1_moves + car2_moves
        if total_moves > 0:
            binom_p_value_moves = binomtest(car1_moves, total_moves, alternative='two-sided').pvalue
            binom_text_moves = f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}"
        else:
            binom_p_value_moves = 1.0
            binom_text_moves = "Test Binomiale (numero di spostamenti): Dati insufficienti"

        binom_p_value_1 = binomtest(np.sum(random_numbers_1), len(random_numbers_1), alternative='two-sided').pvalue
        binom_text_1 = f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}"

        binom_p_value_2 = binomtest(np.sum(random_numbers_2), len(random_numbers_2), alternative='two-sided').pvalue
        binom_text_2 = f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}"

        stats_text = mann_whitney_text + "\n" + binom_text_moves + "\n" + binom_text_1 + "\n" + binom_text_2
        st.write(stats_text)
    
    if reset_button:
        car_pos = 50
        car2_pos = 50
        car1_moves = 0
        car2_moves = 0
        data_for_excel_1 = []
        data_for_excel_2 = []
        data_for_condition_1 = []
        data_for_condition_2 = []
        random_numbers_1 = []
        random_numbers_2 = []
        st.write("Gioco resettato!")

if __name__ == "__main__":
    main()

