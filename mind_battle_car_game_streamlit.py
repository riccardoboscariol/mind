import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt
import threading
import time
import serial
import serial.tools.list_ports

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
    try:
        random_bits = list(map(int, response.text.strip().split()))
        if len(random_bits) != num_bits:
            raise ValueError("Number of bits received does not match the requested number.")
    except Exception as e:
        st.error(f"Errore durante l'ottenimento dei bit casuali da random.org: {e}")
        random_bits = []
    return random_bits

# Funzione per calcolare l'entropia
def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

st.title("Mind Battle Car Game")

num_bits = 10000
random_numbers_1 = []
random_numbers_2 = []
sub_block_size = 5000

# Variabili globali per la gestione dei thread e della seriale
ser = None
reading_thread = None
running = False

# Funzione per listare le porte seriali
def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

# Funzione per iniziare la lettura dalla porta seriale
def start_reading():
    global ser, running, reading_thread
    if not running:
        ports = list_serial_ports()
        if not ports:
            st.warning("Nessuna porta seriale trovata, utilizzerò random.org per generare i numeri casuali.")
            generate_random_numbers_from_random_org()
            return

        # Assumi che la prima porta sia TrueRNG
        true_rng_port = ports[0]

        try:
            ser = serial.Serial(true_rng_port, 9600, timeout=1)
        except serial.SerialException as e:
            st.error(f"Impossibile aprire la porta seriale: {e}")
            return

        running = True
        reading_thread = threading.Thread(target=read_random_numbers_from_truerng)
        reading_thread.start()

# Funzione per fermare la lettura dalla porta seriale
def stop_reading():
    global running, ser
    running = False
    if ser:
        ser.close()

# Funzione per leggere i numeri casuali dalla porta seriale
def read_random_numbers_from_truerng():
    global running, ser, random_numbers_1, random_numbers_2
    while running:
        try:
            random_bytes = ser.read(2 * sub_block_size // 8)  # Leggi i byte necessari per 10000 bit (1250 byte)
            random_bits = [int(bit) for byte in random_bytes for bit in format(byte, '08b')]

            random_bits_1 = random_bits[:sub_block_size]
            random_bits_2 = random_bits[sub_block_size:]

            random_numbers_1.extend(random_bits_1)
            random_numbers_2.extend(random_bits_2)

            time.sleep(0.1)  # Pausa di 0.1 secondi
        except Exception as e:
            print(f"Errore durante la lettura: {str(e)}")
            running = False
            break

# Funzione per generare numeri casuali da random.org
def generate_random_numbers_from_random_org():
    global random_numbers_1, random_numbers_2
    random_bits = get_random_bits_from_random_org(num_bits)
    if random_bits:
        random_bits_1 = random_bits[:num_bits//2]
        random_bits_2 = random_bits[num_bits//2:]

        random_numbers_1.extend(random_bits_1)
        random_numbers_2.extend(random_bits_2)

# Funzione per il download dei dati
def download_data():
    data_1 = pd.DataFrame({'Auto Verde': random_numbers_1})
    data_2 = pd.DataFrame({'Auto Rossa': random_numbers_2})
    data_1.to_csv('auto_verde_dati.csv', index=False)
    data_2.to_csv('auto_rossa_dati.csv', index=False)
    st.success("I dati sono stati scaricati come CSV")

# Pulsanti di controllo
if st.button("Avvia Generazione"):
    start_reading()

if st.button("Blocca Generazione"):
    stop_reading()

if st.button("Scarica Dati"):
    download_data()

# Visualizzazione delle statistiche
if random_numbers_1 and random_numbers_2:
    entropy_1 = calculate_entropy(random_numbers_1)
    entropy_2 = calculate_entropy(random_numbers_2)

    st.write(f"Entropia Auto Verde: {entropy_1}")
    st.write(f"Entropia Auto Rossa: {entropy_2}")

    u_stat, p_value_mw = mannwhitneyu(random_numbers_1, random_numbers_2, alternative='two-sided')
    st.write(f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value_mw:.4f}")

    total_moves_1 = sum(random_numbers_1)
    total_moves_2 = sum(random_numbers_2)
    binom_p_value_moves = binomtest(total_moves_1, len(random_numbers_1), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}")

    binom_p_value_1 = binomtest(np.sum(random_numbers_1), len(random_numbers_1), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}")

    binom_p_value_2 = binomtest(np.sum(random_numbers_2), len(random_numbers_2), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}")

    st.write(f"Posizione Auto Verde: {total_moves_1 / 100.0}")
    st.write(f"Posizione Auto Rossa: {total_moves_2 / 100.0}")

    # Plot dei dati
    df = pd.DataFrame({
        "Auto Verde": random_numbers_1,
        "Auto Rossa": random_numbers_2
    })

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df["Auto Verde"], bins=30, alpha=0.5, color='green', edgecolor='k', label='Auto Verde')
    ax.hist(df["Auto Rossa"], bins=30, alpha=0.5, color='red', edgecolor='k', label='Auto Rossa')
    ax.set_title('Distribuzione della Rarità degli Slot')
    ax.set_xlabel('Rarità')
    ax.set_ylabel('Frequenza')
    ax.legend()
    st.pyplot(fig)


