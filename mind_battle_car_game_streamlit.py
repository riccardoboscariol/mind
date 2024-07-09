import streamlit as st
import requests
import pandas as pd
import numpy as np
import serial
import serial.tools.list_ports
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt

# Funzione per ottenere i bit casuali da random.org
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
    response = requests.get(url, params=params)
    random_bits = list(map(int, response.text.strip().split()))
    return random_bits

# Funzione per ottenere i bit casuali dalla chiavetta TrueRNG3
def get_random_bits_from_truerng(num_bits, port):
    ser = serial.Serial(port, 9600, timeout=1)
    random_bytes = ser.read(num_bits // 8)
    ser.close()
    random_bits = [int(bit) for byte in random_bytes for bit in format(byte, '08b')]
    return random_bits

# Funzione per calcolare l'entropia
def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

# Funzione per elencare le porte seriali
def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

st.title("Generatore di Anomalie Casuali Binari")

num_bits = 10000
use_truerng = False

# Controlla se la chiavetta TrueRNG3 è disponibile
ports = list_serial_ports()
if ports:
    use_truerng = True
    true_rng_port = ports[0]
    st.warning("Chiavetta TrueRNG3 rilevata. Verrà utilizzata per generare i numeri casuali.")
else:
    st.warning("Attenzione! Non è stata rilevata la chiavetta 'TrueRNG3' indispensabile per il compito.\nVerrà quindi utilizzato random.org per generare i numeri casuali.")

if st.button("Avvia Generazione"):
    if use_truerng:
        random_bits = get_random_bits_from_truerng(num_bits, true_rng_port)
    else:
        random_bits = get_random_bits_from_random_org(num_bits)
    
    random_bits_1 = random_bits[:num_bits//2]
    random_bits_2 = random_bits[num_bits//2:]

    entropy_1 = calculate_entropy(random_bits_1)
    entropy_2 = calculate_entropy(random_bits_2)

    st.write(f"Entropia Condizione 1: {entropy_1}")
    st.write(f"Entropia Condizione 2: {entropy_2}")

    u_stat, p_value_mw = mannwhitneyu(random_bits_1, random_bits_2, alternative='two-sided')
    st.write(f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value_mw:.4f}")

    total_moves_1 = sum(random_bits_1)
    total_moves_2 = sum(random_bits_2)
    binom_p_value_moves = binomtest(total_moves_1, num_bits//2, alternative='two-sided').pvalue
    st.write(f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}")

    binom_p_value_1 = binomtest(np.sum(random_bits_1), len(random_bits_1), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}")

    binom_p_value_2 = binomtest(np.sum(random_bits_2), len(random_bits_2), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}")

    st.write(f"Posizione Auto Verde: {total_moves_1 / 100.0}")
    st.write(f"Posizione Auto Rossa: {total_moves_2 / 100.0}")

    df = pd.DataFrame({
        "Condizione 1": random_bits_1,
        "Condizione 2": random_bits_2
    })

    csv = df.to_csv(index=False)
    st.download_button(
        label="Scarica Dati",
        data=csv,
        file_name='random_numbers.csv',
        mime='text/csv',
    )

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df["Condizione 1"], bins=30, alpha=0.5, color='red', edgecolor='k', label='Condizione 1')
    ax.hist(df["Condizione 2"], bins=30, alpha=0.5, color='green', edgecolor='k', label='Condizione 2')
    ax.set_title('Distribuzione della Rarità degli Slot')
    ax.set_xlabel('Rarità')
    ax.set_ylabel('Frequenza')
    ax.legend()
    st.pyplot(fig)
