#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$HOME/.claude/rules"

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Always install common rules
if [ -d "$SCRIPT_DIR/common" ]; then
    echo "Installing common rules to $TARGET_DIR..."
    cp -r "$SCRIPT_DIR/common" "$TARGET_DIR/"
else
    echo "Error: 'common' directory not found in $SCRIPT_DIR"
    exit 1
fi

# Install requested language rules
for lang in "$@"; do
    if [ -d "$SCRIPT_DIR/$lang" ]; then
        echo "Installing $lang rules..."
        cp -r "$SCRIPT_DIR/$lang" "$TARGET_DIR/"
    else
        echo "Warning: Language directory '$lang' not found. Skipping."
    fi
done

echo "Installation complete. Rules are located in: $TARGET_DIR"
