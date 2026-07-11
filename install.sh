#!/usr/bin/env bash
set -e

APP_NAME="MCServerHost"
REPO="https://github.com/ionmsr/hostmcserver.git"
INSTALL_DIR="$HOME/MCServerHost-app"

echo "=================================="
echo "  MCServerHost Installer"
echo "=================================="
echo ""

# ── Detect OS ────────────────────────────────────────
OS="$(uname -s)"
echo "[1/6] Detected OS: $OS"

# ── Check / Install Python ──────────────────────────
echo "[2/6] Checking Python..."
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
    echo "  Python 3 not found. Installing..."
    if [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-tk
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3 python3-tkinter
        elif command -v yum &>/dev/null; then
            sudo yum install -y python3 python3-tkinter
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm python python tk
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y python3 python3-tk
        fi
    elif [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install python-tk
        else
            echo "  Homebrew not found. Install from https://brew.sh"
            exit 1
        fi
    fi
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "  FAILED to install Python. Install Python 3.8+ manually."
        exit 1
    fi
fi
echo "  Python: $($PYTHON_CMD --version 2>&1)"

# ── Check / Install tkinter ─────────────────────────
echo "[3/6] Checking tkinter..."
if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    echo "  tkinter not found. Installing..."
    if [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y -qq python3-tk
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y python3-tkinter
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm tk
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y python3-tk
        fi
    elif [ "$OS" = "Darwin" ]; then
        brew install tk 2>/dev/null || true
    fi
    if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
        echo "  WARNING: tkinter still missing. The app will attempt to install it on first run."
    else
        echo "  tkinter: OK"
    fi
else
    echo "  tkinter: OK"
fi

# ── Check / Install Java ────────────────────────────
echo "[4/6] Checking Java..."
JAVA_OK=false
if command -v java &>/dev/null; then
    JAVA_VER=$(java -version 2>&1 | head -1 | grep -oP '"\K\d+')
    if [ "$JAVA_OK" = false ] && [ "$JAVA_VER" -ge 21 ] 2>/dev/null; then
        JAVA_OK=true
        echo "  Java: $(java -version 2>&1 | head -1)"
    fi
fi

if [ "$JAVA_OK" = false ]; then
    echo "  Java 21+ not found. Installing..."
    if [ "$OS" = "Linux" ]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y -qq openjdk-21-jre-headless 2>/dev/null || \
            sudo apt-get install -y -qq openjdk-17-jre-headless 2>/dev/null || true
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y java-21-openjdk-headless 2>/dev/null || \
            sudo dnf install -y java-17-openjdk-headless 2>/dev/null || true
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm jre-openjdk
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y java-21-openjdk-headless 2>/dev/null || true
        fi
    elif [ "$OS" = "Darwin" ]; then
        if command -v brew &>/dev/null; then
            brew install openjdk
        fi
    fi
    if command -v java &>/dev/null; then
        echo "  Java: $(java -version 2>&1 | head -1)"
    else
        echo "  WARNING: Java not installed. The app will attempt to install it on first run."
    fi
fi

# ── Clone / Update Repository ───────────────────────
echo "[5/6] Downloading MCServerHost..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Repository exists. Updating..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || echo "  Warning: git pull failed (using existing files)"
else
    if [ -d "$INSTALL_DIR" ]; then
        echo "  Removing old installation..."
        rm -rf "$INSTALL_DIR"
    fi
    git clone "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

chmod +x run.sh 2>/dev/null || true

# ── Create Desktop Shortcut ─────────────────────────
echo "[6/6] Creating desktop shortcut..."
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    SHORTCUT="$DESKTOP_DIR/MCServerHost.desktop"
    cat > "$SHORTCUT" << EOF
[Desktop Entry]
Name=MCServerHost
Comment=Host a Minecraft Server
Exec=bash -c 'cd "$INSTALL_DIR" && ./run.sh'
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Game;
EOF
    chmod +x "$SHORTCUT" 2>/dev/null || true
    echo "  Shortcut created on Desktop."
else
    echo "  Desktop folder not found. Skipping shortcut."
fi

echo ""
echo "=================================="
echo "  Installation Complete!"
echo "=================================="
echo ""
echo "  Location: $INSTALL_DIR"
echo "  Run:      cd $INSTALL_DIR && ./run.sh"
echo ""
echo "  Or use the desktop shortcut."
echo ""
