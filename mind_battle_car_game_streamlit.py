import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import base64
import io
import os
from rdoclient import RandomOrgClient
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configura Google Sheets
def configure_google_sheets(json_keyfile_name, sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile_name, scope)
    client = gspread.authorize(credentials)
    sheet = client.open(sheet_name).sheet1  # Apri il primo foglio
    return sheet

# Salva i dati su Google Sheets
def save_to_google_sheets(sheet, data):
    sheet.append_row(data)

# Genera bit casuali
def get_random_bits_from_random_org(num_bits, client=None):
    """Ottieni bit casuali da random.org o utilizza un generatore pseudocasuale locale."""
    try:
        if client:
            # Usa RANDOM.ORG
            random_bits = client.generate_integers(num_bits, 0, 1)
            return random_bits, True
        else:
            # Usa un generatore pseudocasuale locale
            random_bits = get_local_random_bits(num_bits)
            return random_bits, False
    except Exception:
        # In caso di errore, utilizza un generatore pseudocasuale locale
        random_bits = get_local_random_bits(num_bits)
        return random_bits, False

def get_local_random_bits(num_bits):
    """Genera bit pseudocasuali localmente."""
    return list(np.random.randint(0, 2, size=num_bits))

def calculate_entropy(bits):
    """Calcola l'entropia usando la formula di Shannon."""
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

def move_car(car_pos, distance):
    """Muovi l'auto di una certa distanza."""
    car_pos += distance
    if car_pos > 900:  # Accorcia la pista per lasciare spazio alla bandiera
        car_pos = 900
    return car_pos

def image_to_base64(image):
    """Converti un'immagine in base64."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Funzione principale
def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")

    # Usa il nome corretto del file JSON delle credenziali
    json_keyfile_name = "client_secret.json"  # Modifica con il nome esatto del file JSON
    sheet_name = "test"  # Nome del foglio di lavoro su Google Sheets
    sheet = configure_google_sheets(json_keyfile_name, sheet_name)

    if "language" not in st.session_state:
        st.session_state.language = "Italiano"

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

    if "warned_random_org" not in st.session_state:
        st.session_state.warned_random_org = False

    if "player_choice" not in st.session_state:
        st.session_state.player_choice = None
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
    if "show_retry_popup" not in st.session_state:
        st.session_state.show_retry_popup = False

    st.sidebar.title("Menu")
    start_button = st.sidebar.button(
        "Avvia Gara", key="start_button", disabled=st.session_state.player_choice is None or st.session_state.running
    )
    stop_button = st.sidebar.button("Blocca Gara", key="stop_button")

    st.session_state.api_key = st.sidebar.text_input(
        "Inserisci API Key per random.org", key="api_key_input", value=st.session_state.api_key, type="password"
    )

    client = None
    if st.session_state.api_key:
        client = RandomOrgClient(st.session_state.api_key)

    reset_button = st.sidebar.button("Resetta Gioco", key="reset_button")
    move_multiplier = st.sidebar.slider(
        "Moltiplicatore di Movimento", min_value=1, max_value=100, value=50, key="move_multiplier"
    )

    st.write("Scegli il tuo bit per la macchina verde:")

    col1, col2 = st.columns([1, 1])
    with col1:
        button1 = st.button(
            "Scegli 1", key="button1", use_container_width=True, help="Scegli il bit 1"
        )
    with col2:
        button0 = st.button(
            "Scegli 0", key="button0", use_container_width=True, help="Scegli il bit 0"
        )

    if button1:
        st.session_state.player_choice = 1

    if button0:
        st.session_state.player_choice = 0

    def check_winner():
        """Verifica se c'è un vincitore."""
        if st.session_state.car_pos >= 900:  # Accorcia la pista per lasciare spazio alla bandiera
            return "Rossa"
        elif st.session_state.car2_pos >= 900:  # Accorcia la pista per lasciare spazio alla bandiera
            return "Verde"
        return None

    def end_race(winner):
        """Termina la gara e mostra il vincitore."""
        st.session_state.running = False
        st.session_state.show_retry_popup = True
        st.success(f"Vince l'auto {winner}, complimenti!")
        
        # Salva i dati su Google Sheets
        end_time = time.time()
        duration = end_time - st.session_state.car_start_time
        api_key_used = "Sì" if st.session_state.api_key else "No"
        data = [
            "riccardoboscariol97@gmail.com",  # Recapito
            "Verde",  # Macchina scelta
            st.session_state.player_choice,  # Bit scelto
            st.session_state.move_multiplier,  # Moltiplicatore di movimento
            winner,  # Esito
            round(duration, 2),  # Durata
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Data e ora
            api_key_used  # Chiave API random.org usata?
        ]
        save_to_google_sheets(sheet, data)

    if start_button and st.session_state.player_choice is not None:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()
        st.session_state.show_retry_popup = False

    if stop_button:
        st.session_state.running = False

    if st.session_state.running:
        start_time = time.time()

        # Ottieni numeri casuali da random.org
        random_bits_1, random_org_success_1 = get_random_bits_from_random_org(1000, client)
        random_bits_2, random_org_success_2 = get_random_bits_from_random_org(1000, client)

        if not random_org_success_1 and not random_org_success_2:
            if not st.session_state.warned_random_org:
                st.session_state.warned_random_org = True

        st.session_state.random_numbers_1.extend(random_bits_1)
        st.session_state.random_numbers_2.extend(random_bits_2)

        entropy_score_1 = calculate_entropy(random_bits_1)
        entropy_score_2 = calculate_entropy(random_bits_2)

        percentile_5_1 = np.percentile(st.session_state.random_numbers_1, 5)
        percentile_5_2 = np.percentile(st.session_state.random_numbers_2, 5)

        count_1 = sum(random_bits_1)
        count_0 = len(random_bits_1) - count_1

        if entropy_score_1 < percentile_5_1:
            if st.session_state.player_choice == 1 and count_1 > count_0:
                st.session_state.car2_pos = move_car(
                    st.session_state.car2_pos,
                    move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)),
                )
                st.session_state.car1_moves += 1
            elif st.session_state.player_choice == 0 and count_0 > count_1:
                st.session_state.car2_pos = move_car(
                    st.session_state.car2_pos,
                    move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)),
                )
                st.session_state.car1_moves += 1

        if entropy_score_2 < percentile_5_2:
            if st.session_state.player_choice == 1 and count_0 > count_1:
                st.session_state.car_pos = move_car(
                    st.session_state.car_pos,
                    move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)),
                )
                st.session_state.car2_moves += 1
            elif st.session_state.player_choice == 0 and count_1 > count_0:
                st.session_state.car_pos = move_car(
                    st.session_state.car_pos,
                    move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)),
                )
                st.session_state.car2_moves += 1

        # Verifica se c'è un vincitore
        winner = check_winner()
        if winner:
            end_race(winner)

        time_elapsed = time.time() - start_time
        time.sleep(max(0.5 - time_elapsed, 0))

    if reset_button:
        st.session_state.car_pos = 50
        st.session_state.car2_pos = 50
        st.session_state.car1_moves = 0
        st.session_state.car2_moves = 0
        st.session_state.random_numbers_1 = []
        st.session_state.random_numbers_2 = []
        st.session_state.running = False

if __name__ == "__main__":
    main()

