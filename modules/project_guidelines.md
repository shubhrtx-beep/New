# Draw3 Project Architecture & Guidelines

## Directory Layout
- **Root Directory (`d:/draw3/`)**:
  - Python scripts and modules (`.py`).
  - Python runtime to use: `D:/python/python.exe`.
- **Render Engine (`d:/draw3/rander_engin/`)**:
  - Compiled binaries / executable output (`.exe`).
- **Render Engine Source (`d:/draw3/rander_engin/c++files/`)**:
  - C++ source and header files (`.cpp`, `.h`, `.hpp`).
  - Compiler: `g++` (MinGW / MSYS2).
- **AI Memory (`d:/draw3/ai_memory/`)**:
  - Memory notes, architectural decisions, and context for AI assistant.
- **Prompts Archive (`d:/draw3/ai_memory/prompt/`)**:
  - Raw prompt text files (`.txt`) received from the user and other sources.
- **Documentation (`d:/draw3/doc/`)**:
  - Project documentation and specifications.
- **Examples (`d:/draw3/examples/`)**:
  - Example scripts and usage demonstrations.
- **Tests (`d:/draw3/test/`)**:
  - `failed/`: Test logs and traces for failed test runs.
  - `passed/`: Test logs and traces for passed test runs.

## Environment Details
- **Python**: `D:/python/python.exe` (v3.13.12)
- **C++ Compiler**: `g++` (Rev3, Built by MSYS2 project, 16.2.0)
