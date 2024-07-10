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

# Costante per il numero massimo di bit per richiesta
MAX_BITS_PER_REQUEST = 10000

# Variabili globali per la gestione dei thread e della seriale
ser = None
running = False

# Funzione per ottenere i bit casuali da random.org con gestione dei limiti
def get_random_bits_from_random_org(num_bits):
    random_bits = []
    try:
        while num_bits > 0:
            bits_to_request = min(num_bits, MAX_BITS_PER_REQUEST)
            url = "https://www.random.org/integers/"
            params = {
                "num": bits_to_request,
                "min": 0,
                "max": 1,
                "col": 1,
                "base": 10,
                "format": "plain",
                "rnd": "new"
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                try:
                    random_bits_chunk = list(map(int, response.text.strip().split()))
                    if len(random_bits_chunk) != bits_to_request:
                        raise ValueError("Number of bits received does not match the requested number.")
                    random_bits.extend(random_bits_chunk)
                    num_bits -= bits_to_request
                except Exception as e:
                    st.error(f"Errore durante l'ottenimento dei bit casuali da random.org: {e}")
                    break
            else:
                st.warning(f"Errore durante l'ottenimento dei bit casuali da random.org: {response.text}")
                break
    except Exception as e:
        st.error(f"Errore durante l'ottenimento dei bit casuali da random.org: {e}")
    return random_bits

# Funzione per ottenere i bit casuali localmente
def get_random_bits_locally(num_bits):
    return np.random.randint(0, 2, size=num_bits).tolist()

# Funzione per calcolare l'entropia
def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

def list_serial_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

# Funzione per iniziare la lettura dalla porta seriale
def start_reading(use_random_org, sub_block_size, car_positions, random_numbers):
    global running
    if use_random_org:
        read_random_numbers_from_random_org_continuously(sub_block_size, car_positions, random_numbers)
    else:
        ports = list_serial_ports()
        if not ports:
            st.warning("Nessuna porta seriale trovata, utilizzerò un generatore locale per generare i numeri casuali.")
            read_random_numbers_locally_continuously(sub_block_size, car_positions, random_numbers)
        else:
            true_rng_port = ports[0]
            st.write(f"Utilizzo della porta seriale: {true_rng_port}")
            ser = serial.Serial(true_rng_port, 9600, timeout=1)
            read_random_numbers_from_truerng_continuously(ser, sub_block_size, car_positions, random_numbers)

# Funzione per leggere i numeri casuali dalla porta seriale in modo continuo
def read_random_numbers_from_truerng_continuously(ser, sub_block_size, car_positions, random_numbers):
    global running
    while running:
        random_bytes = ser.read(2 * sub_block_size // 8)  # Leggi i byte necessari per 10000 bit (1250 byte)
        random_bits = [int(bit) for byte in random_bytes for bit in format(byte, '08b')]

        random_bits_1 = random_bits[:sub_block_size]
        random_bits_2 = random_bits[sub_block_size:]

        random_numbers['1'].extend(random_bits_1)
        random_numbers['2'].extend(random_bits_2)

        update_positions(random_bits_1, random_bits_2, car_positions)
        time.sleep(1)

# Funzione per leggere i numeri casuali da random.org in modo continuo
def read_random_numbers_from_random_org_continuously(sub_block_size, car_positions, random_numbers):
    global running
    while running:
        random_bits = get_random_bits_from_random_org(2 * sub_block_size)
        if not random_bits:
            random_bits = get_random_bits_locally(2 * sub_block_size)
        random_bits_1 = random_bits[:sub_block_size]
        random_bits_2 = random_bits[sub_block_size:]

        random_numbers['1'].extend(random_bits_1)
        random_numbers['2'].extend(random_bits_2)

        update_positions(random_bits_1, random_bits_2, car_positions)
        time.sleep(1)

# Funzione per leggere i numeri casuali localmente in modo continuo
def read_random_numbers_locally_continuously(sub_block_size, car_positions, random_numbers):
    global running
    while running:
        random_bits = get_random_bits_locally(2 * sub_block_size)
        random_bits_1 = random_bits[:sub_block_size]
        random_bits_2 = random_bits[sub_block_size:]

        random_numbers['1'].extend(random_bits_1)
        random_numbers['2'].extend(random_bits_2)

        update_positions(random_bits_1, random_bits_2, car_positions)
        time.sleep(1)

# Funzione per aggiornare le posizioni delle auto
def update_positions(bits1, bits2, car_positions):
    entropy_1 = calculate_entropy(bits1)
    entropy_2 = calculate_entropy(bits2)

    car_positions['car1'] += 10 * (1 - entropy_1)  # Muovi l'auto verde in base all'entropia
    car_positions['car2'] += 10 * (1 - entropy_2)  # Muovi l'auto rossa in base all'entropia

    if car_positions['car1'] > 1000:
        car_positions['car1'] = 1000
    if car_positions['car2'] > 1000:
        car_positions['car2'] = 1000

    # Aggiornamento automatico della visualizzazione
    st.experimental_rerun()

# Imposta l'interfaccia Streamlit
st.title("Mind Battle Car Game")

num_bits = 10000
sub_block_size = 5000
car_positions = {'car1': 0, 'car2': 0}
random_numbers = {'1': [], '2': []}
use_random_org = False

# Pulsanti di controllo
if st.button("Avvia Generazione"):
    ports = list_serial_ports()
    if not ports:
        st.warning("Nessuna porta seriale trovata, utilizzerò random.org per generare i numeri casuali.")
        use_random_org = True
    running = True
    threading.Thread(target=start_reading, args=(use_random_org, sub_block_size, car_positions, random_numbers)).start()

if st.button("Blocca Generazione"):
    running = False

if st.button("Scarica Dati"):
    data_1 = pd.DataFrame({'Auto Verde': random_numbers['1']})
    data_2 = pd.DataFrame({'Auto Rossa': random_numbers['2']})
    data_1.to_csv('auto_verde_dati.csv', index=False)
    data_2.to_csv('auto_rossa_dati.csv', index=False)
    st.success("I dati sono stati scaricati come CSV")

# Visualizzazione delle posizioni delle auto
st.write(f"Posizione Auto Verde: {car_positions['car1']}")
st.write(f"Posizione Auto Rossa: {car_positions['car2']}")

fig, ax = plt.subplots()
ax.plot([car_positions['car1']], [1], 'go', label='Auto Verde')
ax.plot([car_positions['car2']], [2], 'ro', label='Auto Rossa')
ax.set_yticks([1, 2])
ax.set_yticklabels(['Auto Verde', 'Auto Rossa'])
ax.set_xlim([0, 1000])
ax.set_ylim([0, 3])
ax.legend()
st.pyplot(fig)

# Visualizzazione delle statistiche
if random_numbers['1'] and random_numbers['2']:
    entropy_1 = calculate_entropy(random_numbers['1'])
    entropy_2 = calculate_entropy(random_numbers['2'])

    st.write(f"Entropia Auto Verde: {entropy_1}")
    st.write(f"Entropia Auto Rossa: {entropy_2}")

    u_stat, p_value_mw = mannwhitneyu(random_numbers['1'], random_numbers['2'], alternative='two-sided')
    st.write(f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value_mw:.4f}")

    total_moves_1 = sum(random_numbers['1'])
    total_moves_2 = sum(random_numbers['2'])
    binom_p_value_moves = binomtest(total_moves_1, len(random_numbers['1']), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}")

    binom_p_value_1 = binomtest(np.sum(random_numbers['1']), len(random_numbers['1']), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}")

    binom_p_value_2 = binomtest(np.sum(random_numbers['2']), len(random_numbers['2']), alternative='two-sided').pvalue
    st.write(f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}")

    st.write(f"Posizione Auto Verde: {total_moves_1 / 100.0}")
    st.write(f"Posizione Auto Rossa: {total_moves_2 / 100.0}")

    # Plot dei dati
    df = pd.DataFrame({
        "Auto Verde": random_numbers['1'],
        "Auto Rossa": random_numbers['2']
    })

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df["Auto Verde"], bins=30, alpha=0.5, color='green', edgecolor='k', label='Auto Verde')
    ax.hist(df["Auto Rossa"], bins=30, alpha=0.5, color='red', edgecolor='k', label='Auto Rossa')
    ax.set_title('Distribuzione della Rarità degli Slot')
    ax.set_xlabel('Rarità')
    ax.set_ylabel('Frequenza')
    ax.legend()
    st.pyplot(fig)
