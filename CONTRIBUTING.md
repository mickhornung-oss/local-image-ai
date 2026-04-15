# Contributing Guidelines

Thank you for your interest in contributing to local-image-ai! This document provides guidelines and instructions for contributing to this project.

## Getting Started

### Prerequisites
- Python 3.9+
- PyQt5 or tkinter (GUI framework)
- OpenCV, PIL/Pillow
- CUDA/GPU support (optional, for better performance)

### Local Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/local-image-ai.git`
3. Navigate to the project: `cd local-image-ai`
4. Create a virtual environment: `python -m venv .venv`
5. Activate it: `.\.venv\Scripts\Activate.ps1` (Windows)
6. Install dependencies: `pip install -r requirements.txt`

## Development Workflow

### Creating a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### Code Guidelines
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use type hints for function signatures
- Add docstrings to functions and classes
- Keep GUI responsive (use threading for heavy operations)

### Testing Your Changes
- Test GUI functionality on Windows
- Verify image processing pipelines
- Test with various input formats

## Submitting Changes

### Commit Messages
- Use clear, descriptive commit messages
- Format: `type: brief description`
- Examples: `feat: add batch image processing`, `fix: GUI freezing on large files`, `docs: update user guide`

### Pull Request Process
1. Push your changes to your fork
2. Open a Pull Request with:
   - Clear title describing the feature or fix
   - Description of changes
   - Screenshots/GIFs showing the feature
   - Testing evidence

3. Wait for review and address feedback

## Areas for Contribution

### AI Features
- New image processing algorithms
- Additional AI model support
- Performance optimization

### GUI
- User interface improvements
- Better error messaging
- Accessibility enhancements

### Documentation
- User guides
- Tutorial improvements
- API documentation

## Questions?

Feel free to:
- Open an Issue for feature requests or bugs
- Start a Discussion for ideas
- Email the maintainer: [mick.hornung@googlemail.com](mailto:mick.hornung@googlemail.com)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Happy Contributing!** 🚀
