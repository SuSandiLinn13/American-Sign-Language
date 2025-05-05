import os
import time
import threading
import cv2
from ultralytics import YOLO
import tkinter as tk
from tkinter import Text, ttk
from PIL import Image, ImageTk, ImageDraw
from utilities import save_as_text, text_to_speech

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'asl_model.pt')
THEME_PATH = os.path.join(os.path.dirname(__file__), 'themes', 'forest-dark.tcl')
AUDIO_PATH = os.path.join(os.path.dirname(__file__), 'audio', 'output.wav')

class ASLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ASL TTS App")
        self.root.resizable(False, False)

        # Keybindings
        root.bind("<Alt-c>", lambda event: self.clear_text())  # Alt + C to clear text
        root.bind("<Alt-s>", lambda event: self.start_camera())  # Alt + S to start camera
        root.bind("<Alt-p>", lambda event: self.stop_camera())  # Alt + P to stop camera
        root.bind("<Alt-r>", lambda event: self.read_aloud())  # Alt + R to read aloud
        root.bind("<Alt-t>", lambda event: self.save_text())  # Alt + T to save as .txt
        
        # Apply Forest Theme
        root.tk.call('source', THEME_PATH)
        ttk.Style().theme_use('forest-dark')
        
        # Tracking variables
        self.detected_text = ""
        self.current_sentence = ""
        self.sign_start_time = None
        self.stable_duration = 2.0
        self.conf = 0.5
        self.speech_rate = 1.0

        # Load the YOLO model
        self.model = None
        threading.Thread(target=self.load_model,daemon = True).start()

        # Main Layout
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(expand=False, fill='both')
        
        # Left Panel (Video Feed)
        self.left_panel = ttk.Frame(self.main_frame,padding= (10,10,5,10))
        self.left_panel.pack(side=tk.LEFT, fill='y')
        
        self.video_card = ttk.LabelFrame(self.left_panel, text='Capture')
        self.video_card.pack(fill='both', expand=True)
        
        self.panel1 = ttk.Label(self.video_card)
        self.panel1.pack(padx=5, pady=(5,0))
        
        # Placeholder Image
        self.placeholder_img = Image.new('RGB', (640, 480), color=(20, 20, 20))
        draw = ImageDraw.Draw(self.placeholder_img)
        draw.text((280, 220), "Camera is OFF", fill=(255, 255, 255))
        self.placeholder_photo = ImageTk.PhotoImage(self.placeholder_img)
        self.panel1.configure(image=self.placeholder_photo)
        
        # Buttons
        self.button_frame = ttk.Frame(self.video_card)
        self.button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(self.button_frame, text="Start", style='Accent.TButton', command=self.start_camera)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(self.button_frame, text="Stop", command=self.stop_camera)
        self.stop_button.pack(side=tk.RIGHT, padx=5)

        # Settings frame
        self.setting_frame = ttk.LabelFrame(self.left_panel, text="Settings", padding=10)
        self.setting_frame.pack(fill="both")
        self.setting_frame.columnconfigure(index=0,weight=1)
        self.setting_frame.columnconfigure(index=1,weight=1)
        self.setting_frame.rowconfigure(index=0,weight=1)
        self.setting_frame.rowconfigure(index=1,weight=1)
        self.setting_frame.rowconfigure(index=2, weight=1)

        self.conf_slider_label = ttk.Label(self.setting_frame, text="Confidence: ")
        self.conf_slider_label.grid(row=0, column=0, sticky='nes', padx=5, pady=5)

        self.conf_slider = ttk.Scale(self.setting_frame, from_= 0.0, to=1.0, length=125, command=self.on_conf_changed)
        self.conf_slider.set(self.conf)
        self.conf_slider.grid(row=0, column=1,sticky='nws', padx=5, pady=5)

        self.timeout_slider_label = ttk.Label(self.setting_frame, text="Timeout: ")
        self.timeout_slider_label.grid(row=1, column=0, sticky='nes', padx=5, pady=5)

        self.timeout_slider = ttk.Scale(self.setting_frame, from_= 0.5, to=5.0, length=125, command=self.on_timer_changed)
        self.timeout_slider.set(self.stable_duration)
        self.timeout_slider.grid(row=1, column=1,sticky='nws', padx=5, pady=5)

        self.tts_speed_label = ttk.Label(self.setting_frame, text="TTS Speed: ")
        self.tts_speed_label.grid(row=2, column=0, sticky='nes', padx=5, pady=5)

        self.tts_speed_slider = ttk.Scale(self.setting_frame, from_= 0.5, to=2.0, length=125, command=self.on_tts_speed_changed)
        self.tts_speed_slider.set(self.speech_rate)
        self.tts_speed_slider.grid(row=2, column=1,sticky='nws', padx=5, pady=5)
        
        # Right Panel (Text Display)
        self.panel2 = ttk.Frame(self.main_frame, padding=(5,10,10,10))
        self.panel2.pack(side=tk.RIGHT, fill='y')
        
        self.text_card = ttk.LabelFrame(self.panel2, text='Text')
        self.text_card.pack(fill='both', expand=True)
        
        self.text_panel = Text(self.text_card, width=60)
        self.text_panel.pack(padx=5, pady=(5,0), fill='both', expand=True)
        
        # Button frame
        self.button_frame2 = ttk.Frame(self.text_card)
        self.button_frame2.pack(pady=10)
        
        self.save_button = ttk.Button(self.button_frame2, text="Save as .txt", command=self.save_text)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(self.button_frame2, text="Clear", command=self.clear_text)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.read_button = ttk.Button(self.button_frame2, text="Read Aloud", command=self.read_aloud)
        self.read_button.pack(side=tk.RIGHT, padx=5)
        
        self.cap = None  # Webcam variable

    def load_model(self):
        self.model = YOLO(MODEL_PATH)

    def on_conf_changed(self, value):
        self.conf = float(value)
        self.conf_slider_label.config(text=f"Confidence: {self.conf:.2f}")

    def on_timer_changed(self, value):
        self.stable_duration = float(value)
        self.timeout_slider_label.configure(text=f"Timer: {self.stable_duration:.2f}")

    def on_tts_speed_changed(self, value):
        self.speech_rate = float(value)
        self.tts_speed_label.configure(text=f"TTS Speed: {self.speech_rate:.2f}")
    
    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE ,1)
        threading.Thread(target=self.update_frame, daemon=True).start()
    
    def stop_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.panel1.configure(image=self.placeholder_photo)
    
    def update_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)

                # Define ROI for sign detection
                h, w, _ = frame.shape
                box_w = w // 3
                box_h = h // 2
                start_x = ((w - box_w) // 2) + 150
                start_y = (h - box_h) // 2 - 50
                end_x = start_x + box_w
                end_y = start_y + box_h + 100

                # Draw a rectangle around the detection area
                cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (33, 115, 70), 2)
                region_frame = frame[start_y:end_y, start_x:end_x]

                results = self.model(region_frame, conf = self.conf)

                current_char = None
                for result in results:
                    if result.boxes:
                        for box in result.boxes:
                            current_char = self.model.names[int(box.cls[0])]
                            break  # Take only the first detected sign
                    annotated_region = result.plot()

                frame[start_y:end_y, start_x:end_x] = annotated_region
                
                # Detection timeout
                if current_char is not None:
                    if self.sign_start_time is None:
                        self.sign_start_time = time.time()
                    elif time.time() - self.sign_start_time >= self.stable_duration:
                        if current_char == "space":
                            self.current_sentence += " "
                        elif current_char == "delete":
                            self.current_sentence = self.current_sentence[:-1]
                        elif current_char == "stop":
                            self.current_sentence += "."
                            self.detected_text += self.current_sentence + "\n"
                            # save_to_file(self.current_sentence, FILE_PATH)
                            self.current_sentence = ""
                        else:
                            self.current_sentence += current_char

                        self.sign_start_time = None
                        cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (33, 115, 70), -1)
                else:
                    self.sign_start_time = None

                # Update text box
                self.text_panel.delete("1.0", tk.END)
                self.text_panel.insert(tk.END, self.detected_text + self.current_sentence + "\n")
                self.text_panel.see(tk.END)

                current_text = self.text_panel.get("1.0", "end").strip()
                new_text = f"{self.detected_text}{self.current_sentence}"

                # Append only if the text has changed
                # if current_text != new_text:
                #     self.text_panel.delete("1.0", tk.END)
                #     self.text_panel.insert(tk.END, self.current_sentence + "\n")
                #     self.text_panel.see(tk.END)

                # Display the frame
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.panel1.imgtk = imgtk
                self.panel1.configure(image=imgtk)

            self.root.after(100, self.update_frame)
    
    def save_text(self):
        text = self.text_panel.get("1.0", tk.END).strip()
        save_as_text(text=text)

    def clear_text(self):
        self.detected_text = ""
        self.current_sentence = ""
        self.text_panel.delete("1.0", tk.END)
    
    def read_aloud(self):
        # Get the text from the text widget
        text = self.text_panel.get("1.0", tk.END).strip()
    
        # Run text_to_speech in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=self.run_tts, args=(text, self.speech_rate))
        thread.start()

    def run_tts(self, text, rate):
        # Call the text_to_speech function
        text_to_speech(text=text, rate=rate, path=AUDIO_PATH)

if __name__ == "__main__":
    root = tk.Tk()
    app = ASLApp(root)
    root.mainloop()
