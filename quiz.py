import requests
import json
import re
import tkinter as tk
from tkinter import simpledialog, messagebox
import random  
import socket
import hashlib
import ctypes
import threading

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyWVfGFF22VGe0O6t6IzeAmpPnqA5oKfm2lKndhPeTastKOaUORq-MMbYrYpBcHZr75/exec"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Rhyx-RINPq6qX8TL1l42LpYuk7oVy5QMdQaUiY2ciAE/gviz/tq?tqx=out:json"
DATA_URL = "https://docs.google.com/spreadsheets/d/1Q2UHyfAliAWxbd4p-jSrVfSjxbzz5s23MwGYtyN_3rg/gviz/tq?tqx=out:json"
def encrypt_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except:
        return "Unknown"
    
def check_ip_registered(ip, username):
    try:
        response = requests.get(DATA_URL)
        match = re.search(r"google.visualization.Query.setResponse\((.*)\);", response.text)
        if match:
            data = json.loads(match.group(1))
            rows = data["table"]["rows"]
            for row in rows:
                if len(row["c"]) > 2:
                    sheet_username = row["c"][0]["v"].strip() 
                    sheet_ip = row["c"][2]["v"].strip()
                    print(f"Checking: {sheet_username} vs {username} and {sheet_ip} vs {ip}") 
                    if sheet_username.lower() == username.lower() and sheet_ip == ip:
                        return True
    except Exception as e:
        print("Error checking IP:", e)
    return False

def get_username_by_ip(ip):
    try:
        response = requests.get(DATA_URL) 
        match = re.search(r"google.visualization.Query.setResponse\((.*)\);", response.text)
        
        if match:
            data = json.loads(match.group(1)) 
            rows = data["table"]["rows"]
            
            for row in rows:
                if len(row["c"]) > 2 and row["c"][2] and "v" in row["c"][2]:
                    registered_ip = row["c"][2]["v"].strip()
                    if registered_ip == ip.strip():
                        return row["c"][0]["v"]
    except Exception as e:
        print("Error retrieving username by IP:", e)
    return None

def register(username, password, ip):
    encrypted_password = encrypt_password(password)
    try:
        response = requests.post(WEB_APP_URL, json={
            "action": "register",
            "username": username,
            "password": encrypted_password,
            "ip": ip
        })
        return response.text.strip() == "Registration successful"
    except Exception as e:
        messagebox.showerror("Error", f"Gagal terhubung ke server!\n{e}")
        return False

def login(username, password, ip):
    encrypted_password = encrypt_password(password)
    try:
        response = requests.post(WEB_APP_URL, json={
            "action": "login",
            "username": username,
            "password": encrypted_password,
            "ip": ip
        })
        return response.text.strip() == "Login successful"
    except Exception as e:
        messagebox.showerror("Error", f"Gagal terhubung ke server!\n{e}")
        return False

def authenticate():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Get the user's IP
    user_ip = get_user_ip()

    # Check if the IP is registered and retrieve the associated username
    username = get_username_by_ip(user_ip)
    
    # If a username is found for the IP, auto login
    if username:
        return username, ""

    # If no username is found, prompt the user to log in or register
    while True:
        choice = simpledialog.askstring("Welcome", "Type 'login' to log in, or 'register' to create an account:")
        if choice and choice.lower() == "register":
            username = simpledialog.askstring("Register", "Enter your username:").lower()
            password = simpledialog.askstring("Register", "Choose a password:", show="*")
            if username and password:
                if register(username, password, user_ip):
                    return username, password
                else:
                    messagebox.showerror("Error", "Registration failed. Try again.")
        elif choice and choice.lower() == "login":
            username = simpledialog.askstring("Login", "Enter your username:").lower()
            password = simpledialog.askstring("Login", "Enter your password:", show="*")
            if username and password:
                if login(username, password, user_ip):
                    return username, password
                else:
                    messagebox.showerror("Error", "Invalid username or password. Try again.")
        else:
            messagebox.showerror("Error", "Invalid choice. Please enter 'login' or 'register'.")

def fetch_questions():
    try:
        response = requests.get(GOOGLE_SHEET_URL)
        match = re.search(r"google.visualization.Query.setResponse\((.*)\);", response.text)
        if match:
            data = json.loads(match.group(1))
            rows = data["table"]["rows"]
            questions = []
            
            for row in rows:
                if len(row["c"]) < 9 or not row["c"][0]["v"]:  
                    continue  

                question_text = row["c"][0]["v"]
                options = [cell["v"] for cell in row["c"][1:7] if cell]  
                correct_answer = row["c"][8]["v"] if len(row["c"]) > 8 else ""

                random.shuffle(options)
                correct_index = options.index(correct_answer) if correct_answer in options else -1

                questions.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "correct_index": correct_index
                })

            return questions
    except Exception as e:
        print("Error fetching questions:", e)
    return []

def send_quiz_data(username, question, selected_answer, correct_answer, score):
    def send():
        try:
            payload = {
                "action": "submit_quiz",
                "username": username,
                "question": question,
                "selected_option": selected_answer,
                "correct_answer": correct_answer,
                "correct": selected_answer == correct_answer,
                "points": 10 if selected_answer == correct_answer else 0,
                "total_score": score
            }
            print("Payload yang dikirim:", json.dumps(payload, indent=2)) 
            response = requests.post(WEB_APP_URL, json=payload, headers={"Content-Type": "application/json"})
            print("Response dari server:", response.text)
        except Exception as e:
            print("Gagal mengirim data:", e)

    thread = threading.Thread(target=send)
    thread.start()

class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Online Quiz")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        self.root.configure(bg="#f4f4f4")
        self.root.iconbitmap("icon.ico")

        self.font_main = ("Helvetica", 14)
        self.font_button = ("Helvetica", 12, "bold")

        self.username, self.password = authenticate()
        if not self.username:
            self.root.destroy()
            return

        self.questions = fetch_questions()
        if not self.questions:
            
            tk.Label(root, text="No questions available!", fg="red", font=("Arial", 14), bg="#f4f4f4").pack(pady=20)
            return

        self.total_questions = len(self.questions)
        self.total_score = 0
        self.current_question_index = 0

        self.score_label = tk.Label(root, text=f"Score: 0", font=self.font_main, bg="#f3f4f6", fg="#3498db")
        self.score_label.pack(pady=10)

        self.question_label = tk.Label(root, text="Loading...", wraplength=400, font=("Arial", 14, "bold"), bg="#f4f4f4")
        self.question_label.pack(pady=20)

        self.buttons = []
        for i in range(6):
            btn = tk.Button(root, text=f"Option {i+1}", font=("Arial", 12), bg="#3498db", fg="white",
                            activebackground="#2980b9", command=lambda i=i: self.select_answer(i))
            btn.pack(fill="x", padx=50, pady=5)
            self.buttons.append(btn)

        self.load_question()

    def load_question(self):
        if self.current_question_index < self.total_questions:
            question_data = self.questions[self.current_question_index]
            self.question_label.config(text=question_data["question"])

            for i, btn in enumerate(self.buttons):
                if i < len(question_data["options"]):
                    btn.config(text=question_data["options"][i], state="normal")
                else:
                    btn.config(text="", state="disabled")
        else:
            self.show_result()

    def select_answer(self, index):
        self.buttons[index].config(state=tk.DISABLED)
        question_data = self.questions[self.current_question_index]
        selected_answer = question_data["options"][index]
        correct_answer = question_data["correct_answer"]

        if index == question_data["correct_index"]:
            self.total_score += 10
            self.score_label.config(text=f"Score: {self.total_score}")
            self.buttons[index].config(bg="green") 
        else:
            self.buttons[index].config(bg="red") 

        send_quiz_data(self.username, question_data["question"], selected_answer, correct_answer, self.total_score)
        self.root.after(1000, self.next_question)  

    def next_question(self):
        for btn in self.buttons:
            btn.config(bg="#2980b9", state="normal")

        self.current_question_index += 1
        self.load_question()

    def show_result(self):
        self.question_label.config(text=f"Quiz Selesai! Skor: {self.total_score}/{self.total_questions * 10}", font=("Helvetica", 18, "bold"))
        self.score_label.config(text=f"Skor Akhir: {self.total_score}/{self.total_questions * 10}")

        for btn in self.buttons:
            btn.config(state="disabled")

        # Hapus tombol retry sebelumnya jika ada
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Button) and widget.cget("text") == "Retry":
                widget.destroy()

        retry_button = tk.Button(self.root, text="Retry", font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                                activebackground="#1e8449", command=self.restart_quiz)
        retry_button.pack(pady=10)
    def restart_quiz(self):
        self.total_score = 0
        self.current_question_index = 0
        self.score_label.config(text="Score: 0")

        for btn in self.buttons:
            btn.config(state="normal")

        self.load_question()


class MainMenu:
    def __init__(self, root, username):
        self.root = root
        self.root.title("Main Menu")
        self.root.iconbitmap("icon.ico")
        self.root.geometry("600x400")  
        self.root.minsize(600, 400) 
        self.username = username

        self.font_button = ("Arial", 16, "bold")
        
        self.root.configure(bg="#f4f4f4")

        tk.Label(root, text=f"Welcome, {self.username}!", font=("Arial", 18, "bold"), bg="#f4f4f4").pack(pady=30)

        tk.Button(root, text="Start Quiz", command=self.open_quiz, font=self.font_button, bg="#3498db", fg="white",
                  activebackground="#2980b9", width=20, height=2).pack(pady=20)
        
        tk.Button(root, text="Pets", command=self.open_pets, font=self.font_button, bg="#3498db", fg="white",
                  activebackground="#2980b9", width=20, height=2).pack(pady=20)
        
        tk.Button(root, text="Exit", command=self.root.quit, font=self.font_button, bg="#e74c3c", fg="white",
                  activebackground="#c0392b", width=20, height=2).pack(pady=20)
    
    def open_quiz(self):
        self.root.destroy()
        open_quiz(self.username)

    def open_pets(self):
        messagebox.showinfo("Pets", "Pets feature coming soon!")

def open_main_menu(username):
    root = tk.Tk()
    MainMenu(root, username)
    root.mainloop()

def open_quiz(username):
    root = tk.Tk()
    QuizApp(root)
    root.mainloop()

if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("quiz.app")
    username, password = authenticate()
    root = tk.Tk()
    app = MainMenu(root, username)
    root.mainloop()