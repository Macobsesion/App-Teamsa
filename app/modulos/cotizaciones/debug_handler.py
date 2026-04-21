import traceback
import os

def log_error(e):
    with open("error_debug.log", "a") as f:
        f.write("\n" + "="*50 + "\n")
        f.write(traceback.format_exc())
        f.write("\n" + "="*50 + "\n")
