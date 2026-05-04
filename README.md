# Tkinter Foundry

A modern, production-ready tkinter application with uv, Docker, and CI/CD.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-green.svg)](https://www.gnu.org/licenses/gpl-3.0)
![Ruff](https://img.shields.io/badge/code%20style-ruff-ff69b4.svg)

## Features

- 🐍 **uv package manager** - Fast and efficient dependency management
- 🐳 **Docker development** - Containerized environment with docker-compose
- 🎯 **Ruff integration** - Modern linter and formatter for code quality
- 🚀 **GitHub Actions** - CI/CD, version management, and multi-platform releases
- 🏗️ **MVC architecture** - Clean separation of concerns
- 📝 **Conventional commits** - Automatic version bumping based on commit patterns

## Quick Start

### Development with Docker

1. **Start development environment:**
   ```bash
   docker-compose up -d app
   ```

2. **Get shell in container:**
   ```bash
   docker-compose run --rm shell
   ```

### Local Development

1. **Install uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies:**
   ```bash
   uv sync --all-extras
   ```

3. **Run the application:**
   ```bash
   uv run python -m app.main
   ```

4. **Run tests:**
   ```bash
   uv run pytest
   ```

5. **Run linting:**
   ```bash
   uv run ruff check src/ tests/
   uv run ruff format src/ tests/
   ```

## Project Structure

```
tkinter-app/
├── .github/
│   └── workflows/
│       ├── ci.yml          # CI pipeline
│       ├── release.yml     # Multi-platform releases
│       └── version.yml     # Automatic version bumping
├── src/
│   └── app/
│       ├── __init__.py
│       ├── assets/         # Icons, logos, images, styles
│       ├── config/         # Config files, Application settings
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── main.py         # Application entry point
│       ├── models.py       # Data models
│       ├── views/          # UI components
│       │   ├── __init__.py
│           └── components/ # Reusable UI components
│           └── dialogs/    # Dialog Windows
│       │   └── main_view.py
│       └── controllers/    # Business logic
│           ├── __init__.py
│           └── app_controller.py
│           └── base_controller.py
│       └── utils/                      # Utility functions
│           ├── __init__.py
│           └── event_bus.py            # Threading logic
│           └── helpers.py              # Helper functions
│           └── sybil_epi.py            # Sybil Epi Scoring implementation
├── tests/
├── scripts/
│   └── build.py           # Build script for distribution
├── pyproject.toml         # Project configuration
├── uv.lock               # Dependency lock file
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Docker services
├── .dockerignore         # Docker ignore file
├── .gitignore            # Git ignore file
└── README.md             # This file
```

## Architecture

This template follows the **MVC (Model-View-Controller)** pattern:

- **Models** (`src/app/models.py`): Data structures and business logic
- **Views** (`src/app/views/`): UI components and user interface
- **Controllers** (`src/app/controllers/`): Handle user input and coordinate models and views

## CI/CD Features

### Automatic Version Bumping

The template uses **conventional commits** for automatic version management:

```
feat: add new feature
fix: fix a bug
docs: update documentation
style: format code
refactor: refactor code
test: add tests
chore: maintenance tasks
```

Examples:
- `feat: add user authentication` → Bumps minor version
- `fix: resolve login button not working` → Bumps patch version
- `feat(ui): add dark mode support` → Bumps minor version with scope

Conventional commits [cheatsheet](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13)

### Multi-Platform Releases

When you create a release on GitHub, the workflow automatically builds and packages your application for:
- **Windows** - Executable with installer
- **macOS** - App bundle
- **Linux** - Binary package

### CI Pipeline

The CI pipeline runs on every push and pull request:
- Test across Python 3.9, 3.10, 3.11, and 3.12
- Run security scans with Bandit
- Lint code with Ruff
- Check for potential issues

## Docker Development

### Services

- **app**: Main application container
- **shell**: Development shell for running commands

### Environment Variables

- `DISPLAY`: X11 display for GUI applications
- `XAUTHORITY`: X11 authority file

### Volume Mounts

- `./src:/app/src` - Live code reloading
- `./scripts:/app/scripts` - Build scripts

## Configuration

### pyproject.toml

Main project configuration including:
- Dependencies and optional dev dependencies
- Project metadata
- Entry points
- Tool configurations (Ruff, pytest)

### Ruff Configuration

Ruff is configured with:
- Line length: 88 characters
- Target Python version: 3.9+
- Selected rules: E, W, F, I, B, C4, UP
- Ignored rules: E501 (line too long), B008 (function calls in defaults)

## Building and Distribution

### Local Build

```bash
uv run python scripts/build.py
```

This creates a standalone executable in the `dist/` directory.

### Creating a Release

1. Make sure you have conventional commits
2. When you push commits release please action will automatically create a release PR
3. when you are ready merge the Release PR
4. release-please pushes a v* tag
5. The workflow will automatically build for all platforms

## Testing

### Running Tests

```bash
uv run pytest
```

### Test Coverage

Tests include coverage reporting:
- Terminal output with missing lines
- HTML report in `htmlcov/` directory

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow conventional commits
4. Run tests and linting (`uv run pytest && uv run ruff check`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Use existing code structure and patterns
- Write tests for new features
- Update documentation as needed
- Follow Ruff linting rules
- Use conventional commit messages

## Troubleshooting

### Docker Issues

- If GUI doesn't display, ensure `DISPLAY` and `XAUTHORITY` are set
- Try running `xhost +local:docker` to allow container access to X11
- Check that your system has X11 forwarding enabled

### Python Environment Issues

- Use `uv sync --all-extras` to install all dependencies
- Run `uv sync --upgrade` to update dependencies
- Check Python version compatibility (3.9+ required)

### GUI Issues

- Ensure tkinter is installed (`apt-get install tk` on Linux)
- Check system dependencies for GUI applications
- Verify display server is running

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [uv](https://docs.astral.sh/uv/) - Fast Python package management
- [Docker](https://www.docker.com/) - Containerization platform
- [Ruff](https://github.com/astral-sh/ruff) - Extremely fast Python linter
- [GitHub Actions](https://docs.github.com/en/actions) - CI/CD automation


---

