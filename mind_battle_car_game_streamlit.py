import tkinter as tk
from tkinter import messagebox
import threading
import time
import serial
import serial.tools.list_ports
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation

class RandomNumberGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mind Battle Car Game")

        self.ser = None
        self.reading_thread = None
        self.running = False
        self.visualizing = False
        self.random_numbers_1 = []
        self.random_numbers_2 = []
        self.sub_block_size = 5000  # Numero di cifre binarie per sub-blocco (5000 per ogni auto)
        self.data_for_excel_1 = []  # Lista per memorizzare i dati per l'Excel condizione 1
        self.data_for_excel_2 = []  # Lista per memorizzare i dati per l'Excel condizione 2
        self.data_for_condition_1 = []  # Lista per memorizzare i dati della condizione 1
        self.data_for_condition_2 = []  # Lista per memorizzare i dati della condizione 2
        self.car1_moves = 0
        self.car2_moves = 0
        self.anomalies = []  # Lista per memorizzare le anomalie riscontrate

        self.car_x = 50
        self.car2_x = 50
        self.car1_laps = 0
        self.car2_laps = 0

        self.setup_ui()

    def setup_ui(self):
        self.root.configure(bg='black')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        frame = tk.Frame(self.root, bg='black')
        frame.pack(pady=20)

        self.start_button = tk.Button(frame, text="Avvia Generazione", command=self.start_reading, font=("Calibri", 12), bg='black', fg='white')
        self.start_button.pack(side=tk.LEFT, padx=10)

        self.stop_button = tk.Button(frame, text="Blocca Generazione", command=self.stop_reading, font=("Calibri", 12), bg='black', fg='white')
        self.stop_button.pack(side=tk.LEFT, padx=10)

        self.download_button = tk.Button(frame, text="Scarica Dati", command=self.download_data, font=("Calibri", 12), bg='black', fg='white')
        self.download_button.pack(side=tk.LEFT, padx=10)

        self.fig, self.ax = plt.subplots(figsize=(8, 4))  # Adjusted figure size
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(padx=10, pady=10)

        # Adding car movement canvas
        self.car_canvas = tk.Canvas(self.root, width=1000, height=200, bg='black')  # Reduced height
        self.car_canvas.pack(pady=20)
        self.car_image = tk.PhotoImage(file="car.png").subsample(7, 7)  # Reduce the size of the car image
        self.car = self.car_canvas.create_image(self.car_x, 50, anchor=tk.CENTER, image=self.car_image)  # 1/4 height
        self.car2_image = tk.PhotoImage(file="car2.png").subsample(7, 7)  # Reduce the size of the car2 image
        self.car2 = self.car_canvas.create_image(self.car2_x, 150, anchor=tk.CENTER, image=self.car2_image)  # 3/4 height

        self.car1_laps_label = tk.Label(self.root, text=f"Auto Verde: Giri = {self.car1_laps}", font=("Calibri", 12), fg='white', bg='black')
        self.car1_laps_label.pack(pady=5)

        self.car2_laps_label = tk.Label(self.root, text=f"Auto Rossa: Giri = {self.car2_laps}", font=("Calibri", 12), fg='white', bg='black')
        self.car2_laps_label.pack(pady=5)

        self.stats_label = tk.Label(self.root, text="", font=("Calibri", 12), fg='white', bg='black')
        self.stats_label.pack(pady=5)

        self.anomalies_label = tk.Label(self.root, text="", font=("Calibri", 12), fg='white', bg='black')
        self.anomalies_label.pack(pady=5)

    def list_serial_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def start_reading(self):
        if not self.running:
            ports = self.list_serial_ports()
            if not ports:
                messagebox.showerror("Errore", "Nessuna porta seriale trovata")
                return

            # Assumi che la prima porta sia TrueRNG
            true_rng_port = ports[0]

            try:
                self.ser = serial.Serial(true_rng_port, 9600, timeout=1)
            except serial.SerialException as e:
                messagebox.showerror("Errore", f"Impossibile aprire la porta seriale: {e}")
                return

            self.running = True
            self.reading_thread = threading.Thread(target=self.read_random_numbers)
            self.reading_thread.daemon = True
            self.reading_thread.start()
            self.start_visualization()  # Start the visualization when reading starts

    def stop_reading(self):
        self.running = False
        if self.ser:
            self.ser.close()

    def read_random_numbers(self):
        while self.running:
            try:
                random_bytes = self.ser.read(2 * self.sub_block_size // 8)  # Leggi i byte necessari per 10000 bit (1250 byte)
                random_bits = [int(bit) for byte in random_bytes for bit in format(byte, '08b')]
                
                random_bits_1 = random_bits[:self.sub_block_size]
                random_bits_2 = random_bits[self.sub_block_size:]

                self.random_numbers_1.extend(random_bits_1)
                self.random_numbers_2.extend(random_bits_2)

                # Aggiungi i sub-blocchi ai dati per l'Excel
                self.data_for_excel_1.extend(random_bits_1)
                self.data_for_excel_2.extend(random_bits_2)

                # Calcola l'entropia utilizzando il metodo NIST
                entropy_score_1 = self.calculate_entropy(random_bits_1)
                entropy_score_2 = self.calculate_entropy(random_bits_2)

                # Aggiungi l'entropia ai dati per visualizzare la distribuzione
                self.data_for_condition_1.append(entropy_score_1)
                self.data_for_condition_2.append(entropy_score_2)

                # Muovi le auto sullo schermo solo se l'entropia è inferiore al 5%
                if len(self.data_for_condition_1 + self.data_for_condition_2) > 0:
                    percentile_5_1 = np.percentile(self.data_for_condition_1, 5)
                    percentile_5_2 = np.percentile(self.data_for_condition_2, 5)
                    if entropy_score_1 < percentile_5_1:
                        rarity_percentile = 1 - (entropy_score_1 / percentile_5_1)
                        self.move_car(1 + (10 * rarity_percentile))  # Move car 1 by calculated distance
                    if entropy_score_2 < percentile_5_2:
                        rarity_percentile = 1 - (entropy_score_2 / percentile_5_2)
                        self.move_car2(1 + (10 * rarity_percentile))  # Move car 2 by calculated distance

                self.update_stats()
                time.sleep(0.1)  # Pausa di 0.1 secondi
            except Exception as e:
                print(f"Errore durante la lettura: {str(e)}\n")
                self.running = False
                break

    def calculate_entropy(self, bits):
        n = len(bits)
        counts = np.bincount(bits, minlength=2)
        p = counts / n
        p = p[np.nonzero(p)]
        entropy = -np.sum(p * np.log2(p))
        return entropy

    def move_car(self, distance):
        self.car_x += distance
        if self.car_x >= 1000:
            self.car_x = 50
            self.car1_laps += 1
        self.car_canvas.coords(self.car, self.car_x, 50)
        self.car1_laps_label.config(text=f"Auto Verde: Giri = {self.car1_laps}")

    def move_car2(self, distance):
        self.car2_x += distance
        if self.car2_x >= 1000:
            self.car2_x = 50
            self.car2_laps += 1
        self.car_canvas.coords(self.car2, self.car2_x, 150)
        self.car2_laps_label.config(text=f"Auto Rossa: Giri = {self.car2_laps}")

    def update_stats(self):
        # Aggiorna le statistiche e visualizza le anomalie
        if len(self.random_numbers_1) >= self.sub_block_size and len(self.random_numbers_2) >= self.sub_block_size:
            u_stat, p_value_mw = mannwhitneyu(self.random_numbers_1[-self.sub_block_size:], self.random_numbers_2[-self.sub_block_size:], alternative='two-sided')
            total_moves_1 = sum(self.random_numbers_1[-self.sub_block_size:])
            total_moves_2 = sum(self.random_numbers_2[-self.sub_block_size:])
            binom_p_value_moves = binomtest(total_moves_1, self.sub_block_size, alternative='two-sided').pvalue
            binom_p_value_1 = binomtest(np.sum(self.random_numbers_1[-self.sub_block_size:]), self.sub_block_size, alternative='two-sided').pvalue
            binom_p_value_2 = binomtest(np.sum(self.random_numbers_2[-self.sub_block_size:]), self.sub_block_size, alternative='two-sided').pvalue

            stats_text = (f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value_mw:.4f}\n"
                          f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}\n"
                          f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}\n"
                          f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}\n"
                          f"Posizione Auto Verde: {total_moves_1 / 100.0}\n"
                          f"Posizione Auto Rossa: {total_moves_2 / 100.0}")
            
            self.stats_label.config(text=stats_text)

            # Controlla per le anomalie
            if p_value_mw < 0.05 or binom_p_value_moves < 0.05 or binom_p_value_1 < 0.05 or binom_p_value_2 < 0.05:
                self.anomalies.append(stats_text)
                self.anomalies_label.config(text="Anomalie riscontrate:\n" + "\n".join(self.anomalies[-5:]))

    def download_data(self):
        data_1 = pd.DataFrame({'Auto Verde': self.random_numbers_1})
        data_2 = pd.DataFrame({'Auto Rossa': self.random_numbers_2})
        data_1.to_excel('auto_verde_dati.xlsx', index=False)
        data_2.to_excel('auto_rossa_dati.xlsx', index=False)
        messagebox.showinfo("Scarica Dati", "I dati sono stati scaricati come Excel")

    def start_visualization(self):
        if not self.visualizing:
            self.visualizing = True
            self.animation = FuncAnimation(self.fig, self.update_plot, interval=1000)
            self.canvas.draw()

    def update_plot(self, frame):
        self.ax.clear()
        self.ax.hist(self.data_for_condition_1, bins=30, alpha=0.5, color='green', edgecolor='k', label='Auto Verde')
        self.ax.hist(self.data_for_condition_2, bins=30, alpha=0.5, color='red', edgecolor='k', label='Auto Rossa')
        self.ax.set_title('Distribuzione della Rarità degli Slot')
        self.ax.set_xlabel('Rarità')
        self.ax.set_ylabel('Frequenza')
        self.ax.legend()
        self.canvas.draw()

    def on_closing(self):
        self.stop_reading()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = RandomNumberGeneratorApp(root)
    root.mainloop()
