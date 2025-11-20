# ░▀█▀░█▄█░█▀█░█▀█░█▀▄░▀█▀░█▀▀
# ░░█░░█░█░█▀▀░█░█░█▀▄░░█░░▀▀█
# ░▀▀▀░▀░▀░▀░░░▀▀▀░▀░▀░░▀░░▀▀▀

import logging
import random
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Any

import click
import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
from tqdm import tqdm

# ░█▀█░█▀█░█▀▄░█▀█░█▄█░█▀▀
# ░█▀▀░█▀█░█▀▄░█▀█░█░█░▀▀█
# ░▀░░░▀░▀░▀░▀░▀░▀░▀░▀░▀▀▀

BANNER: str = """
         &&&&&&&&&&&&&&&&&&&&&&&&+                .&&&&         ;&&&&&&&&&&&&&&&&&&&&&&&&
          &&&&&&&&&&&&&&&&&&&&&&&&&           &&&&&&           &&&&&&&&&&&&&&&&&&&&&&&&&
            ;&&&&&&&&&&&&&&&&&&&&&&&&       &&&&&&$   x;;   x&&&&&&&&&&&&&&&&&&&&&&&&;
               &&&&&&&&&&&&&&&&&&&&&&       &&&&&&&&&&      &&&&&&&&&&&&&&&&&&&&&&&
                &&&&&&&&&&&&&&&&&&&&&       &&&&&&&&&&      &&&&&&&&&&&&&&&&&&&&&&
                   ;&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&+
                     &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
                       $&&&&&&&&&&&&&&&&&  $$$$:  .$$$$  &&&&&&&&&&&&&&&&&$
                          &&&&&&&&&&&&&&&                &&&&&&&&&&&&&&&
                           &&&&&&&&&&&&&&         .&&&   &&&&&&&&&&&&&&
                              &&&&&&&&&&&      X&&$      &&&&&&&&&&&
                                &&&&&&&&&     &&&        &&&&&&&&&
                                 x&&&&&&&   &&&:         &&&&&&&x
                                     &&&&&&            &&&&&&
                                      &&&&&&          &&&&&&
                                        &&&&&&&:  .&&&&&&&
                                        &&&&&&&&&&&&&&&&&&
                                      &&&&&&&&&&&&&&&&&&&&&&
                                         &&&&&&&&&&&&&&&&
                                        &&&&&&&&&&&&&&&&&&
                                           +&&&&&&&&&&+
                                              &&&&&&
"""

dist_dir = files("arstotzka") / "dist"
DIST_PATH = Path(str(dist_dir))

# Set video parameters
frame_size = (1280, 720)  # width, height
width = frame_size[0]
height = frame_size[1]
fps = 30

# Set font properties
font = ImageFont.truetype(DIST_PATH / "misc/pixelplay.ttf", 40)
font_color = (255, 255, 255)

# Create black background image
background = np.zeros((frame_size[1], frame_size[0], 3), dtype=np.uint8)

# ░█▄█░█▀▀░▀█▀░█░█░█▀█░█▀▄░█▀▀
# ░█░█░█▀▀░░█░░█▀█░█░█░█░█░▀▀█
# ░▀░▀░▀▀▀░░▀░░▀░▀░▀▀▀░▀▀░░▀▀▀


def get_text_size(text: str, font: ImageFont.FreeTypeFont):
    """Calculate the width and height of the given text.

    Parameters
    ----------
    text : str
        Text to measure.
    font : ImageFont.FreeTypeFont
        Font used for the text.

    Returns
    -------
    width : int
        Width of the text in pixels.
    height : int
        Height of the text in pixels.

    """
    box = font.getbbox(text)
    return (box[2], box[3])


def get_video_duration(video_path: Path) -> float:
    """Retrieve the duration of a video.

    Parameters
    ----------
    video_path : Path
        Path to the video file.

    Returns
    -------
    duration : float
        Duration of the video in seconds.
    """
    video = cv2.VideoCapture(str(video_path))
    fps = video.get(cv2.CAP_PROP_FPS)
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    video.release()
    return duration


def create_text_image(text: str, frame: np.ndarray, x=int(width / 2), y=int(height * 2 / 3)) -> np.ndarray:
    """Draw text on a frame, centered at (x, y).

    Parameters
    ----------
    text : str
        Text to display.
    frame : np.ndarray
        Frame image to draw on.
    x : int, optional
        X-coordinate of the text center.
    y : int, optional
        Y-coordinate of the text center.

    Returns
    -------
    frame : np.ndarray
        Frame with text drawn.
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
        draw.text((x - int(line_width / 2), y + line_height * i), "{}".format(lines[i]), font=font, fill=font_color)

    return np.array(img)


def letter_by_letter(
    text: str,
    frame: np.ndarray,
    start_frame: int,
    current_frame: int,
    frame_offset: int,
    sound_frames: list[dict[str, Any]],
    sound_offset: int,
) -> tuple[np.ndarray, bool]:
    """Draw text letter by letter on a frame depending on frame offset.

    Parameters
    ----------
    text : str
        Text to display.
    frame : np.ndarray
        Frame to draw on.
    start_frame : int
        Frame index when drawing began.
    current_frame : int
        Current frame index.
    frame_offset : int
        Frames required to draw a new letter.
    sound_frames : list of dict
        List of sound events.
    sound_offset : int
        Frames between each letter sound.

    Returns
    -------
    frame : np.ndarray
        Updated frame with text.
    done : bool
        True if the full text has been drawn.
    """
    logging.debug("Adding text...")

    # Add sound if new letter
    if (current_frame - start_frame - 1) // sound_offset != (current_frame - start_frame) // sound_offset:
        sound_frames.append({"type": "letter", "frame": current_frame})

    # Determine letters to display depending on the current frame
    text_to_display = text[: (current_frame - start_frame) // frame_offset]

    return create_text_image(text_to_display, frame), len(text_to_display) >= len(text)


def create_image(img_file: Path, frame: np.ndarray, percentage: float = 1) -> np.ndarray:
    """Draw an image on a frame, optionally hiding a portion from the left.

    Parameters
    ----------
    img_file : Path
        Image file path.
    frame : np.ndarray
        Frame to draw on.
    percentage : float, optional
        Fraction of the image width to hide (0.0-1.0).

    Returns
    -------
    frame : np.ndarray
        Frame with the image drawn.
    """
    target_size = (480, 320)
    image = cv2.imread(str(img_file))
    if image is None:
        raise FileNotFoundError(f"Failed to load image: {img_file}")

    # Check if the image size matches the target size
    img_h, img_w = image.shape[:2]
    if img_w != target_size[0] or img_h != target_size[1]:
        # Resize the image to the target size
        image = cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)

    x1 = int(width / 2 - img_w / 2)
    y1 = int(height / 3 - img_h / 2)
    x2 = int(x1 + img_w)
    y2 = int(y1 + img_h)

    # Width to remove from image
    if percentage < 0:
        percentage = 0
    empty_width = int(percentage * img_w)

    # Insert image
    frame[y1:y2, x1 + empty_width : x2, :] = image[0:img_h, empty_width:img_w, :]

    return frame


def image_repr(
    img_file: Path, frame: np.ndarray, start_frame: int, current_frame: int, frame_offset: int | float
) -> tuple[np.ndarray, bool]:
    """Draw an image on a frame with a right-to-left wipe transition.

    Parameters
    ----------
    img_file : Path
        Image file path.
    frame : np.ndarray
        Frame to draw on.
    start_frame : int
        Frame index when drawing began.
    current_frame : int
        Current frame index.
    frame_offset : int | float
        Frames required for 1% of image width to appear.

    Returns
    -------
    frame : np.ndarray
        Frame with image applied.
    done : bool
        True if the transition is complete.
    """
    logging.debug("Adding image...")
    percentage = 0.01 * float((current_frame - start_frame) / frame_offset)
    percentage = 1 - percentage

    frame = create_image(img_file, frame, percentage)
    return frame, percentage <= 0


def wait_x_second(video_writer: cv2.VideoWriter, frame: np.ndarray, seconds: float) -> int:
    """Repeat a frame for a specified number of seconds.

    Parameters
    ----------
    video_writer : cv2.VideoWriter
        Video writer object.
    frame : np.ndarray
        Frame to repeat.
    seconds : float
        Duration in seconds.

    Returns
    -------
    nb_frames : int
        Number of frames written.
    """
    logging.debug("Waiting...")
    nb_frames = int(fps * seconds)
    for _ in range(nb_frames):
        video_writer.write(frame)

    return nb_frames


@click.command()
@click.option(
    "--video-filename",
    "-v",
    "video_filename",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, writable=True),
    default="jail.mp4",
    show_default=True,
    help="Path to the generated video file.",
)
@click.option(
    "--report-file",
    "-r",
    "report_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    help="Path where the video's text is written.",
)
@click.option(
    "--image-folder",
    "-i",
    "image_folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Optional path to your images.",
)
@click.option(
    "--sound-folder",
    "-s",
    "sound_folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    help="Optional path to your sound map folder.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Increase verbosity.",
)
@click.option(
    "--jail-mode",
    is_flag=True,
    help="Change the default files for a jail ambiance.",
)
def main(  # noqa: C901
    video_filename: str,
    report_file: str | None,
    image_folder: str | None,
    sound_folder: str | None,
    verbose: bool,
    jail_mode: bool,
) -> None:
    """Process method."""
    logging.basicConfig(level=logging.INFO if not verbose else logging.DEBUG)

    if jail_mode:
        logging.info("Jail mode enabled.")
        # image_folder = str(DIST_PATH / "jail_imgs")
        sound_folder = str(DIST_PATH / "jail_sounds")

    # Load sound config
    yaml_path = (DIST_PATH / "sounds" if not sound_folder else Path(sound_folder)) / "sounds.yaml"
    with yaml_path.open("r") as f:
        sounds: dict[str, list[str] | str] = yaml.safe_load(f)[0]
    SOUNDS_PATH: Path = Path(yaml_path).parent  # noqa: N806

    # List all possible images
    nb_images = 0
    for x in (DIST_PATH / "imgs").iterdir():
        if x.suffix == ".png" and "inspector" not in x.name:
            nb_images += 1

    # Load text to display
    report_path = (DIST_PATH / "report.txt") if not report_file else Path(report_file)
    text = report_path.read_text()

    # Remove empty lines
    lines = [line for line in text.splitlines() if line.strip()]

    # Define where to find the images
    IMAGE_FOLDER: Path = DIST_PATH / "imgs" if not image_folder else Path(image_folder)  # noqa: N806

    if len(lines) >= nb_images:
        logging.error(f"Too many lines in your report (currently {len(lines)}), maximum is {nb_images - 1}.")
        exit()
    elif len(lines) == 0 or lines[0].strip() == "":
        logging.error("No text found, please fill in the file 'report.txt'")
        exit()

    # Burn the famous line to the video
    lines.append("Glory to Arstotzka.")

    # Create video writer object
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore
    temp_dir = tempfile.TemporaryDirectory()
    video_file = Path(temp_dir.name) / "temp.mp4"
    video_writer: cv2.VideoWriter = cv2.VideoWriter(str(video_file), fourcc, fps, frame_size)

    # Frame to display
    frame: np.ndarray = background.copy()

    # Last frame that contained an image without text
    last_image_frame: np.ndarray | None = None

    # Last frame that contained text
    last_text_frame: np.ndarray | None = None

    # Frame counter
    frame_counter = 0

    # List of sounds to display with their respective frame
    sound_frames = [{"type": "music", "frame": frame_counter}]

    # Beginning generating
    for line_counter in tqdm(range(len(lines)), desc="Writing text", colour="RED"):
        line = lines[line_counter]

        # If last line, put the arstotzka image automatically (BURN IT TO THE VIDEO)
        image_path: Path = (
            IMAGE_FOLDER / f"{line_counter}.png" if line_counter < len(lines) - 1 else DIST_PATH / "imgs/arstotzka.png"
        )

        # add image
        done = False
        start_frame = frame_counter
        while not done:
            frame, done = image_repr(image_path, frame, start_frame, frame_counter, 0.2)
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
            frame, done = letter_by_letter(line, last_image_frame, start_frame, frame_counter, 2, sound_frames, 3)
            video_writer.write(frame)
            frame_counter += 1
            last_text_frame = frame.copy()

        # if not the last image
        if line_counter != len(lines) - 1:
            # wait sec
            frame_counter += wait_x_second(video_writer, frame, 0.8)

            # wait sec
            frame_counter += wait_x_second(video_writer, frame, 1.2)

            # remove text
            frame = last_image_frame

            # wait sec
            frame_counter += wait_x_second(video_writer, frame, 0.1)

            # append next sound
            sound_frames.append({"type": "next", "frame": frame_counter})
        else:
            if last_text_frame is None:
                raise ValueError("Could not find an initilized 'last_text_frame'.")
            frame_counter += wait_x_second(video_writer, last_text_frame, 5)

    # Release video writer
    video_writer.release()

    # Load the video
    video_duration = get_video_duration(video_file)

    # CREATE THE FUCKING AUDIO (took me quite some time to finally figure out a way to do it)
    audio_file = Path(temp_dir.name) / "temp.mp3"

    # Init the music first
    main_sound: AudioSegment
    if isinstance(sounds["music"], str):
        # If one single music sound
        main_sound = AudioSegment.from_wav(SOUNDS_PATH / sounds["music"])
    else:
        # If multiple music sounds, add them all at once
        main_sound = AudioSegment.from_wav(SOUNDS_PATH / sounds["music"][0])
        for sound_file in sounds["music"][1:]:
            audio_path = SOUNDS_PATH / sound_file
            audiofile = AudioSegment.from_wav(audio_path)
            main_sound = main_sound.overlay(audiofile)

    for sound in tqdm(sound_frames, desc="Mixing sound", colour="YELLOW"):
        if sound["type"] == "music":
            # The music main_sound has already been initiliazed
            continue
        else:
            new_audio = sounds[sound["type"]]
            rd = random.randint(0, len(new_audio) - 1)  # noqa: S311
            audio_path = SOUNDS_PATH / new_audio[rd]
            if not audio_path.exists():
                audio_path = DIST_PATH / "sounds" / new_audio[rd]
            audiofile = AudioSegment.from_wav(audio_path)

            # lower the letter sound
            if sound["type"] == "letter":
                audiofile -= 7

            main_sound = main_sound.overlay(audiofile, position=int(1000 * (sound["frame"] / fps)))

    # Split the audio
    main_sound = main_sound[: 1000 * video_duration]  # type: ignore
    main_sound = main_sound.fade_out(1000)
    main_sound.export(audio_file, format="mp3")

    command: list[str] = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-y",
        "-i",
        str(video_file),
        "-i",
        str(audio_file),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        video_filename,
    ]

    try:
        logging.debug(" ".join(command))
        subprocess.run(command, check=True)  # noqa: S603
    finally:
        # Cleanup temp files
        temp_dir.cleanup()
        logging.info("Video successfully created at '%s'.\n\n%s\nGlory to Arstotzka.", video_filename, BANNER)
