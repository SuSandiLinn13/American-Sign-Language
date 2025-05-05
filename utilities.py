from tkinter import filedialog
from kokoro import KPipeline
import soundfile as sf
import pygame

def save_as_text(text):
    if not text:
        return  # Do nothing if there's no text to save

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="Save As"
    )

    if file_path:  # If the user didn't cancel
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(text)

def text_to_speech(text, rate, path):
    if text:
        pipeline = KPipeline(lang_code='a')
        pygame.mixer.init()
        generator = pipeline(text, voice='af_heart', speed=rate, split_pattern=r'\n+')

        for i, (_, _, audio) in enumerate(generator):
            if i == 0:  # Play only the first generated audio
                output_file = path
                sf.write(output_file, audio, 24000)  # Save the audio file

                pygame.mixer.music.load(output_file)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

if __name__ == "__main__":
    print("Functions imported")
