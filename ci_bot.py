import os
import subprocess
import time
import requests
import json
from telethon import TelegramClient

# Configuration variables
CONFIG_LUNCH = ""
CONFIG_OFFICIAL_FLAG = ""
CONFIG_TARGET = "bacon"
CONFIG_CHATID = "-"
CONFIG_BOT_TOKEN = ""
CONFIG_ERROR_CHATID = ""
CONFIG_PDUP_API = ""
POWEROFF = ""

# Script Constants
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"
BOLD_GREEN = BOLD + "\033[32m"
OFFICIAL = "0"
ROOT_DIRECTORY = os.getcwd()

# Post Constants
DEVICE = CONFIG_LUNCH.split("_")[-1].split("-")[0]
ROM_NAME = os.path.basename(os.getcwd())
OUT = os.path.join(os.getcwd(), "out/target/product", DEVICE)
STICKER_URL = "https://index.sauraj.eu.org/api/raw/?path=/sticker.webp"

# Telegram Client
client = TelegramClient('ci_bot', CONFIG_BOT_TOKEN, CONFIG_BOT_TOKEN)

async def send_message(text, chat_id):
    message = await client.send_message(chat_id, text, parse_mode='html', link_preview=False)
    return message.id

async def edit_message(text, chat_id, message_id):
    await client.edit_message(chat_id, message_id, text, parse_mode='html')

async def send_file(file_path, chat_id):
    await client.send_file(chat_id, file_path, parse_mode='html')

async def send_sticker(sticker_url, chat_id):
    sticker_file = os.path.join(ROOT_DIRECTORY, "sticker.webp")
    response = requests.get(sticker_url)
    with open(sticker_file, 'wb') as f:
        f.write(response.content)
    await client.send_file(chat_id, sticker_file, is_animated=False, is_video=False)

async def pin_message(chat_id, message_id):
    await client.pin_message(chat_id, message_id)

def upload_file(file_path):
    response = requests.put(f"https://pixeldrain.com/api/file/{CONFIG_PDUP_API}", files={'file': open(file_path, 'rb')})
    hash_id = response.json().get('id')
    return f"https://pixeldrain.com/u/{hash_id}"

def fetch_progress():
    with open(os.path.join(ROOT_DIRECTORY, "build.log"), 'r') as f:
        lines = f.readlines()
    progress = [line for line in lines if ' ninja' in line][-1].split()[0]
    return progress if progress else "Initializing the build system..."

def main():
    # CLI parameters
    import sys
    args = sys.argv[1:]
    SYNC = CLEAN = False
    for arg in args:
        if arg in ['-s', '--sync']:
            SYNC = True
        elif arg in ['-c', '--clean']:
            CLEAN = True
        elif arg in ['-o', '--official']:
            if CONFIG_OFFICIAL_FLAG:
                OFFICIAL = "1"
            else:
                print(f"{YELLOW}\nERROR: Please specify the flag to export for official build in the configuration!!{RESET}\n")
                sys.exit(1)
        elif arg in ['-h', '--help']:
            print(f"\nNote: • You should specify all the mandatory variables in the script!\n"
                  f"      • Just run \"./{sys.argv[0]}\" for normal build\n"
                  f"Usage: ./build_rom.py [OPTION]\n"
                  f"Example:\n"
                  f"    ./{os.path.basename(sys.argv[0])} -s -c or ./{os.path.basename(sys.argv[0])} --sync --clean\n"
                  f"\nMandatory options:\n"
                  f"    No option is mandatory!, just simply run the script without passing any parameter.\n"
                  f"\nOptions:\n"
                  f"    -s, --sync            Sync sources before building.\n"
                  f"    -c, --clean           Clean build directory before compilation.\n"
                  f"    -o, --official        Build the official variant during compilation.\n")
            sys.exit(0)
        else:
            print(f"{YELLOW}\nUnknown parameter(s) passed: {arg}{RESET}\n")
            sys.exit(1)

    # Configuration Checking
    if not CONFIG_LUNCH or not CONFIG_TARGET:
        print(f"{YELLOW}\nERROR: Please specify all of the mandatory variables!! Exiting now...{RESET}\n")
        sys.exit(1)

    # Cleanup Files
    for file in ["out/error.log", "out/.lock", os.path.join(ROOT_DIRECTORY, "build.log")]:
        if os.path.exists(file):
            os.remove(file)

    # Jobs Configuration
    CORE_COUNT = os.cpu_count()
    CONFIG_SYNC_JOBS = 12 if CORE_COUNT > 8 else CORE_COUNT
    CONFIG_COMPILE_JOBS = CORE_COUNT

    # Execute Parameters
    if SYNC:
        sync_start_message = (f"🟡 | <i>Syncing sources!!</i>\n\n"
                              f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                              f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                              f"<b>• JOBS:</b> <code>{CONFIG_SYNC_JOBS} Cores</code>\n"
                              f"<b>• DIRECTORY:</b> <code>{os.getcwd()}</code>")
        sync_message_id = await send_message(sync_start_message, CONFIG_CHATID)

        SYNC_START = time.time()

        print(f"{BOLD_GREEN}\nStarting to sync sources now...{RESET}\n")
        sync_command = f"repo sync -c --jobs-network={CONFIG_SYNC_JOBS} -j{CONFIG_SYNC_JOBS} --jobs-checkout={CONFIG_SYNC_JOBS} --optimized-fetch --prune --force-sync --no-clone-bundle --no-tags"
        if subprocess.call(sync_command, shell=True) != 0:
            print(f"{YELLOW}\nInitial sync has failed!!{RESET}\n{BOLD_GREEN}\nTrying to sync again with lesser arguments...{RESET}\n")
            if subprocess.call(f"repo sync -j{CONFIG_SYNC_JOBS}", shell=True) != 0:
                print(f"{YELLOW}\nSyncing has failed completely!{RESET}\n{BOLD_GREEN}\nStarting the build now...{RESET}\n")
            else:
                SYNC_END = time.time()
        else:
            SYNC_END = time.time()

        if SYNC_END:
            DIFFERENCE = SYNC_END - SYNC_START
            MINUTES = (DIFFERENCE % 3600) // 60
            SECONDS = ((DIFFERENCE % 3600) % 60)
            sync_finished_message = (f"🟢 | <i>Sources synced!!</i>\n\n"
                                     f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                                     f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                                     f"<b>• JOBS:</b> <code>{CONFIG_SYNC_JOBS} Cores</code>\n"
                                     f"<b>• DIRECTORY:</b> <code>{os.getcwd()}</code>\n\n"
                                     f"<i>Syncing took {MINUTES} minutes(s) and {SECONDS} seconds(s)</i>")
            await edit_message(sync_finished_message, CONFIG_CHATID, sync_message_id)
        else:
            sync_failed_message = (f"🔴 | <i>Syncing sources failed!!</i>\n\n"
                                   f"<i>Trying to compile the ROM now...</i>")
            await edit_message(sync_failed_message, CONFIG_CHATID, sync_message_id)

    if CLEAN:
        print(f"{BOLD_GREEN}\nNuking the out directory now...{RESET}\n")
        subprocess.call("rm -rf out", shell=True)

    build_start_message = (f"🟡 | <i>Compiling ROM...</i>\n\n"
                           f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                           f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                           f"<b>• JOBS:</b> <code>{CONFIG_COMPILE_JOBS} Cores</code>\n"
                           f"<b>• TYPE:</b> <code>{'Official' if OFFICIAL == '1' else 'Unofficial'}</code>\n"
                           f"<b>• PROGRESS</b>: <code>Lunching...</code>")
    build_message_id = await send_message(build_start_message, CONFIG_CHATID)

    BUILD_START = time.time()

    print(f"{BOLD_GREEN}\nSetting up the build environment...{RESET}")
    subprocess.call("source build/envsetup.sh", shell=True)

    print(f"{BOLD_GREEN}\nStarting to lunch {DEVICE} now...{RESET}")
    if subprocess.call(f"lunch {CONFIG_LUNCH}", shell=True) == 0:
        print(f"{BOLD_GREEN}\nStarting to build now...{RESET}")
        subprocess.call(f"m installclean -j{CONFIG_COMPILE_JOBS}", shell=True)
        subprocess.call(f"m {CONFIG_TARGET} -j{CONFIG_COMPILE_JOBS} 2>&1 | tee -a {os.path.join(ROOT_DIRECTORY, 'build.log')}", shell=True)
    else:
        print(f"{YELLOW}\nFailed to lunch {DEVICE}{RESET}")
        build_failed_message = (f"🔴 | <i>ROM compilation failed...</i>\n\n"
                                f"<i>Failed at lunching {DEVICE}...</i>")
        await edit_message(build_failed_message, CONFIG_CHATID, build_message_id)
        await send_sticker(STICKER_URL, CONFIG_CHATID)
        sys.exit(1)

    previous_progress = ""
    while subprocess.call("jobs -r", shell=True) == 0:
        current_progress = fetch_progress()
        if current_progress != previous_progress:
            build_progress_message = (f"🟡 | <i>Compiling ROM...</i>\n\n"
                                      f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                                      f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                                      f"<b>• JOBS:</b> <code>{CONFIG_COMPILE_JOBS} Cores</code>\n"
                                      f"<b>• TYPE:</b> <code>{'Official' if OFFICIAL == '1' else 'Unofficial'}</code>\n"
                                      f"<b>• PROGRESS:</b> <code>{current_progress}</code>")
            await edit_message(build_progress_message, CONFIG_CHATID, build_message_id)
            previous_progress = current_progress
        time.sleep(5)

    build_progress_message = (f"🟡 | <i>Compiling ROM...</i>\n\n"
                              f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                              f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                              f"<b>• JOBS:</b> <code>{CONFIG_COMPILE_JOBS} Cores</code>\n"
                              f"<b>• TYPE:</b> <code>{'Official' if OFFICIAL == '1' else 'Unofficial'}</code>\n"
                              f"<b>• PROGRESS:</b> <code>{fetch_progress()}</code>")
    await edit_message(build_progress_message, CONFIG_CHATID, build_message_id)

    BUILD_END = time.time()
    DIFFERENCE = BUILD_END - BUILD_START
    HOURS = DIFFERENCE // 3600
    MINUTES = (DIFFERENCE % 3600) // 60

    if os.path.exists("out/error.log"):
        build_failed_message = (f"🔴 | <i>ROM compilation failed...</i>\n\n"
                                f"<i>Check out the log below!</i>")
        await edit_message(build_failed_message, CONFIG_ERROR_CHATID, build_message_id)
        await send_file("out/error.log", CONFIG_ERROR_CHATID)
    else:
        ota_file = [f for f in os.listdir(OUT) if "ota" in f][-1]
        os.remove(os.path.join(OUT, ota_file))

        zip_file = [f for f in os.listdir(OUT) if DEVICE in f][-1]
        zip_file_path = os.path.join(OUT, zip_file)

        print(f"{BOLD_GREEN}\nStarting to upload the ZIP file now...{RESET}\n")
        zip_file_url = upload_file(zip_file_path)
        zip_file_md5sum = subprocess.check_output(f"md5sum {zip_file_path}", shell=True).split()[0].decode()
        zip_file_size = subprocess.check_output(f"ls -sh {zip_file_path}", shell=True).split()[0].decode()

        build_finished_message = (f"🟢 | <i>ROM compiled!!</i>\n\n"
                                  f"<b>• ROM:</b> <code>{ROM_NAME}</code>\n"
                                  f"<b>• DEVICE:</b> <code>{DEVICE}</code>\n"
                                  f"<b>• TYPE:</b> <code>{'Official' if OFFICIAL == '1' else 'Unofficial'}</code>\n"
                                  f"<b>• SIZE:</b> <code>{zip_file_size}</code>\n"
                                  f"<b>• MD5SUM:</b> <code>{zip_file_md5sum}</code>\n"
                                  f"<b>• DOWNLOAD:</b> {zip_file_url}\n\n"
                                  f"<i>Compilation took {HOURS} hours(s) and {MINUTES} minutes(s)</i>")
        await edit_message(build_finished_message, CONFIG_CHATID, build_message_id)
        await pin_message(CONFIG_CHATID, build_message_id)

    if POWEROFF:
        print(f"{BOLD_GREEN}\nAyo, powering off server...{RESET}")
        subprocess.call("sudo poweroff", shell=True)

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
