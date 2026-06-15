#!/bin/bash
# Build script for Lung Cancer Linux application
# Usage: ./build_linux.sh [clean|build|both|appimage]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This script is designed for Linux only"
    exit 1
fi

# Configuration
BUILD_TYPE="${1:-both}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SPEC_FILE="$PROJECT_ROOT/pulmorisk.spec"
ICON_FILE="$PROJECT_ROOT/src/app/assets/icons/app_icon.png"

cd "$PROJECT_ROOT"

# Check for required files
check_requirements() {
    print_status "Checking requirements..."

    if [ ! -f "$SPEC_FILE" ]; then
        print_error "Spec file not found: $SPEC_FILE"
        exit 1
    fi

    if [ ! -f "src/app/main.py" ]; then
        print_error "main.py not found"
        exit 1
    fi

    if ! uv run pyinstaller --version &> /dev/null; then
        print_error "PyInstaller not available in uv environment."
        print_error "Run: uv sync --dev"
        exit 1
    fi

    print_status "Requirements check passed"
}

# Clean build artifacts
clean_build() {
    print_status "Cleaning build artifacts..."

    # Remove build directories
    rm -rf build/*
    rm -rf dist/*
    rm -rf __pycache__/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

    # Remove spec file generated files
    rm -f pulmorisk.spec.bak

    print_status "Clean complete"
}



# Create icon if it doesn't exist
create_icon() {
    print_status "Icon File: $ICON_FILE"
    if [ ! -f "$ICON_FILE" ]; then
        print_warning "app_icon.png not found. Icon will not be included."
        return
    fi

    # For Linux, PNG is usually sufficient
    # But we can create different sizes for better appearance
    if command -v convert &> /dev/null; then
        print_status "Creating icon sizes from app_icon.png..."

        mkdir -p icons
        for size in 16 32 48 64 128 256; do
            convert app_icon.png -resize ${size}x${size} icons/logo_${size}.png 2>/dev/null || true
        done

        print_status "Icons created in icons/ directory"
    else
        print_warning "ImageMagick not installed. Using app_icon.png as-is."
        print_warning "Install for better icons: sudo apt-get install imagemagick"
    fi
}

# Build the application
build_app() {
    print_status "Starting PyInstaller build..."

    # Set environment variables for build
    export PYTHONOPTIMIZE=1

    # Run PyInstaller
    uv run pyinstaller \
        --clean \
        --noconfirm \
        "$SPEC_FILE" \
        2>&1 | tee build.log

    if [ $? -eq 0 ]; then
        print_status "Build completed successfully!"

        if [ -d "dist/PulmoRisk" ]; then
            APP_SIZE=$(du -sh dist/PulmoRisk | cut -f1)
            print_status "Application size: $APP_SIZE"
            print_status "Application location: $PROJECT_ROOT/dist/PulmoRisk"

            # Make executable
            chmod +x dist/PulmoRisk/PulmoRisk
        fi
    else
        print_error "Build failed. Check build.log for details"
        exit 1
    fi
}

# Create .desktop file for Linux
create_desktop_file() {
    print_status "Creating .desktop file..."

    # Ensure the directory exists
    mkdir -p dist/PulmoRisk

    cat > dist/PulmoRisk/PulmoRisk.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PulmoRisk
Comment=Lung Cancer risk prediction tool
Exec=$(pwd)/dist/PulmoRisk/PulmoRisk
Icon=$(pwd)/dist/PulmoRisk/app_icon.png
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    print_status "Desktop file created: dist/PulmoRisk/PulmoRisk.desktop"
    print_status "To install system-wide:"
    print_status "  sudo cp dist/PulmoRisk/PulmoRisk.desktop /usr/share/applications/"
}

# Test the built application
test_app() {
    print_status "Testing application..."

    if [ ! -f "dist/PulmoRisk/PulmoRisk" ]; then
        print_error "Application not found"
        return 1
    fi

    # Try to launch the app
    print_status "Attempting to launch application..."
    ./dist/PulmoRisk/PulmoRisk &

    print_status "Application launched. Check if it opens correctly."
    print_warning "Press Ctrl+C to stop if app doesn't open or crashes"
    sleep 5
}

# Create AppImage (portable Linux application)
create_appimage() {
    if [ ! -d "dist/PulmoRisk" ]; then
        print_error "Application not found. Build first."
        return 1
    fi

    print_status "Creating AppImage..."

    # Check for appimagetool
    if ! command -v appimagetool &> /dev/null; then
        print_warning "appimagetool not found. Downloading..."

        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage \
            -O appimagetool
        chmod +x appimagetool
    fi

    # Create AppDir structure
    APP_DIR="PulmoRisk.AppDir"
    rm -rf "$APP_DIR"
    mkdir -p "$APP_DIR/usr/bin"
    mkdir -p "$APP_DIR/usr/share/applications"
    mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

    # Copy application
    cp -r dist/PulmoRisk/* "$APP_DIR/usr/bin/"

    # Copy icon
    if [ -f "$ICON_FILE" ]; then
        cp "$ICON_FILE" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/PulmoRisk.png"
        cp "$ICON_FILE" "$APP_DIR/PulmoRisk.png"
    fi

    # Create desktop file
    cat > "$APP_DIR/PulmoRisk.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PulmoRisk
Comment=Lung Cancer risk prediction tool
Exec=PulmoRisk
Icon=PulmoRisk
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    # Copy desktop file
    cp "$APP_DIR/PulmoRisk.desktop" "$APP_DIR/usr/share/applications/"

    # Create AppRun
    cat > "$APP_DIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
cd "${HERE}/usr/bin"
exec "${HERE}/usr/bin/PulmoRisk" "$@"
EOF

    chmod +x "$APP_DIR/AppRun"

    # Build AppImage
    ARCH=x86_64 ./appimagetool "$APP_DIR" PulmoRisk-x86_64.AppImage

    if [ $? -eq 0 ]; then
        APP_SIZE=$(du -sh PulmoRisk-x86_64.AppImage | cut -f1)
        print_status "AppImage created: PulmoRisk-x86_64.AppImage ($APP_SIZE)"
        print_status "You can now distribute this single file!"
    else
        print_error "Failed to create AppImage"
        return 1
    fi

    # Clean up
    rm -rf "$APP_DIR"
}

# Create DEB package
create_deb() {
    if [ ! -d "dist/PulmoRisk" ]; then
        print_error "Application not found. Build first."
        return 1
    fi

    print_status "Creating DEB package..."

    # Create package structure
    PKG_DIR="PulmoRisk_1.1.0_amd64"
    rm -rf "$PKG_DIR"

    mkdir -p "$PKG_DIR/DEBIAN"
    mkdir -p "$PKG_DIR/opt/PulmoRisk"
    mkdir -p "$PKG_DIR/usr/share/applications"
    mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$PKG_DIR/usr/bin"

    # Copy application
    cp -r dist/lunPulmoRiskg/* "$PKG_DIR/opt/PulmoRisk/"

# Create symlink for gui
cat > "$PKG_DIR/usr/bin/PulmoRisk" << 'EOF'
#!/bin/bash
cd /opt/PulmoRisk
exec /opt/PulmoRisk/PulmoRisk "$@"
EOF
    chmod +x "$PKG_DIR/usr/bin/PulmoRisk"

    # Copy icon
    if [ -f "$ICON_FILE" ]; then
        cp "$ICON_FILE" "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/PulmoRisk.png"
    fi

    # Create desktop file
    cat > "$PKG_DIR/usr/share/applications/PulmoRisk.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PulmoRisk
Comment=Lung Cancer risk prediction tool
Exec=/usr/bin/PulmoRisk
Icon=PulmoRisk
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    # Create control file
    cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: PulmoRisk
Version: 1.0.0
Section: science
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.8)
Maintainer: Your Name <your.email@example.com>
Description: Lung Cancer risk prediction tool
 PulmoRisk is a tool for lung cancer risk prediction that combines deep learning features from the Sybil model with clinical and epidemiological factors.
EOF

    # Build package
    dpkg-deb --build "$PKG_DIR"

    if [ $? -eq 0 ]; then
        PKG_SIZE=$(du -sh "${PKG_DIR}.deb" | cut -f1)
        print_status "DEB package created: ${PKG_DIR}.deb ($PKG_SIZE)"
        print_status "Install with: sudo dpkg -i ${PKG_DIR}.deb"
    else
        print_error "Failed to create DEB package"
        return 1
    fi

    # Clean up
    rm -rf "$PKG_DIR"
}

# Troubleshooting function
troubleshoot() {
    print_status "Running diagnostics..."

    echo ""
    echo "System Information:"
    uname -a

    echo ""
    echo "Python Version:"
    python --version

    echo ""
    echo "PyInstaller Version:"
    uv run pyinstaller --version

    echo ""
    echo "Installed Packages (relevant):"
    uv run pip list | grep -E "customtkinter|sybil|torch|torchvision"

    echo ""
    echo "Project Structure:"
    tree -L 2 -I '__pycache__|*.pyc|build|dist' 2>/dev/null || ls -R | head -50

    echo ""
    echo "Display Server:"
    echo "DISPLAY=$DISPLAY"
    echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"

    echo ""
    print_status "Check build.log for detailed error messages"
}

# Main execution
main() {
    echo ""
    echo "========================================"
    echo "  PulmoRisk Linux Build Script"
    echo "========================================"
    echo ""

    check_requirements

    case "$BUILD_TYPE" in
        clean)
            clean_build
            ;;
        build)
            create_icon
            build_app
            create_desktop_file
            ;;
        both)
            clean_build
            create_icon
            build_app
            create_desktop_file
            create_appimage
            create_deb
            ;;
        test)
            test_app
            ;;
        appimage)
            create_appimage
            ;;
        deb)
            create_deb
            ;;
        troubleshoot)
            troubleshoot
            ;;
        *)
            echo "Usage: $0 [clean|build|both|test|appimage|deb|troubleshoot]"
            echo ""
            echo "Options:"
            echo "  clean         - Remove build artifacts"
            echo "  build         - Build the application"
            echo "  both          - Clean then build (default)"
            echo "  test          - Test the built application"
            echo "  appimage      - Create portable AppImage"
            echo "  deb           - Create DEB package"
            echo "  troubleshoot  - Run diagnostics"
            exit 1
            ;;
    esac

    echo ""
    print_status "Done!"
}

# Run main function
main
