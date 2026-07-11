#!/usr/bin/env bash
cd "$(dirname "$0")"

PYTHON_CMD=""

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PY_VER=$(python --version 2>&1 | grep -oP '\d+')
    if [ "$PY_VER" -ge 3 ] 2>/dev/null; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "Python 3 is not installed. Attempting to install..."
    SYSTEM=$(uname -s)

    if [ "$SYSTEM" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y python3 python3-tk
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-tkinter
        elif command -v yum &>/dev/null; then
            sudo yum install -y python3 python3-tkinter
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm python python tk
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y python3 python3-tk
        else
            echo "Could not detect package manager. Install Python 3.8+ manually."
            echo "https://www.python.org/downloads/"
            exit 1
        fi
    elif [ "$SYSTEM" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install python-tk
        else
            echo "Homebrew not found. Install it from https://brew.sh"
            echo "Or install Python from https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo "Unsupported OS. Install Python 3.8+ from https://www.python.org/downloads/"
        exit 1
    fi

    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "Python installation failed. Please install Python 3.8+ manually."
        echo "https://www.python.org/downloads/"
        exit 1
    fi

    echo "Python installed successfully."
fi

exec "$PYTHON_CMD" mcserverhost.py
