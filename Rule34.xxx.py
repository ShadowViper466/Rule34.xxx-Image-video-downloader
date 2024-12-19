import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import tkinter.messagebox as messagebox
from tkinter import filedialog
import shutil
from tkinter import PhotoImage
from PIL import Image, ImageTk
import sys
import random
import time
from urllib.parse import urljoin, urlparse

stop_flag = False
is_completed = False

def handle_url_focus(event):
    """Clear the default text when the user clicks on the URL field."""
    url_entry.delete(0, tk.END)  # Clear the default text

# Function to paste but block typing
def disable_typing(event):
    """Prevent typing but allow pasting."""
    if event.keysym not in ("Control_L", "Control_R", "v", "V"):  # Allow only paste (Ctrl+V)
        return "break" 
    
def get_resource_path(relative_path):
    # If running as a PyInstaller bundle, use the temp folder
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Otherwise, use the script's directory
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)
    
def provide_pdf():
    # Locate the bundled PDF
    source_pdf = get_resource_path("Help me Rule34.xxx.pdf")

    # Ask the user where to save the file
    save_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        title="Save Help PDF"
    )

    if not save_path:  # If the user cancels the dialog
        return

    try:
        # Copy the PDF to the chosen location
        shutil.copyfile(source_pdf, save_path)
        messagebox.showinfo("Download Complete", f"The PDF has been saved to:\n{save_path}")
    except IOError as e:
        messagebox.showerror("Error", f"Failed to save the PDF: {e}")

def random_user_agent():
    """Return a random user agent to simulate browser requests."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
    ]
    return random.choice(user_agents)

def make_request_with_retry(url, headers, retries=3, delay=10):
    """Make an HTTP request with retries in case of failure."""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            else:
                print(f"Attempt {attempt + 1} failed: Status Code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        time.sleep(delay)  # Longer delay to avoid rate-limiting
    return None

def clean_url(media_url):
    """Clean the URL by removing query parameters."""
    parsed_url = urlparse(media_url)
    return parsed_url._replace(query="").geturl()

def download_media(media_url, media_type, page_folder):
    """Download the media (image or video)."""
    media_url = media_url.strip()
    if not media_url:
        return
    
    headers = {
        "User-Agent": random_user_agent()
    }

    # Clean the URL to remove any query parameters
    media_url = clean_url(media_url)

    media_name = os.path.basename(media_url)
    if not media_name.lower().endswith(('jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm')):
        print(f"Skipping invalid media format: {media_name}")
        return

    # Create folder for media type if it doesn't exist
    media_folder = os.path.join(page_folder, media_type)
    if not os.path.exists(media_folder):
        os.makedirs(media_folder)

    try:
        response = requests.get(media_url, headers=headers)
        if response.status_code == 200:
            with open(os.path.join(media_folder, media_name), "wb") as media_file:
                media_file.write(response.content)
            print(f"Downloaded {media_type} media: {media_name}")
        else:
            print(f"Failed to download {media_type} media: {media_url} (Status Code: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {media_type} media {media_name}: {e}")

def get_character_name(base_url):
    """Retrieve the character name from the input field."""
    headers = {
        "User-Agent": random_user_agent()
    }
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch character name. Status Code: {response.status_code}")
            return "UnknownCharacter"
        
        soup = BeautifulSoup(response.text, "html.parser")
        input_tag = soup.find("input", {"name": "tags"})
        if input_tag and input_tag.get("value"):
            return input_tag["value"].strip()
    except Exception as e:
        print(f"Error retrieving character name: {e}")
    return "UnknownCharacter"

def scrape_post_page(post_url, page_folder):
    global stop_flag
    if stop_flag:
        return  # Exit early if stop_flag is True

    headers = {
        "User-Agent": random_user_agent()
    }

    response = make_request_with_retry(post_url, headers)
    if not response:
        print(f"Failed to retrieve post page: {post_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    img_tag = soup.find("img", {"id": "image"})
    video_tag = soup.find("video", {"id": "video"})
    video_meta = soup.find("meta", property="og:image")

    if img_tag and img_tag.get("src"):
        media_url = urljoin(post_url, img_tag["src"])
        download_media(media_url, "IMG", page_folder)
    elif video_meta and video_meta.get("content"):
        media_url = urljoin(post_url, video_meta["content"])
        download_media(media_url, "VIDS", page_folder)
    elif video_tag and video_tag.get("src"):
        media_url = urljoin(post_url, video_tag["src"])
        download_media(media_url, "VIDS", page_folder)
    else:
        print(f"No image or video found on post page: {post_url}")


def scrape_list_page(list_page_url, page_folder):
    global stop_flag
    headers = {
        "User-Agent": random_user_agent()
    }

    response = make_request_with_retry(list_page_url, headers)
    if not response:
        print(f"Failed to retrieve list page: {list_page_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    post_links = soup.find_all("a", id=True, href=True)

    if not post_links:
        print("No post links found on the page.")
        return

    for link in post_links:
        if stop_flag:
            print("Scraping stopped.")
            break  # Exit the loop if stop_flag is True

        post_url = urljoin(list_page_url, link["href"])
        print(f"Processing post: {post_url}")
        scrape_post_page(post_url, page_folder)

def scrape_pages(start_page, end_page, base_folder):
    """Scrape multiple pages from the site."""
    global is_completed  # Declare global to modify it

    base_url = "https://rule34.xxx/index.php?page=post&s=list&tags=feet&pid="
    character_name = get_character_name(base_url)
    rule34_folder = os.path.join(base_folder, "Rule34.xxx", character_name)
    os.makedirs(rule34_folder, exist_ok=True)

    for page_num in range(start_page, end_page + 1):
        page_folder = os.path.join(rule34_folder, f"page{page_num + 1}")
        os.makedirs(page_folder, exist_ok=True)

        # Handle pagination properly by adjusting `pid`
        page_url = f"{base_url}&tags={character_name.replace(' ', '+')}&pid={page_num * 42}"
        print(f"Scraping page {page_num + 1}: {page_url}")
        scrape_list_page(page_url, page_folder)

        # Add a delay between page scraping to avoid being rate-limited
        time.sleep(random.randint(3, 7))  # Longer delay between requests

    # Only set is_completed to True if scraping finishes naturally
    if not stop_flag:
        is_completed = True
    reset_ui()  # Reset UI after scraping

def reset_ui():
    """Reset the UI to its default state."""
    global is_completed  # Declare is_completed as global

    # Schedule GUI updates on the main thread using after()
    root.after(0, reset_ui_gui)

def reset_ui_gui():
    """Update the GUI components after scraping is finished or stopped."""
    global is_completed
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    url_entry.config(state=tk.NORMAL)
    start_page_entry.config(state=tk.NORMAL)
    end_page_entry.config(state=tk.NORMAL)
    folder_entry.config(state=tk.NORMAL)
    folder_button.config(state=tk.NORMAL)

    # Reset button appearance
    start_button.config(bg="SystemButtonFace", fg="black")
    stop_button.config(bg="SystemButtonFace", fg="black")

    # Show completion message if scraping finished
    if is_completed and not stop_flag:  # Check if scraping is completed naturally
        messagebox.showinfo("Completed", "All images/videos have been downloaded successfully.")
        # Reset is_completed to prevent showing the message again
        is_completed = False

def start_scraping_thread():
    global stop_flag
    stop_flag = False

    url = url_entry.get()

    # Validate URL
    if not url.startswith("https://rule34.xxx"):
        messagebox.showerror("Invalid URL", "The base URL must be from https://rule34.xxx")
        return

    start_page = int(start_page_entry.get())
    end_page = int(end_page_entry.get())
    destination_folder = folder_entry.get()

    if not os.path.isdir(destination_folder):
        messagebox.showerror("Invalid folder", "The selected folder is invalid.")
        return

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)  # Enable the stop button when the download starts
    url_entry.config(state=tk.DISABLED)
    start_page_entry.config(state=tk.DISABLED)
    end_page_entry.config(state=tk.DISABLED)
    folder_entry.config(state=tk.DISABLED)
    folder_button.config(state=tk.DISABLED)
        # Make sure the hover effect is cleared when the button is disabled
    start_button.config(bg="SystemButtonFace", fg="black")  # Reset start button appearance


    threading.Thread(target=scrape_pages, args=(start_page, end_page, destination_folder)).start()

def browse_folder():
    """Open a folder selection dialog."""
    folder_selected = filedialog.askdirectory()
    folder_entry.delete(0, tk.END)
    folder_entry.insert(0, folder_selected)

def start_scraping():
    """Start the scraping process."""
    try:
        start_page = int(start_page_entry.get())
        end_page = int(end_page_entry.get())
        base_folder = folder_entry.get()
        scrape_pages(start_page, end_page, base_folder)
    except ValueError:
        print("Please enter valid page numbers.")

def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_entry.config(state=tk.NORMAL)
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_path)
        folder_entry.config(state="readonly")

def stop_scraping():
    global stop_flag, is_completed
    stop_flag = True  # Set the stop flag to true to stop the download

    # Set completion flag to False because download was stopped manually
    is_completed = False

    # Show "Download Stopped" message
    messagebox.showinfo("Download Stopped", "The download process has been stopped.")
    
    # Disable all buttons and reset UI
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    url_entry.config(state=tk.NORMAL)
    start_page_entry.config(state=tk.NORMAL)
    end_page_entry.config(state=tk.NORMAL)
    folder_entry.config(state=tk.NORMAL)
    folder_button.config(state=tk.NORMAL)

    stop_button.config(bg="SystemButtonFace", fg="black")  # Reset stop button appearance
    reset_ui()  # Reset UI after stopping


def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In normal mode, return the current working directory
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def on_enter(event):
    if event.widget['state'] == tk.NORMAL:  # Check if the button is enabled
        event.widget.config(bg="#aae5a4", fg="blue")  # Change to green with white text

def on_leave(event):
    if event.widget['state'] == tk.NORMAL:  # Check if the button is enabled
        event.widget.config(bg="SystemButtonFace", fg="black")  # Revert to default appearance

#For Stop Button
def on_enter2(event):
    if event.widget.cget("state") == "normal":  # Check if the button is enabled
        event.widget.config(bg="#345434", fg="white")  # Change to green with white text
        closeProgram_button.config(bg="red")  # Change color to red on hover

def on_leave2(event):
    if event.widget.cget("state") == "normal":  # Check if the button is enabled
        event.widget.config(bg="SystemButtonFace", fg="black")  # Revert to default appearance
        closeProgram_button.config(bg="#344434")  # Change color back when hover ends

def resource_path(relative_path):
    """Get the absolute path to the resource, works for dev and bundled exe."""
    try:
        # If running as a bundled exe
        base_path = sys._MEIPASS
    except Exception:
        # If running as a script
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def close_window():
    root.quit()

    # Function to make the window draggable
def on_drag(event):
    x = root.winfo_pointerx() - root._offset_x
    y = root.winfo_pointery() - root._offset_y
    root.geometry(f'+{x}+{y}')

def on_press(event):
    root._offset_x = root.winfo_pointerx() - root.winfo_rootx()
    root._offset_y = root.winfo_pointery() - root.winfo_rooty()

# Set up the Tkinter window
root = tk.Tk()
root.title("Scraper Settings")
root.geometry("400x600")
root.overrideredirect(True)
root.resizable(False, False)
root.configure(bg="#344434")
button_font = ('Arial', 12)
label_font = ('Helvetica', 12)
button_font2 =('Arial', 10)
window_width = 400
window_height = 600
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_top = int(screen_height / 2 - window_height / 2)
position_left = int(screen_width / 2 - window_width / 2)
root.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")
if getattr(sys, 'frozen', False):
    # If running as a bundled .exe
    base_path = sys._MEIPASS
else:
    # If running as a script
    base_path = os.path.dirname(__file__)

# Access the files
image_path = os.path.join(base_path, "Rule34.xxx.png")

# Set the background color to match the image's transparency or desired color
root.config(bg='#aae5a4')  # Set to your desired color

# Get the image path from the resource folder or bundled executable
image_path = resource_path("Rule34.xxx.png")

try:
    # Open the image file with transparency support (RGBA)
    img = Image.open(image_path).convert("RGBA")  # Convert to RGBA to handle transparency

    # Resize the image to fit
    max_size = (300, 200)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert the image to a Tkinter-compatible format
    image = ImageTk.PhotoImage(img)

    # Create a Canvas widget
    canvas = tk.Canvas(root, width=img.width, height=img.height, bg='#aae5a4', bd=0, highlightthickness=0)
    canvas.pack(pady=10)

    # Display the image on the canvas
    canvas.create_image(0, 0, anchor=tk.NW, image=image)

except FileNotFoundError:
    print(f"Error: Image file '{image_path}' not found.")
    image = None

# If image loading failed, show a fallback message
if image is None:
    fallback_label = tk.Label(root, text="Image not found", bg='#344434', fg="white")
    fallback_label.pack(pady=10)

url_label = tk.Label(root, text="Enter URL here:")
url_label.pack(pady=5)
url_entry = tk.Entry(root, width=50, justify="center")
url_entry.pack(pady=5)
url_entry.insert(0, "Enter Rule34.US URL here!")
url_entry.bind("<FocusIn>", handle_url_focus)
url_entry.bind("<KeyPress>", disable_typing)

start_page_label = tk.Label(root, text="Start Page:")
start_page_label.pack(pady=5)
start_page_entry = tk.Entry(root, width=10, justify="center")
start_page_entry.pack(pady=5)

end_page_label = tk.Label(root, text="End Page:")
end_page_label.pack(pady=5)
end_page_entry = tk.Entry(root, width=10, justify="center")
end_page_entry.pack(pady=5)

# Folder Selection
folder_label = tk.Label(root, text="Select Folder:", font=label_font)
folder_label.pack(pady=5)
folder_button = tk.Button(root, text="Browse", command=select_folder, font=button_font)
folder_button.pack(pady=5)
folder_entry = tk.Entry(root, width=50, justify="center", state="readonly")
folder_entry.pack(pady=5)

browse_button = tk.Button(root, text="Browse", command=browse_folder)
browse_button

start_button = tk.Button(root, text="Start Downloading", command=start_scraping_thread)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Stop Downloading", command=stop_scraping, state=tk.DISABLED, font=button_font2)
stop_button.pack(pady=5)

help_button = tk.Button(root, text="Help how does this work?", command=provide_pdf, font=button_font2)
help_button.pack(pady=10)

closeProgram_button = tk.Button(root, text="X", command=close_window, bg="#344434", fg="white", relief="flat", font=("Arial", 12))
closeProgram_button.place(x=window_width - 50, y=10)

root.bind("<Button-1>", on_press)
root.bind("<B1-Motion>", on_drag)

# Bind hover events to the Folder Button
folder_button.bind("<Enter>", on_enter)
folder_button.bind("<Leave>", on_leave)
# Bind hover events to the Start Button
start_button.bind("<Enter>", on_enter)
start_button.bind("<Leave>", on_leave)
# Bind hover events to the Stop Button
stop_button.bind("<Enter>", on_enter)
stop_button.bind("<Leave>", on_leave)
# Bind hover events to the Help Button
help_button.bind("<Enter>", on_enter)
help_button.bind("<Leave>", on_leave)
# Bind hover events to the CloseProgram Button
closeProgram_button.bind("<Enter>", on_enter2)
closeProgram_button.bind("<Leave>", on_leave2)


root.mainloop()

#Werkt op het moment
