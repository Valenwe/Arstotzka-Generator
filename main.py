# ░▀█▀░█▄█░█▀█░█▀█░█▀▄░▀█▀░█▀▀
# ░░█░░█░█░█▀▀░█░█░█▀▄░░█░░▀▀█
# ░▀▀▀░▀░▀░▀░░░▀▀▀░▀░▀░░▀░░▀▀▀

import logging
import json
import os
import random
import subprocess
from tqdm import tqdm

# Image handle
import numpy as np
from PIL import ImageFont, ImageDraw, Image

# Video handle
from moviepy.editor import VideoFileClip
import cv2

# Audio handle
from pydub import AudioSegment

# ░█▀▀░█▀█░█▀█░█▀▀░▀█▀░█▀▀
# ░█░░░█░█░█░█░█▀▀░░█░░█░█
# ░▀▀▀░▀▀▀░▀░▀░▀░░░▀▀▀░▀▀▀

# Load sound config
with open("sounds/sounds.json", "r") as file:
    sounds = json.loads(file.read())[0]

# List all possible images
nb_images = 0
for x in os.listdir("imgs"):
    if x.endswith(".png") and "inspector" not in x:
        nb_images += 1

# Load text to display
with open("report.txt", "r") as file:
    text = file.read()
lines = text.split("\n")
if len(lines) >= nb_images:
    logging.error(f"Too many lines, maximum is {nb_images}.")
    exit()
elif len(lines) == 0 or lines[0].strip() == "":
    logging.error("No text found, please fill in the file 'report.txt'")
    exit()
# Add the famous line
lines.append("Glory to Arstotzka.")

# ░█▀█░█▀█░█▀▄░█▀█░█▄█░█▀▀
# ░█▀▀░█▀█░█▀▄░█▀█░█░█░▀▀█
# ░▀░░░▀░▀░▀░▀░▀░▀░▀░▀░▀▀▀

# Set video parameters
frame_size = (1280, 720)  # width, height
width = frame_size[0]
height = frame_size[1]
fps = 30

# Set font properties
font = ImageFont.truetype("imgs/pixelplay.ttf", 40)
font_color = (255, 255, 255)

# Create video writer object
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_file = "temp.mp4"
video_writer = cv2.VideoWriter(video_file, fourcc, fps, frame_size)

# Create black background image
background = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)

# ░█▄█░█▀▀░▀█▀░█░█░█▀█░█▀▄░█▀▀
# ░█░█░█▀▀░░█░░█▀█░█░█░█░█░▀▀█
# ░▀░▀░▀▀▀░░▀░░▀░▀░▀▀▀░▀▀░░▀▀▀

def get_text_size(text: str, font: ImageFont.FreeTypeFont):
    """get_text_size

    Will calculate the width and the height of a given text.

    Args:
        text  (str): the text to check.
        font: (ImageFont): the font used for the text.

    Returns:
        (width, height)
    """
    box = font.getbbox(text)
    # width = box[2] - box[0]
    # height = box[3] - box[1]
    return (box[2], box[3])


def create_text_image(text: str, frame: list, x = int(width / 2), y = int(height * 2/3)) -> list:
    """create_text_image

    Will put a given text on a given frame.

    Args:
        text  (str): the text to display.
        frame (list): the frame to draw.
        x     (int): the x coordinates of the center of the text.
        y     (int): the y coordinates of the center of the text.

    Returns:
        new frame (list): the frame as a pixel list.
    """
    # Add text to frame
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)

    lines = []
    line_height = 0
    temp_text = ""
    # Add new line if too much width
    for word in text.split(" "):
        if len(temp_text) > 0:
            temp_text += " "
        temp_text += word

        (line_width, temp_line_height) = get_text_size(temp_text, font)

        # Save the highest height
        if line_height < temp_line_height:
            line_height = temp_line_height

        if line_width >= 800:
            lines.append(temp_text)
            temp_text = ""

    lines.append(temp_text)

    for i in range(len(lines)):
        line_width = get_text_size(lines[i], font)[0]
        draw.text((x - int(line_width / 2), y + line_height * i), lines[i], font=font, fill=font_color)

    return np.array(img)

def letter_by_letter(text: str, frame: list, start_frame: int, current_frame: int, frame_offset: int, sound_offset: int) -> list:
    """letter_by_letter

    Draw a given text letter by letter, depending on a frame offset.

    Args:
        text          (str): the text to display.
        frame         (list): the frame to draw.
        start_frame   (int): the frame index when we first began drawing.
        current_frame (int): the current frame index.
        frame_offset  (int): the number of frame required to draw a new letter.
        sound_offset  (int): the number of frame required to add the letter sound.

    Returns:
        new frame (list): the frame as a pixel list.
    """
    logging.debug("Adding text...")

    # Add sound if new letter
    if (current_frame - start_frame - 1) // sound_offset != (current_frame - start_frame) // sound_offset:
        sound_frames.append({"type": "letter", "frame": current_frame})

    # Determine letters to display depending on the current frame
    text_to_display = text[:(current_frame - start_frame) // frame_offset]

    return create_text_image(text_to_display, frame), len(text_to_display) >= len(text)

def create_image(img_file: str, frame: list, percentage: float = 1) -> list:
    """create_image

    Draw a given image on a frame.

    Args:
        img_file   (str): the image file path.
        frame      (list): the frame to draw.
        percentage (int): the percentage of the image width being hidden (starting from the left).

    Returns:
        new frame (list): the frame as a pixel list.
    """
    image = cv2.imread(img_file)
    image_size = (image.shape[1], image.shape[0])

    x1 = int(width / 2 - image_size[0] / 2)
    y1 = int(height / 3 - image_size[1] / 2)
    x2 = int(x1 + image_size[0])
    y2 = int(y1 + image_size[1])

    # Width to remove from image
    if percentage < 0:
        percentage = 0
    empty_width = int(percentage * image_size[0])

    # Insert image
    frame[y1:y2, x1 + empty_width:x2, :] = image[0:image_size[1], empty_width:image_size[0], :]
    return frame

def image_repr(img_file: str, frame: list, start_frame: int, current_frame: int, frame_offset: int) -> list:
    """image_repr

    Draw a given image with a wipe entry transition effect from the right.

    Args:
        img_file   (str): the image file path.
        frame         (list): the frame to draw.
        start_frame   (int): the frame index when we first began drawing.
        current_frame (int): the current frame index.
        frame_offset  (int): the number of frame required to add 1% of the image width for the wipe transition.

    Returns:
        new frame (list): the frame as a pixel list.
    """
    logging.debug("Adding image...")
    percentage = 0.01 * float((current_frame - start_frame) / frame_offset)
    percentage = 1 - percentage

    frame = create_image(img_file, frame, percentage)
    return frame, percentage <= 0

def wait_x_second(video_writer, frame: list, seconds: float) -> list:
    """wait_x_second

    Will reproduce a given frame for a given amount of seconds.

    Args:
        video_writer: the video writer.
        frame (list): the frame to reproduce.
        seconds (float): the amount of seconds to reproduce.

    Returns:
        new frame (list): the frame as a pixel list.
    """
    logging.debug("Waiting...")
    nb_frames = int(fps * seconds)
    for _ in range(nb_frames):
        video_writer.write(frame)

    return nb_frames

# Frame to display
frame = background.copy()

# Last frame that contained an image without text
last_image_frame = None

# Last frame that contained text
last_text_frame = None

# Frame counter
frame_counter = 0

# List of sounds to display with their respective frame
sound_frames = [{"type": "music", "frame": frame_counter}]

# Beginning generating
for line_counter in tqdm(range(len(lines)), desc="Writing text", colour="RED"):
    line = lines[line_counter]

    # If last line, put the arstotzka image automatically
    image_index = line_counter
    if line_counter == len(lines) - 1:
        image_index = "arstotzka"

    # add image
    done = False
    start_frame = frame_counter
    while not done:
        frame, done = image_repr(f"imgs/{image_index}.png", frame, start_frame, frame_counter, 0.2)
        video_writer.write(frame)
        frame_counter += 1

    # save frame before text
    last_image_frame = frame.copy()

    # wait sec
    frame_counter += wait_x_second(video_writer, frame, 0.2)

    # add text
    done = False
    start_frame = frame_counter
    while not done:
        frame, done = letter_by_letter(line, last_image_frame, start_frame, frame_counter, 2, 3)
        video_writer.write(frame)
        frame_counter += 1
        last_text_frame = frame.copy()

    # if not the last image
    if line_counter != len(lines) - 1:
        # wait sec
        frame_counter += wait_x_second(video_writer, frame, .8)

        # Add a false 'letter' sound for the next button (nevermind)
        # sound_frames.append({"type": "letter", "frame": frame_counter})

        # wait sec
        frame_counter += wait_x_second(video_writer, frame, 1.2)

        # remove text
        frame = last_image_frame

        # wait sec
        frame_counter += wait_x_second(video_writer, frame, 0.1)

        # append next sound
        sound_frames.append({"type": "next", "frame": frame_counter})
    else:
        frame_counter += wait_x_second(video_writer, last_text_frame, 5)

# Release video writer
video_writer.release()

# Load the video
video = VideoFileClip(video_file)

# CREATE THE FUCKING AUDIO (took me quite some time to finally figure out a way to do it)
audio_file = "temp.mp3"
main_sound = None
for sound in tqdm(sound_frames, desc="Mixing sound", colour="YELLOW"):
    if sound["type"] == "music":
        main_sound = AudioSegment.from_wav(sounds[sound["type"]][0]["filename"])
    else:
        new_audio = sounds[sound["type"]]
        rd = random.randint(0, len(new_audio) - 1)
        audiofile = AudioSegment.from_wav(new_audio[rd]["filename"])

        # lower letter sound
        if sound["type"] == "letter":
            audiofile -= 7

        main_sound = main_sound.overlay(audiofile, position=int(1000 * (sound["frame"] / fps)))

# Split the audio
main_sound = main_sound[:1000 * video.duration]
main_sound = main_sound.fade_out(1000)
main_sound.export(audio_file, format="mp3")

command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y",
           "-i", video_file, "-i", audio_file,
           "-c:v", "libx264", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
           "jail.mp4"]

# print(" ".join(command))
subprocess.call(command, shell=True)

# Removing temp files (might not work)
try:
    os.remove(video_file)
    os.remove(audio_file)
except:
    logging.error("Could not remove temp files.")