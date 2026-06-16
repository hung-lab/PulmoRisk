#!/bin/bash
# Build script for Lung Cancer Linux application
# Usage: ./build_linux.sh [clean|build|both|test|appimage|deb|troubleshoot]
#
# Optional: override the version embedded in package names by setting
# VERSION in the environment, e.g.:
#   VERSION="${GITHUB_REF_NAME#v}" ./build_linux.sh both

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
DIST_DIR="$PROJECT_ROOT/dist"

APP_NAME="PulmoRisk"
APP_ID="pulmorisk"
VERSION="${VERSION:-0.0.0}"
ARCH="x86_64"     # used for the AppImage filename
DEB_ARCH="amd64"  # Debian's arch naming convention

APP_EXEC="${APP_ID}"
APP_PATH="$DIST_DIR/$APP_NAME"

APPIMAGE_NAME="${APP_NAME}-${VERSION}-${ARCH}.AppImage"
APPIMAGE_PATH="$DIST_DIR/$APPIMAGE_NAME"

DEB_NAME="${APP_ID}_${VERSION}_${DEB_ARCH}.deb"
DEB_PATH="$DIST_DIR/$DEB_NAME"

APP_DIR="${APP_NAME}.AppDir"
APP_BINARY="$APP_PATH/$APP_EXEC"

mkdir -p "$DIST_DIR"

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



# Create additional icon sizes alongside the source icon (optional, best-effort)
create_icon() {
    print_status "Icon File: $ICON_FILE"
    if [ ! -f "$ICON_FILE" ]; then
        print_warning "app_icon.png not found. Icon will not be included."
        return
    fi

    if command -v convert &> /dev/null; then
        print_status "Creating icon sizes from $ICON_FILE..."

        ICON_OUT_DIR="$PROJECT_ROOT/icons"
        mkdir -p "$ICON_OUT_DIR"
        for size in 16 32 48 64 128 256; do
            convert "$ICON_FILE" -resize ${size}x${size} "$ICON_OUT_DIR/logo_${size}.png" 2>/dev/null || true
        done

        print_status "Icons created in $ICON_OUT_DIR/"
    else
        print_warning "ImageMagick not installed. Using $ICON_FILE as-is."
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

        if [ -d "$APP_PATH" ]; then
            APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
            print_status "Application size: $APP_SIZE"
            print_status "Application location: $APP_PATH"

            # Make executable
            if [ -f "$APP_PATH/$APP_EXEC" ]; then
                chmod +x "$APP_PATH/$APP_EXEC"
            else
                print_warning "Executable not found: $APP_PATH/$APP_EXEC"
            fi
        fi
    else
        print_error "Build failed. Check build.log for details"
        exit 1
    fi
}

# Create .desktop file for Linux
create_desktop_file() {
    print_status "Creating .desktop file..."

    mkdir -p "$APP_PATH"

    cat > "$APP_PATH/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=$VERSION
Type=Application
Name=$APP_NAME
Comment=Lung Cancer risk prediction tool
Exec=$APP_EXEC
Icon=$APP_ID
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    print_status "Desktop file created: $APP_PATH/$APP_NAME.desktop"
    print_status "To install system-wide:"
    print_status "  sudo cp $APP_PATH/$APP_NAME.desktop /usr/share/applications/"
}

# Test the built application
test_app() {
    print_status "Testing application..."

    if [ ! -f "$APP_BINARY" ]; then
        print_error "Application not found: $APP_BINARY"
        return 1
    fi

    print_status "Attempting to launch application..."

    "$APP_BINARY" &
    APP_PID=$!

    print_status "Application launched (PID: $APP_PID)"
    print_warning "Press Ctrl+C to stop if it doesn't open or crashes"

    sleep 5

    # Optional: check if still running
    if kill -0 "$APP_PID" 2>/dev/null; then
        print_status "App is still running"
    else
        print_warning "App exited early — likely crash"
    fi
}

# Create AppImage (portable Linux application)
create_appimage() {
    if [ ! -d "$APP_PATH" ]; then
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
    rm -rf "$APP_DIR"
    mkdir -p "$APP_DIR/usr/bin"
    mkdir -p "$APP_DIR/usr/share/applications"
    mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"

    # Copy application
    cp -r "$APP_PATH/"* "$APP_DIR/usr/bin/"

    # Copy icon
    if [ -f "$ICON_FILE" ]; then
        cp "$ICON_FILE" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"
        cp "$ICON_FILE" "$APP_DIR/$APP_ID.png"
    fi

    # Create desktop file
    cat > "$APP_DIR/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Lung Cancer risk prediction tool
Exec=$APP_EXEC
Icon=$APP_ID
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    # Copy desktop file
    cp "$APP_DIR/$APP_NAME.desktop" "$APP_DIR/usr/share/applications/"

    # Create AppRun
    # NOTE: this heredoc is intentionally UNQUOTED so that ${APP_EXEC} is
    # substituted at build time. $SELF, $HERE and $@ are escaped so they're
    # only evaluated at runtime inside the AppImage.
    cat > "$APP_DIR/AppRun" << EOF
#!/bin/bash
SELF=\$(readlink -f "\$0")
HERE=\${SELF%/*}
export PATH="\${HERE}/usr/bin:\${PATH}"
export LD_LIBRARY_PATH="\${HERE}/usr/lib:\${LD_LIBRARY_PATH}"
cd "\${HERE}/usr/bin"
exec "\${HERE}/usr/bin/${APP_EXEC}" "\$@"
EOF

    chmod +x "$APP_DIR/AppRun"

    # Build AppImage
    ARCH=$ARCH ./appimagetool "$APP_DIR" "$APPIMAGE_PATH"

    if [ -f "$APPIMAGE_PATH" ]; then
        APP_SIZE=$(du -sh "$APPIMAGE_PATH" | cut -f1)
        print_status "AppImage created: $APPIMAGE_PATH ($APP_SIZE)"
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
    if [ ! -d "$APP_PATH" ]; then
        print_error "Application not found. Build first."
        return 1
    fi

    print_status "Creating DEB package..."

    # Create package structure
    PKG_DIR="${APP_NAME}_${VERSION}_${DEB_ARCH}"
    rm -rf "$PKG_DIR"

    mkdir -p "$PKG_DIR/DEBIAN"
    mkdir -p "$PKG_DIR/opt/$APP_NAME"
    mkdir -p "$PKG_DIR/usr/share/applications"
    mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$PKG_DIR/usr/bin"

    # Copy application
    cp -r "$APP_PATH/"* "$PKG_DIR/opt/$APP_NAME/"

    # Create symlink for gui
    cat > "$PKG_DIR/usr/bin/$APP_ID" << EOF
#!/bin/bash
cd /opt/$APP_NAME
exec /opt/$APP_NAME/$APP_EXEC "\$@"
EOF
    chmod +x "$PKG_DIR/usr/bin/$APP_ID"

    # Copy icon
    if [ -f "$ICON_FILE" ]; then
        cp "$ICON_FILE" "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"
    fi

    # Create desktop file
    cat > "$PKG_DIR/usr/share/applications/$APP_NAME.desktop" << EOF
[Desktop Entry]
Version=$VERSION
Type=Application
Name=$APP_NAME
Comment=Lung Cancer risk prediction tool
Exec=/usr/bin/$APP_ID
Icon=$APP_NAME
Terminal=false
Categories=Science;Education;MedicalSoftware;
EOF

    # Create control file
    cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: $APP_ID
Version: $VERSION
Section: science
Priority: optional
Architecture: $DEB_ARCH
Depends: python3 (>= 3.8)
Maintainer: Your Name <your.email@example.com>
Description: Lung Cancer risk prediction tool
 PulmoRisk is a tool for lung cancer risk prediction that combines deep learning features from the Sybil model with clinical and epidemiological factors.
EOF

    # Build package
    dpkg-deb --build "$PKG_DIR" "$DEB_PATH"

    if [ -f "$DEB_PATH" ]; then
        PKG_SIZE=$(du -sh "$DEB_PATH" | cut -f1)
        print_status "DEB package created: $DEB_PATH ($PKG_SIZE)"
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