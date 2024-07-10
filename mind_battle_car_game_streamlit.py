import streamlit as st
import time
import numpy as np
import pandas as pd
import requests
import io
from PIL import Image
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt

# Funzioni per ottenere bit casuali da random.org o localmente
def get_random_bits(num_bits):
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
    except requests.RequestException:
        st.warning("Errore durante l'accesso a random.org. Generazione di numeri casuali in locale.")
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
    st.title("Generatore di Anomalie Casuali Binari")
    
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
    use_random_org = True

    car_placeholder = st.empty()
    car2_placeholder = st.empty()
    car_progress = st.empty()
    car2_progress = st.empty()

    if start_button:
        running = True
        car_start_time = time.time()
        
        while running:
            random_bits_1 = get_random_bits(500)
            random_bits_2 = get_random_bits(500)
            
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
                car_pos = move_car(car
