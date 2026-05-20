# Ottawa_Students_HomeHunter Installation Guide

This guide is for people who are not used to setting up developer projects. Take it one step at a time. Ottawa_Students_HomeHunter runs locally on your computer, so you do not need a cloud account or login.

## What You Need

To run Ottawa_Students_HomeHunter, install:

- **Python 3.10 or newer**: required to run the Flask backend.
- **Git**: recommended if you are cloning the project from GitHub.
- **A web browser**: Chrome, Edge, Firefox, or Safari.

Optional for developers:

- **Node.js 20 or newer**: only needed if you want to work on the React frontend with Vite.

The app will install its Python packages automatically into a local `.venv` folder when you run the start script.

## macOS

### 1. Install Python

Go to:

```text
https://www.python.org/downloads/macos/
```

Download and install the latest Python 3 release.

After installing, open **Terminal** and check:

```bash
python3 --version
```

You should see something like:

```text
Python 3.12.x
```

### 2. Install Git

Open **Terminal** and run:

```bash
git --version
```

If macOS asks to install command line developer tools, accept it. After it finishes, run `git --version` again.

### 3. Open The Project Folder

In Terminal, go to the Ottawa_Students_HomeHunter folder. Example:

```bash
cd "/path/to/Ottawa_Students_HomeHunter"
```

If your folder is in Downloads, it may look like:

```bash
cd "$HOME/Downloads/Ottawa_Students_HomeHunter"
```

### 4. Start The App

Run:

```bash
./app_run_scripts/macos/start_app.sh
```

Then open:

```text
http://127.0.0.1:5001/
```

### 5. Stop The App

Run:

```bash
./app_run_scripts/macos/stop_app.sh
```

## Windows

### 1. Install Python

Go to:

```text
https://www.python.org/downloads/windows/
```

Download Python 3.

Important: on the first installer screen, check:

```text
Add python.exe to PATH
```

Then click **Install Now**.

After installing, open **PowerShell** and check:

```powershell
python --version
```

You should see something like:

```text
Python 3.12.x
```

### 2. Install Git

Go to:

```text
https://git-scm.com/download/win
```

Install Git using the default options.

After installing, open a new PowerShell window and check:

```powershell
git --version
```

### 3. Allow PowerShell Scripts

If Windows blocks `.ps1` scripts, run PowerShell as your normal user and enter:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

When asked, type:

```text
Y
```

### 4. Open The Project Folder

In PowerShell, go to the Ottawa_Students_HomeHunter folder. Example:

```powershell
cd "C:\path\to\Ottawa_Students_HomeHunter"
```

If your folder is in Downloads, it may look like:

```powershell
cd "$HOME\Downloads\Ottawa_Students_HomeHunter"
```

### 5. Start The App

Run:

```powershell
.\app_run_scripts\windows\start_app.ps1
```

Then open:

```text
http://127.0.0.1:5001/
```

### 6. Stop The App

Run:

```powershell
.\app_run_scripts\windows\stop_app.ps1
```

## Linux

These instructions use bash.

### 1. Install Python, venv, and Git

On Ubuntu or Debian:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

On Fedora:

```bash
sudo dnf install python3 python3-pip git
```

On Arch Linux:

```bash
sudo pacman -S python python-pip git
```

Check Python:

```bash
python3 --version
```

### 2. Open The Project Folder

```bash
cd "/path/to/Ottawa_Students_HomeHunter"
```

### 3. Start The App

Run:

```bash
./app_run_scripts/linux/start_app.sh
```

Then open:

```text
http://127.0.0.1:5001/
```

### 4. Stop The App

Run:

```bash
./app_run_scripts/linux/stop_app.sh
```

## Optional: Install Node.js For Frontend Development

You do not need Node.js just to use Ottawa_Students_HomeHunter. Install it only if you want to change the React frontend or run Vite.

Download Node.js LTS from:

```text
https://nodejs.org/
```

Check it:

```bash
node --version
npm --version
```

Install frontend packages:

```bash
npm install
```

Run the optional Vite development server:

```bash
npm run dev
```

The normal Ottawa_Students_HomeHunter start script does not require this.

## First Run Notes

The first run may take a few minutes because Ottawa_Students_HomeHunter creates a local Python environment and installs packages listed in `requirements.txt`.

The local environment is stored here:

```text
.venv/
```

Your local app data is stored here:

```text
app_data/
```

Both are local machine folders and should not be committed to Git.

## Common Problems

### Python is not found

Try:

```bash
python3 --version
```

On Windows, try:

```powershell
py --version
```

If Python is still not found, reinstall Python and make sure it is added to PATH.

### Port 5001 is already in use

Stop Ottawa_Students_HomeHunter:

```bash
./app_run_scripts/macos/stop_app.sh
```

On Linux:

```bash
./app_run_scripts/linux/stop_app.sh
```

On Windows:

```powershell
.\app_run_scripts\windows\stop_app.ps1
```

Or start on a different port:

```bash
PORT=5002 ./app_run_scripts/macos/start_app.sh
```

Windows PowerShell:

```powershell
$env:PORT=5002
.\app_run_scripts\windows\start_app.ps1
```

Then open:

```text
http://127.0.0.1:5002/
```

### PowerShell says script execution is disabled

Run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then try the start script again.

### Dependencies fail to install

Make sure you are connected to the internet, then try again:

```bash
./app_run_scripts/macos/start_app.sh
```

Use the Linux or Windows script path if you are on those systems.

## Quick Command Summary

macOS:

```bash
./app_run_scripts/macos/start_app.sh
./app_run_scripts/macos/stop_app.sh
```

Linux:

```bash
./app_run_scripts/linux/start_app.sh
./app_run_scripts/linux/stop_app.sh
```

Windows PowerShell:

```powershell
.\app_run_scripts\windows\start_app.ps1
.\app_run_scripts\windows\stop_app.ps1
```
