#!/bin/bash

# Make all scripts executable
echo "Making all scripts executable..."

# Make all .sh files executable
find scripts/ -name "*.sh" -exec chmod +x {} \;

# Make all .py files executable
find scripts/ -name "*.py" -exec chmod +x {} \;

echo "✅ All scripts are now executable"
